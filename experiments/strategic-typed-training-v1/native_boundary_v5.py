"""Engineering-only continuous native collection/update loop with a complete resume boundary.

The one learner retains model/Adam/RNG in this process across updates. During child
collection/admission it performs no CUDA operations and relinquishes GPU/pool leases;
children perform inference/replay only, never optimization. No concurrent learner.
"""
import os
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG',':4096:8')
import argparse,copy,json,random,subprocess
from pathlib import Path
import torch
from collect_episode_v5 import owned_resources,sha,write
from load_admitted import load
from model_io import load_model,restore_training,make_bundle,atomic_save,digest_json
from episode_balanced_ppo import ppo_update,optimizer_steps
from train_update_v3 import protocol
HERE=Path(__file__).resolve().parent;LAB=Path('/root/heroes3-ai-lab')
CAPSULE=LAB/'evaluations/typed-schema4-ack-drain-capsule-01'
JOBS=[dict(map='takeover-v2-train-01-mines',player=0,seed=2026110800),
      dict(map='takeover-v2-train-02-development',player=1,seed=2026110801)]
def command(args,log):
    r=subprocess.run([str(x) for x in args],capture_output=True,text=True)
    log.write_text(r.stdout+'\nSTDERR:\n'+r.stderr)
    assert r.returncode==0,'Child failed; no silent retry: '+str(log)
def main():
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--initialize',type=Path);g.add_argument('--resume',type=Path)
    p.add_argument('--through-update',type=int,choices=[1,2],required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=False)
    config=None;parent_sha=None;collection_states={};lineage=None
    with owned_resources():
        torch.set_num_threads(1);torch.use_deterministic_algorithms(True)
        torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
        torch.manual_seed(2026110809);torch.cuda.manual_seed_all(2026110809);random.seed(2026110809)
        model,parent,parent_sha=load_model(a.resume or a.initialize,'cuda')
        optimizer=torch.optim.Adam(model.parameters(),lr=3e-4)
        config=protocol(CAPSULE,'engineering_boundary',2026110809)
        config.update(boundary_driver_sha256=sha(Path(__file__)),boundary_jobs=JOBS,
            scope='Two engineering single-episode updates versus EmptyAI only; no strength inference',
            serialization='One learner retained in continuous process; inference-only child CUDA work serialized under the same leases')
        update=0
        if a.resume:
            update=restore_training(parent,model,optimizer,protocol_sha=digest_json(config),device='cuda')
            collection_states=copy.deepcopy(parent['collection_states']);lineage=copy.deepcopy(parent['lineage'])
            checkpoint=a.resume.resolve()
        else:
            lineage=dict(initial_parent_sha256=parent_sha,parent_format=parent['format'],parent_lineage=parent.get('lineage',{}),
                parent_training_updates=parent.get('training_updates',0),parent_optimizer_steps_total=parent.get('optimizer_steps_total',0),
                explicit_optimizer_reset=True,purpose='engineering_boundary',not_an_independent_ability_evaluation=True)
            initial=make_bundle(model,optimizer,training_updates=0,complete=True,protocol=config,parent_sha=parent_sha,
                lineage=lineage,collection_states={},purpose='engineering_boundary',progress={'boundary_initialization':True})
            checkpoint=a.out/'update-0.pt';parent_sha=atomic_save(initial,checkpoint)
        assert update<a.through_update
        write(a.out/'PLAN.json',dict(protocol=config,protocol_sha256=digest_json(config),parent_checkpoint=str(a.resume or a.initialize),
            first_update=update+1,through_update=a.through_update,optimizer_steps_before=optimizer_steps(optimizer),
            jobs=JOBS,training_score_scope='Engineering only; repeated arms are not independent ability samples'))
        torch.cuda.synchronize()
    results=[]
    while update<a.through_update:
        # No parent CUDA calls until every child exits. Each child owns leases.
        work=a.out/f'update-{update+1:02d}';work.mkdir();job=JOBS[update]
        command(['/usr/bin/python3',HERE/'collect_episode_v5.py','--capsule',CAPSULE,'--checkpoint',checkpoint,
            '--map',job['map'],'--player',job['player'],'--opponent','EmptyAI','--seed',job['seed'],'--logical-update',update,
            '--out',work/'native'],work/'collection.log')
        command([LAB/'venv/bin/python',HERE.parent/'strategic-typed-native-v1/audit_game_v5.py',work/'native',work/'raw-audit'],work/'raw-audit.log')
        command([LAB/'gpu-venv/bin/python',HERE/'admit_episode_v5.py','--run',work/'native','--native-audit',work/'raw-audit/AUDIT.json',
            '--out',work/'admitted'],work/'admission.log')
        samples,episodes,admission=load(work/'admitted');assert len(episodes)==1
        expected_runtime={k:config[k] for k in ['capsule_manifest_sha256','native_artifacts']}
        assert episodes[0]['runtime']==expected_runtime and episodes[0]['transport_drained'] is True
        assert episodes[0]['job']['logical_update']==update and all(s['policy_sha256']==parent_sha for s in samples)
        collected=json.loads((work/'native/PLAN.json').read_text())
        for name in ['collect_episode_v5.py','live_jsonl.py','onpolicy_broker_v2.py','model_io.py']:
            path=str(HERE/name);assert collected['hashes'][path]==config['sources'][path]
        assert admission['input_sha256'][str(HERE/'admit_episode_v5.py')]==config['sources'][str(HERE/'admit_episode_v5.py')]
        progress={}
        with owned_resources():
            assert all(sha(Path(p))==h for p,h in config['sources'].items()) and sha(Path(__file__))==config['boundary_driver_sha256']
            assert sha(checkpoint)==parent_sha
            # In the continuous arm there is intentionally no load/restore here.
            state=torch.load(work/'native/agent/sampling-state.pt',map_location='cpu',weights_only=True)
            collection_states[episodes[0]['episode_id']]=state
            before=optimizer_steps(optimizer)
            try:
                ppo_update(model,optimizer,samples,'cuda',progress,episodes=episodes)
                assert progress['completed'] and optimizer_steps(optimizer)>before
                bundle=make_bundle(model,optimizer,training_updates=update+1,complete=True,protocol=config,parent_sha=parent_sha,
                    lineage=lineage,collection_states=collection_states,purpose='engineering_boundary',progress=progress)
                checkpoint=a.out/f'update-{update+1}.pt';parent_sha=atomic_save(bundle,checkpoint)
            except BaseException:
                bundle=make_bundle(model,optimizer,training_updates=update,complete=False,protocol=config,parent_sha=parent_sha,
                    lineage=lineage,collection_states=collection_states,purpose='engineering_boundary',progress=progress)
                atomic_save(bundle,a.out/'PARTIAL_NONRESUMABLE.pt');raise
            update+=1
            results.append(dict(update=update,samples=len(samples),reward=episodes[0]['reward'],
                cuda_optimizer_steps=optimizer_steps(optimizer)-before,optimizer_steps_total=optimizer_steps(optimizer),checkpoint_sha256=parent_sha))
            write(a.out/'RESULT.json',dict(passed=True,through_update=update,updates_in_this_process=results,
                final_checkpoint=str(checkpoint),optimizer_steps_total=optimizer_steps(optimizer),ability_improvement_claim=False))
            print(json.dumps(results[-1]),flush=True);torch.cuda.synchronize()
    return 0
if __name__=='__main__':raise SystemExit(main())
