"""Draft future once-only epoch initialization. Not a qualification of the current flow fix."""
import argparse,copy,hashlib,importlib.util,json,random,sys
from pathlib import Path
import torch
import model_io
HERE=Path(__file__).resolve().parent
PARENT=Path('/root/heroes3-ai-lab/evaluations/strategic-build-exploration-continuation-01/round-04/update/update-4.pt')
EXPECTED='24b8c3f3d5ddacd61e48bd87a526c1fd59b2a83eafbdacfe44bd5ddcfb5d3e6d'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    torch.set_num_threads(1)
    parent_io=module('_replan_draft_frozen_parent_codec',HERE.parent/'strategic-learned-build-exploration-policy-v1/model_io.py')
    old,pb,digest=parent_io.load_model(PARENT,'cpu');assert digest==EXPECTED and pb['optimizer_steps_total']==504
    lineage=dict(reset_optimizer=True,reset_rng=True,discard_rollout=True,weights_only=True,new_gradient_steps=0,
        parent_checkpoint_sha256=digest,parent_optimizer_steps=504,parent_training_updates=4,
        new_epoch='strategic-learned-replan-training-v1',threat_replan='once',
        status='draft future intervention only; native gratis-army-transfer flow diagnosis takes priority; no capsule/source protocol freeze')
    initial=dict(format=model_io.INITIAL_FORMAT,schema=model_io.architecture.encoder.SCHEMA,
        encoder_version=model_io.architecture.ENCODER_VERSION,architecture_version=model_io.architecture.ARCHITECTURE_VERSION,
        state_dim=35,candidate_dim=43,hidden=old.hidden,prior_config=copy.deepcopy(pb['prior_config']),
        state_dict=model_io.cpu_tree(old.state_dict()),lineage=lineage,contract_sha256=model_io.CONTRACT_SHA256,
        policy_tensor_sha256=model_io.tensor_sha(old.state_dict()))
    target=a.out/'replan-initialization.pt';initial_sha=model_io.save_initialization(initial,target)
    new,_,readsha=model_io.load_model(target,'cpu');assert readsha==initial_sha
    assert model_io.tensor_sha(new.state_dict())==model_io.tensor_sha(old.state_dict())
    loader=module('_replan_draft_old_training_admission',HERE.parent/'strategic-learned-economy-policy-v1/load_admitted.py')
    source=Path('/root/heroes3-ai-lab/evaluations/strategic-learned-build-training-01')
    checked=0;build_windows=0;last=None
    with torch.no_grad():
        for cell in sorted(source.glob('cell-*')):
            rows,_,_=loader.load(cell/'admitted')
            for row in rows:
                batch=model_io.architecture.encoder.collate([row['request']]);x,v=old(**batch);y,w=new(**batch)
                assert torch.equal(x,y) and torch.equal(v,w);checked+=1;last=row
                build_windows+=any(c['op']=='build' for c in row['request']['candidates'])
    assert checked==3000 and build_windows==400
    optimizer=torch.optim.Adam(new.parameters(),lr=3e-4)
    protocol=dict(schema='strategic-learned-replan-training-v1',architecture_version=model_io.architecture.ARCHITECTURE_VERSION,
        threat_replan='once',action_schema='strategy-candidates-v5',economy_epoch='learned-economy-build-v1',contract_sha256=model_io.CONTRACT_SHA256)
    cpu=model_io.make_bundle(new,optimizer,training_updates=0,complete=True,protocol=protocol,parent_sha=initial_sha,
        lineage=dict(CPU_CODEC_TEST_ONLY=True),collection_states={},purpose='cpu_codec_test',progress={})
    testpath=a.out/'CPU_TEST_NOT_TRAINED.pt';model_io.atomic_save(cpu,testpath,allow_test=True)
    loaded,lb,_=model_io.load_model(testpath,allow_test=True);opt2=torch.optim.Adam(loaded.parameters(),lr=3e-4)
    model_io.restore_training(lb,loaded,opt2,protocol_sha=cpu['protocol_sha256'],allow_test=True)
    expected_cpu=torch.rand(7);expected_python=[random.random() for _ in range(4)]
    torch.manual_seed(711);random.seed(711)
    model_io.restore_training(lb,loaded,opt2,protocol_sha=cpu['protocol_sha256'],allow_test=True)
    assert torch.equal(expected_cpu,torch.rand(7)) and expected_python==[random.random() for _ in range(4)]
    assert model_io.groups(loaded,opt2)==cpu['parameter_groups'] and model_io.steps(opt2.state_dict())==0
    rejects=[]
    for case in ('old_format','off_protocol','partial','wrong_architecture'):
        bad=copy.deepcopy(cpu)
        if case=='old_format':bad['format']='strategic-learned-build-exploration-ppo-checkpoint-v1'
        if case=='off_protocol':
            bad['protocol']['threat_replan']='off';bad['protocol_sha256']=model_io.digest_json(bad['protocol'])
        if case=='partial':bad['complete_update_boundary']=False
        if case=='wrong_architecture':bad['architecture_version']='unknown'
        before=model_io.tensor_sha(loaded.state_dict());rng=torch.get_rng_state().clone();python=random.getstate()
        try:model_io.restore_training(bad,loaded,opt2,protocol_sha=bad['protocol_sha256'],allow_test=True)
        except (ValueError,AssertionError,RuntimeError):rejects.append(case)
        else:raise AssertionError('Accepted '+case)
        assert before==model_io.tensor_sha(loaded.state_dict()) and torch.equal(rng,torch.get_rng_state()) and python==random.getstate()
    report=dict(passed_CPU=True,status='draft only; once intervention shelved pending actual free-transfer flow diagnosis/fix',
        native_games=0,GPU_steps=0,optimizer_steps=0,final_source_protocol_frozen=False,
        parent_sha256=digest,parent_optimizer_steps_not_continued=504,initialization_sha256=initial_sha,
        architecture_unchanged=True,weights_exact=True,logits_and_critic_exact_on_historical_TRAIN=checked,
        included_old_build_windows=build_windows,empty_Adam_binding_CPU_Python_RNG_recovery=True,rejected=rejects,
        current_source_sha256={p.name:sha(p) for p in HERE.glob('*.py')},ability_improvement_claim=False)
    (a.out/'AUDIT.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
