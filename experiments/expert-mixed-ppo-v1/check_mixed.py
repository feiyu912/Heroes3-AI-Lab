"""CPU-only preparation: no worker, game, CUDA, or training job is launched."""
import argparse
import copy
import gzip
import json
from pathlib import Path
import sys
import numpy as np
import torch
from common import HERE,LAB,RESEARCH,PUBLIC,read,digest,prepare_plan,verify_plan,module,FrozenExpert,FragmentTracker
from lab_io import atomic_json
from reference_ppo import update,encode_reference,distribution


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--plan',default=str(HERE/'draft-plan.json'))
    parser.add_argument('--checkpoint',default=PUBLIC)
    args=parser.parse_args()
    path=Path(args.plan).resolve()
    if not path.exists():prepare_plan(path,args.checkpoint,finalized=False)
    plan=read(path);verify_plan(plan)
    torch.set_num_threads(1);torch.manual_seed(2026101604)
    sys.path.insert(0,str(LAB/'experiments/expert-knowledge-v1'))
    from graph_observation_codec import unpack
    raw=[]
    for side,role in enumerate(['attacker','defender']):
        archive=LAB/('experiments/human-tactics-v1/runs/expert-dragon-breath-train-0-'+role+'.json.gz')
        with gzip.open(archive,'rt') as stream:data=json.load(stream)
        assert data['episode']['split']=='train'
        decisions=data['decisions']
        for index in range(12):raw.append(unpack(decisions[index%len(decisions)]['observation'],side))
    expert=FrozenExpert(plan)
    choices=expert(raw)
    assert len(choices)==24 and all(action in observation['active_action_ids'] for action,observation in zip(choices,raw))
    expert.verify()
    graph=module('mixed_cpu_graph',RESEARCH/'recovered-graph.py')
    learner=graph.RecoveredPair(plan['initial_checkpoint']).cpu().eval()
    for name,parameter in learner.named_parameters():
        parameter.requires_grad_('policy_head__' in name or 'value_head__' in name)
    reference=graph.RecoveredPair(plan['reference_checkpoint']).cpu().eval();reference.requires_grad_(False)
    assert not ({parameter.data_ptr() for parameter in learner.parameters()} & {parameter.data_ptr() for parameter in reference.parameters()})
    body_versions={name:parameter._version for name,parameter in learner.named_parameters() if not parameter.requires_grad}
    reference_versions=[parameter._version for parameter in reference.parameters()]
    cached=learner.encode_features(raw)
    encoded=encode_reference(reference,raw,graph.head_collate,batch_size=24)
    actions=[list(observation['active_action_ids']).index(action) for observation,action in zip(raw,choices)]
    with torch.inference_mode():
        batch=graph.head_collate(cached,'cpu');logits,values=learner(*batch)
        oldlog=distribution(logits,batch[-1]).log_prob(torch.tensor(actions)).numpy().copy()
        oldvalues=values.numpy().copy()
    optimizer=torch.optim.Adam([parameter for parameter in learner.parameters() if parameter.requires_grad],lr=1e-5)
    metrics=update(learner,optimizer,cached,actions,oldlog,oldvalues,np.linspace(-1,1,24,dtype=np.float32),oldvalues+.1,
        epochs=1,batch_size=8,recompute_batch_size=24,recompute_atol=2e-4,recompute_rtol=0.,
        collate_fn=graph.head_collate,reference_coef=.1,reference_log_probs=encoded['log_probs'],
        reference_action_ids=encoded['action_ids'],candidate_action_ids=[sample[2].tolist() for sample in cached],
        reference_parameters=tuple(reference.parameters()))
    assert all(np.isfinite(value) for value in metrics.values())
    assert any(parameter.grad is not None for parameter in learner.parameters() if parameter.requires_grad)
    assert body_versions=={name:parameter._version for name,parameter in learner.named_parameters() if not parameter.requires_grad}
    assert reference_versions==[parameter._version for parameter in reference.parameters()]
    damaged=copy.deepcopy(plan)
    filename=next(iter(damaged['dependency_sha256']))
    damaged['dependency_sha256'][filename]='0'*64
    rejected=False
    try:verify_plan(damaged)
    except AssertionError:rejected=True
    assert rejected,'Source hash mismatch was not rejected'
    tracker=FragmentTracker(4)
    ongoing=dict(terminated=False,truncated=False)
    tracker.observe([ongoing]*4)
    tracker.observe([dict(terminated=True,truncated=False),dict(terminated=False,truncated=True),ongoing,ongoing])
    assert tracker.steps==[0,0,2,2]
    closure=tracker.close_summary(plan['phases'][0][:4],'rotation')
    assert closure['discarded_ongoing_fragments']==2 and closure['sampled_owned_steps_in_fragments']==4
    assert closure['environment_truncations_added']==0 and tracker.steps==[0,0,0,0]
    tracker.observe([ongoing,dict(terminated=True,truncated=False),dict(terminated=True,truncated=False),dict(terminated=False,truncated=True)])
    finish=tracker.close_summary(plan['phases'][0][:4],'finish')
    assert finish['discarded_ongoing_fragments']==1 and finish['sampled_owned_steps_in_fragments']==1
    count_rows=[]
    for number,phase in enumerate(plan['phases']):
        count_rows.append(dict(phase=number,counts={category:{role:sum(row['category']==category and row['config']['role']==role for row in phase)
            for role in ['attacker','defender']} for category in plan['categories']},
            expert_family_roles={family:{role:sum(row['category']=='expert' and row['tactic_id']==family and row['config']['role']==role for row in phase)
                for role in ['attacker','defender']} for family in ['death-cloud','dragon-breath','retaliation-bait']}))
    result=dict(passed=True,plan_sha256=digest(path),plan=str(path),finalized_for_execution=plan['finalized_for_execution'],
        device='cpu',curriculum_counts=count_rows,train_only=True,expert_legal_actions_checked=24,
        real_graph_forward_backward=True,metrics=metrics,frozen_body_unchanged=True,independent_reference_unchanged=True,
        dependency_gate_rejected_changed_sha=True,simulator_started=False,CUDA_started=False,
        fragment_accounting_checked=True,fragment_test=dict(rotation=closure,finish=finish),
        optimization_scope='One CPU mathematical preflight update only; no trained candidate saved',
        training_effectiveness_proven=False)
    atomic_json(HERE/'cpu-preflight.json',result)
    print(json.dumps(result),flush=True)


if __name__=='__main__':main()
