import sys
from pathlib import Path
LOCAL=Path(__file__).resolve().parent
BASE=LOCAL;RUN=LOCAL.parent/'strategic-learned-replan-run-v1';sys.path.append(str(RUN))
sys.path.append(str(BASE))
from pipeline_common import source_inputs,capsule_inputs,validate_capsule,audit_metadata,validate_native_epoch,validate_cells,clean_environment,AUDITOR,NATIVE,MARKER,EPOCH,BASE
"""One certified fresh on-policy CUDA update; complete boundaries only for resume."""
import os
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG',':4096:8')
import argparse,copy,json,random
from pathlib import Path
import torch
from collect_episode_v5 import owned_resources,sha,write
from load_admitted import load
from episode_balanced_ppo import PROTOCOL,ppo_update,optimizer_steps
from model_io import load_model,restore_training,make_bundle,atomic_save,digest_json,tensor_sha,CONTRACT_SHA256,INITIAL_FORMAT,architecture
HERE=LOCAL;TYPED=LOCAL

def protocol(capsule,purpose,seed):
    sources=source_inputs()+[Path(__file__).resolve()]
    return dict(schema=EPOCH,threat_replan='once',architecture_version=architecture.ARCHITECTURE_VERSION,action_schema='strategy-candidates-v5',economy_epoch='learned-economy-build-v1',contract_sha256=CONTRACT_SHA256,purpose=purpose,algorithm=PROTOCOL,learning_rate=3e-4,
        global_seed=seed,optimizer='Adam',torch_version=str(torch.__version__),cuda_version=torch.version.cuda,device=torch.cuda.get_device_name(0),
        deterministic_algorithms=True,allow_tf32=False,
        sources={str(p):sha(p) for p in sources},capsule_manifest_sha256=sha(capsule/'build-source-manifest.json'),
        native_artifacts={n:sha(capsule/'bin'/n) for n in ['vcmiclient','vcmiserver','libvcmi.so']},
        curriculum='Training maps only; one fresh logical-update seed per episode. No final-test or learning-gain inference.')

def main():
    p=argparse.ArgumentParser();group=p.add_mutually_exclusive_group(required=True)
    group.add_argument('--initialize',type=Path);group.add_argument('--resume',type=Path)
    p.add_argument('--admission',type=Path,action='append',required=True);p.add_argument('--capsule',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--seed',type=int,default=2026102801)
    p.add_argument('--purpose',choices=['engineering_boundary','curriculum_training'],default='curriculum_training');a=p.parse_args()
    clean_environment();validate_capsule(a.capsule)
    a.out.mkdir(parents=True,exist_ok=False);samples=[];episodes=[];admissions=[]
    for directory in a.admission:
        rows,manifest,report=load(directory);samples.extend(rows);episodes.extend(manifest)
        admissions.append({'directory':str(directory.resolve()),'sha256':sha(directory/'AUDIT.json'),'report':report})
    assert len({e['episode_id'] for e in episodes})==len(episodes)
    if a.purpose=='curriculum_training':
        validate_cells(episodes)
    else:raise ValueError('This new mainline epoch requires the complete eight-cell curriculum')
    assert any(s['action_type']=='build' for s in samples),'No certified real policy-build sample; do not update and call this economy learning'
    parent=a.resume or a.initialize;progress={};result={'completed_update':False,'cuda_optimizer_steps':0,'ability_improvement_claim':False}
    with owned_resources():
        torch.set_num_threads(1);torch.use_deterministic_algorithms(True);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
        torch.manual_seed(a.seed);torch.cuda.manual_seed_all(a.seed);random.seed(a.seed)
        model,parent_bundle,parent_sha=load_model(parent,'cuda');optimizer=torch.optim.Adam(model.parameters(),lr=3e-4)
        if a.initialize:assert parent_bundle['format']==INITIAL_FORMAT,'This build epoch starts at its explicit reset initialization; later updates require resume'
        config=protocol(a.capsule,a.purpose,a.seed);config_sha=digest_json(config)
        expected_runtime={k:config[k] for k in ['capsule_manifest_sha256','native_artifacts']}
        assert all(e.get('runtime')==expected_runtime and e.get('transport_drained') is True for e in episodes),'Mixed or uncertified native runtime epoch'
        # Bind the actual admitted collector/observer to this protocol epoch.
        # Runtime identity alone cannot certify unchanged sampling tooling.
        for admission in admissions:
            paths=[Path(p) for p in admission['report']['input_sha256'] if p.endswith('/sampling-state.pt')]
            assert len(paths)==1
            collection_plan=json.loads((paths[0].parent.parent/'PLAN.json').read_text())
            for path,digest in config['sources'].items():
                assert collection_plan['hashes'].get(path)==digest,'Collector/source epoch differs: '+path
            assert collection_plan['pipeline_epoch']==EPOCH
            admission_source=str(LOCAL/'admit_episode_v5.py')
            assert admission['report']['input_sha256'].get(admission_source)==config['sources'][admission_source],'Admission epoch differs'
        update=0;collection_states={}
        if a.resume:
            update=restore_training(parent_bundle,model,optimizer,protocol_sha=config_sha,device='cuda')
            collection_states=copy.deepcopy(parent_bundle['collection_states'])
        assert all(s['policy_sha256']==parent_sha for s in samples),'Off-policy or wrong parent samples'
        assert all(e['job']['logical_update']==update for e in episodes),'Sampling logical update differs from parent boundary'
        for e,admission in zip(episodes,admissions):
            paths=[Path(p) for p in admission['report']['input_sha256'] if p.endswith('/sampling-state.pt')]
            assert len(paths)==1
            collection_states[e['episode_id']]=torch.load(paths[0],map_location='cpu',weights_only=True)
        write(a.out/'PLAN.json',dict(protocol=config,protocol_sha256=config_sha,parent_sha256=parent_sha,previous_updates=update,
            admissions=admissions,source_scope='One experimental derived model; existing V8 and checkpoints untouched'))
        stop_before=float(model.actor.stop_bias.detach().cpu());build_before=float(model.actor.build_bias.detach().cpu());step_before=optimizer_steps(optimizer)
        lineage={'parent_format':parent_bundle['format'],'parent_training_updates':parent_bundle.get('training_updates',0),
                 'parent_optimizer_steps_total':parent_bundle.get('optimizer_steps_total',0),'parent_lineage':parent_bundle.get('lineage',{}),
                 'training_epoch':EPOCH,'explicit_optimizer_reset':bool(a.initialize),'purpose':a.purpose,'not_an_independent_ability_evaluation':True}
        try:
            assert next(model.parameters()).device.type=='cuda'
            ppo_update(model,optimizer,samples,'cuda',progress,episodes=episodes)
            assert progress['completed'] and optimizer_steps(optimizer)>step_before
            assert all(sha(Path(p))==h for p,h in config['sources'].items())
            checkpoint=make_bundle(model,optimizer,training_updates=update+1,complete=True,protocol=config,parent_sha=parent_sha,
                lineage=lineage,collection_states=collection_states,purpose=a.purpose,progress=progress)
            checkpoint_path=a.out/f'update-{update+1}.pt';digest=atomic_save(checkpoint,checkpoint_path)
            restored,readback,read_sha=load_model(checkpoint_path,'cpu')
            assert read_sha==digest and tensor_sha(restored.state_dict())==tensor_sha(model.state_dict())
            result.update(completed_update=True,training_updates=update+1,cuda_optimizer_steps=optimizer_steps(optimizer)-step_before,
                optimizer_steps_total=optimizer_steps(optimizer),checkpoint_sha256=digest,checkpoint=str(checkpoint_path),
                stop_bias_before=stop_before,stop_bias_after=float(model.actor.stop_bias.detach().cpu()),
                stop_bias_adam_step=int(optimizer.state[model.actor.stop_bias]['step']),progress=progress,
                build_bias_before=build_before,build_bias_after=float(model.actor.build_bias.detach().cpu()),
                build_bias_adam_step=int(optimizer.state[model.actor.build_bias]['step']),
                build_bias_adam_exp_avg=float(optimizer.state[model.actor.build_bias]['exp_avg'].detach().cpu()),
                episodes=len(episodes),samples=len(samples),training_wins=sum(e['reward']==1 for e in episodes),
                policy_builds=sum(s['action_type']=='build' for s in samples),
                training_losses=sum(e['reward']==-1 for e in episodes),purpose=a.purpose,checkpoint_model_readback_exact=True)
        except BaseException as error:
            progress['attempted_update']=update+1
            partial=make_bundle(model,optimizer,training_updates=update,complete=False,protocol=config,parent_sha=parent_sha,
                lineage=lineage,collection_states=collection_states,purpose=a.purpose,progress=progress)
            atomic_save(partial,a.out/'PARTIAL_NONRESUMABLE.pt')
            result.update(error=repr(error),progress=progress,cuda_optimizer_steps=optimizer_steps(optimizer)-step_before)
        write(a.out/'RESULT.json',result)
    print(json.dumps(result,indent=2));return 0 if result['completed_update'] else 1
if __name__=='__main__':raise SystemExit(main())



