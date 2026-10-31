"""CPU contracts only: no game, native runtime, or CUDA context is started."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import numpy as np
import torch

HERE = Path(__file__).resolve().parent
RESEARCH = HERE.parents[1]/'research'
sys.path.insert(0,str(RESEARCH))
import reference_ppo as refppo
import masked_ppo as original
import decision_model

spec = importlib.util.spec_from_file_location('_reference_check_graph',RESEARCH/'recovered-graph.py')
graph = importlib.util.module_from_spec(spec)
spec.loader.exec_module(graph)
collate = graph.head_collate


class TinyPair(torch.nn.Module):
    def __init__(self,body_scale=1.):
        super().__init__()
        self.body_scale = torch.nn.Parameter(torch.tensor(body_scale))
        self.policy = torch.nn.Linear(64,1)
        self.value = torch.nn.Linear(64,1)
        self.forward_batches = []
        self.encoded_raw = 0

    def encode_features(self,observations):
        self.encoded_raw += len(observations)
        return [(np.asarray(obs['raw'],np.float32)*float(self.body_scale.detach()),
                 np.asarray(obs['global'],np.float32), np.asarray(obs['active_action_ids'],np.int64), obs['lab_side'])
                for obs in observations]

    def forward(self,embeddings,globals_,roles,mask):
        self.forward_batches.append(len(embeddings))
        return self.policy(embeddings).squeeze(-1).masked_fill(~mask,-torch.inf),self.value(globals_).squeeze(-1)


def snapshot(model):
    return {name:value.detach().clone() for name,value in model.state_dict().items()}


def unchanged(model,before):
    return all(torch.equal(value,before[name]) for name,value in model.state_dict().items())


def main():
    torch.set_num_threads(1)
    torch.manual_seed(2026103001)
    rng = np.random.default_rng(2026103001)
    raw = [dict(raw=rng.normal(size=(2+i%3,64)).astype(np.float32),
                global_=None,lab_side=i%2,active_action_ids=list(range(30,32+i%3))) for i in range(7)]
    for obs in raw:
        obs['global'] = rng.normal(size=64).astype(np.float32)
    learner = TinyPair().eval()
    inputs = learner.encode_features(raw)
    actions = [i%len(obs['active_action_ids']) for i,obs in enumerate(raw)]
    old_logp,old_values = [],[]
    with torch.inference_mode():
        for start in range(0,len(inputs),3):
            batch = collate(inputs[start:start+3])
            logits,values = learner(*batch)
            old_logp.extend(refppo.distribution(logits,batch[-1]).log_prob(torch.tensor(actions[start:start+3])).tolist())
            old_values.extend(values.tolist())
    advantages = np.array([-.5,.2,.8,-.3,.6,-.7,.9],np.float32)
    returns = np.asarray(old_values,np.float32)+.2
    common = dict(epochs=2,batch_size=4,recompute_batch_size=3,recompute_atol=2e-4,recompute_rtol=0.,target_kl=100.)
    baseline,zero = copy.deepcopy(learner),copy.deepcopy(learner)
    baseline_opt = torch.optim.SGD(baseline.parameters(),lr=.03)
    zero_opt = torch.optim.SGD(zero.parameters(),lr=.03)
    prior_collate = decision_model.collate
    decision_model.collate = collate
    try:
        torch.manual_seed(7331)
        baseline_metrics = original.update(baseline,baseline_opt,inputs,actions,old_logp,old_values,advantages,returns,**common)
    finally:
        decision_model.collate = prior_collate
    torch.manual_seed(7331)
    zero_metrics = refppo.update(zero,zero_opt,inputs,actions,old_logp,old_values,advantages,returns,
                                reference_coef=0.,collate_fn=collate,**common)
    assert unchanged(zero,snapshot(baseline)), 'coef0 changed original PPO weights'
    assert all(zero_metrics[key] == value for key,value in baseline_metrics.items()), 'coef0 changed PPO metrics'
    checks = [dict(name='coef0 bitwise original-PPO weights and exact common metrics',passed=True)]
    logits = torch.tensor([[-1.,1.,float('nan')]],requires_grad=True)
    mask = torch.tensor([[True,True,False]])
    reference_leaf = torch.log(torch.tensor([.85,.15])).requires_grad_()
    kl = refppo.legal_reference_kl(logits,mask,[reference_leaf]).mean()
    assert float(kl.detach())>0
    kl.backward()
    assert reference_leaf.grad is None
    assert torch.isfinite(logits.grad).all() and logits.grad[0,0]<0 and logits.grad[0,1]>0
    with torch.no_grad():
        moved = logits-.1*logits.grad
    reduced = refppo.legal_reference_kl(moved,mask,[reference_leaf]).mean()
    assert float(reduced.detach())<float(kl.detach())
    checks.append(dict(name='positive KL and gradient toward detached reference',passed=True,before=float(kl.detach()),after=float(reduced.detach())))
    observed = []
    for illegal in [float('nan'),float('inf'),-float('inf'),1e30]:
        padded = torch.tensor([[-1.,1.,illegal]],requires_grad=True)
        value = refppo.legal_reference_kl(padded,mask,[reference_leaf])
        value.sum().backward()
        assert torch.isfinite(padded.grad).all() and padded.grad[0,2]==0
        observed.append(float(value.detach()))
    assert len(set(observed))==1
    checks.append(dict(name='illegal padding NaN/inf/huge logits do not affect legal KL or gradients',passed=True))
    reference = copy.deepcopy(learner).eval()
    reference.body_scale.data.fill_(3.)
    for parameter in reference.parameters():
        parameter.requires_grad_(False)
    before_reference = snapshot(reference)
    encoded = refppo.encode_reference(reference,raw,collate,batch_size=3)
    assert reference.encoded_raw == learner.encoded_raw+len(raw)
    with torch.inference_mode():
        own_features = reference.encode_features(raw)
        batch = collate(own_features)
        expected,_ = reference(*batch)
        expected = refppo.distribution(expected,batch[-1]).logits
        borrowed,_ = reference(*collate(inputs))
        borrowed = refppo.distribution(borrowed,batch[-1]).logits
        for index,row in enumerate(encoded['log_probs']):
            torch.testing.assert_close(row,expected[index][batch[-1][index]],atol=1e-6,rtol=0.)
        assert not torch.allclose(expected[batch[-1]],borrowed[batch[-1]])
    checks.append(dict(name='reference independently encodes raw observations with different frozen body',passed=True))
    fitted = copy.deepcopy(learner)
    fitted.forward_batches = []
    opt = torch.optim.SGD(fitted.parameters(),lr=.03)
    metrics = refppo.update(fitted,opt,inputs,actions,old_logp,old_values,advantages,returns,
        reference_log_probs=encoded['log_probs'],reference_action_ids=encoded['action_ids'],
        candidate_action_ids=[obs['active_action_ids'] for obs in raw],reference_coef=.1,
        reference_parameters=tuple(reference.parameters()),collate_fn=collate,**common)
    assert unchanged(reference,before_reference) and all(parameter.grad is None for parameter in reference.parameters())
    assert all(np.isfinite(value) for value in metrics.values()) and metrics['reference_kl']>0
    assert fitted.forward_batches[:3] == [3,3,1]
    checks.append(dict(name='full cached-feature PPO finite gradients, unchanged reference, rollout-size recompute',passed=True,metrics=metrics))
    rejected = []
    def must_reject(label,kwargs,model=None,optimizer=None,logp=None):
        current = model or copy.deepcopy(learner)
        optimizer = optimizer or torch.optim.SGD(current.parameters(),lr=.03)
        before = snapshot(current)
        try:
            refppo.update(current,optimizer,inputs,actions,old_logp if logp is None else logp,
                old_values,advantages,returns,collate_fn=collate,**(common|kwargs))
        except (ValueError,AssertionError,RuntimeError):
            assert unchanged(current,before), label+' modified learner before rejection'
            rejected.append(label)
        else:
            raise AssertionError('Did not reject '+label)
    must_reject('recompute error above 2e-4',{},logp=np.asarray(old_logp)+.0003)
    must_reject('loosened absolute recompute gate',dict(recompute_atol=.001))
    must_reject('relative recompute tolerance',dict(recompute_rtol=1e-6))
    wrong = copy.deepcopy(encoded['action_ids'])
    wrong[0] = wrong[0][::-1]
    anchor = dict(reference_coef=.1,reference_log_probs=encoded['log_probs'],
                  reference_action_ids=encoded['action_ids'],candidate_action_ids=[obs['active_action_ids'] for obs in raw])
    must_reject('candidate identity/order mismatch',anchor|dict(reference_action_ids=wrong))
    badmodel = copy.deepcopy(learner)
    badopt = torch.optim.SGD(list(badmodel.parameters())+list(reference.parameters()),lr=.03)
    must_reject('reference parameters in optimizer',anchor|dict(reference_parameters=tuple(reference.parameters())),badmodel,badopt)
    badrows = list(encoded['log_probs'])
    badrows[-1] = torch.tensor([0.])
    must_reject('bad reference length rejected before any update',anchor|dict(reference_log_probs=badrows))
    checks.append(dict(name='strict failures preserve learner weights',passed=True,rejections=rejected))
    # Explicitly verify no-action masks and nonfinite legal logits are rejected.
    for badmask,badlogits in [(torch.tensor([[False,False]]),torch.zeros(1,2)),
                              (torch.tensor([[True,False]]),torch.tensor([[float('nan'),0.]]))]:
        try:
            refppo.legal_reference_kl(badlogits,badmask,[torch.tensor([0.])])
        except ValueError:
            pass
        else:
            raise AssertionError('Invalid legal mask/logit accepted')
    checks.append(dict(name='empty masks and nonfinite legal logits rejected',passed=True))
    advantage,return_ = refppo.gae([[1.],[2.]],[[.5],[.2]],[[.2],[.8]],
        [[False],[False]],[[True],[False]],gamma=1.,lam=1.)
    np.testing.assert_allclose(advantage,[[.7],[2.6]],rtol=0,atol=1e-6)
    np.testing.assert_allclose(return_,[[1.2],[2.8]],rtol=0,atol=1e-6)
    checks.append(dict(name='reused GAE truncation bootstraps while ending recurrence',passed=True))
    result = dict(passed=True,device='cpu',checks=checks,training_effectiveness_proven=False,
        limitations='Synthetic mathematical contracts only; no GPU, game, ordinary-winrate or independent-generalization experiment.')
    (HERE/'cpu-math-check.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
