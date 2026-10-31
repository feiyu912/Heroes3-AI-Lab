"""After learners exit: independently rerun raw gates and every CPU DEV decision."""
import argparse,json,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
PACKAGE=HERE.parent/'strategic-active-opponent-learning-20261024'
POLICY=HERE.parent/'strategic-active-opponent-policy-v4'
sys.path.insert(0,str(PACKAGE))
from pipeline_common import sha,INITIAL_SHA,validate_cells,DEFAULT_CAPSULE,LAB
def read(p):return json.loads(Path(p).read_text())
def call(command,log):
    with log.open('w') as stream:r=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT)
    assert r.returncode==0,str(log)
def main():
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    result=read(a.run/'RESULT.json');assert result['passed'] and set(result['arms'])=={'control','curriculum'}
    frozen=read(PACKAGE/'SOURCE_FREEZE.json')['files'];assert all(sha(path)==h for path,h in frozen.items())
    import torch
    torch.set_num_threads(1)
    from model_io import read as read_model,load_model
    training={};trainrows=0;devrows=0;rawhashes={};cpu=[];pairing=[]
    for arm in ('control','curriculum'):
        episodes=[];samples=0;wins=0
        for i in range(8):
            root=a.run/arm/f'cell-{i:02d}';target=a.out/f'TRAIN-{arm}-{i:02d}'
            call([str(LAB/'venv/bin/python'),str(PACKAGE/'audit_game_v6.py'),str(root/'native'),str(target)],a.out/f'TRAIN-{arm}-{i:02d}.log')
            audit=read(target/'AUDIT.json');assert audit==read(root/'raw-audit/AUDIT.json')
            episode=read(root/'admitted/episode.json');admission=read(root/'admitted/AUDIT.json')
            assert admission['passed'] and admission['replay_actions_logprobs_values_rng_exact'] and episode['sampling_replay_exact']
            assert all(sha(path)==h for path,h in admission['input_sha256'].items())
            assert all(sha(root/'admitted'/path)==h for path,h in admission['output_sha256'].items())
            assert episode['checkpoint_sha256']==INITIAL_SHA and episode['job']['arm']==arm
            assert episode['decisions']==admission['samples_admitted']==audit['actual_decisions_checked']
            episodes.append(episode);samples+=episode['decisions'];wins+=episode['reward']==1
            rawhashes.update({str(root/'native'/path):h for path,h in audit['raw_sha256'].items()})
        validate_cells(episodes);trained=result['arms'][arm]['training'];bundle,digest=read_model(trained['checkpoint'])
        assert bundle['training_updates']==1 and bundle['complete_update_boundary'] and bundle['parent_checkpoint_sha256']==INITIAL_SHA
        assert bundle['protocol']['training_treatment']==arm and trained['samples']==samples and trained['training_wins']==wins
        assert digest==trained['checkpoint_sha256'] and bundle['optimizer_steps_total']==trained['cuda_optimizer_steps']>0
        assert bundle['optimizer_steps_total']==bundle['progress']['optimizer_steps']
        recovery=read(result['arms'][arm]['recovery']);assert recovery['passed_exact'] and recovery['actual_CUDA_restore_executed'] and recovery['checkpoint_sha256']==digest
        assert len(recovery['negative_cases'])==12 and recovery['optimizer_steps_restored']==bundle['optimizer_steps_total']
        assert all(sha(path)==h for path,h in bundle['protocol']['sources'].items())
        training[arm]=dict(samples=samples,wins=wins,losses=8-wins,actual_Adam=bundle['optimizer_steps_total'],checkpoint_sha256=digest,full_CUDA_restore_passed=True)
        trainrows+=samples
        del bundle
    for i in range(8):
        roots={arm:a.run/arm/f'cell-{i:02d}'/'native' for arm in ('control','curriculum')}
        plans={arm:read(root/'PLAN.json') for arm,root in roots.items()}
        assert plans['control']['sampling_seed']==plans['curriculum']['sampling_seed']
        assert all(plans['control'][k]==plans['curriculum'][k] for k in ('map','seed','owned_player','opponent','logical_update','checkpoint'))
        unaffected=plans['control']['opponent']=='EmptyAI'
        full_proposals_equal=sha(roots['control']/'agent/typed-broker.jsonl')==sha(roots['curriculum']/'agent/typed-broker.jsonl')
        pairing.append(dict(cell=i,opponent=plans['control']['opponent'],sampling_seed_equal=True,unaffected_treatment=unaffected,full_archived_proposal_stream_equal=full_proposals_equal,initial_request_equal=sha(roots['control']/'agent/request-00000001.json')==sha(roots['curriculum']/'agent/request-00000001.json')))
    dev=read(a.run/'DEV/RESULT.json');assert dev['passed'] and len(dev['pairs'])==8
    for i,pair in enumerate(dev['pairs']):
        assert pair['index']==i and pair['job']['seed']==2026104600+i
        for arm in ('initial','control','curriculum'):
            root=a.run/'DEV'/f'pair-{i:02d}'/arm;target=a.out/f'DEV-{i:02d}-{arm}'
            call([str(LAB/'venv/bin/python'),str(PACKAGE/'audit_game_v6.py'),str(root/'native'),str(target)],a.out/f'DEV-{i:02d}-{arm}.log')
            audit=read(target/'AUDIT.json');assert audit==read(root/'raw-audit/AUDIT.json')
            replay=a.out/f'CPU-{i:02d}-{arm}.json'
            call([str(LAB/'venv/bin/python'),str(HERE/'independent-evidence-01/replay_priorzero_arm.py'),'--policy',str(POLICY),'--raw',str(root/'native'),'--out',str(replay)],a.out/f'CPU-{i:02d}-{arm}.log')
            r=read(replay);assert r['CPU_full_proposals_recomputed']==audit['actual_decisions_checked']
            assert r['victory']==pair['arms'][arm]['win'] and r['recruited_quantity']==pair['arms'][arm]['recruited_amount']
            assert r['counts'].get('recruit',0)==audit['actual_recruits_checked']
            assert r['model_sha256']==(INITIAL_SHA if arm=='initial' else training[arm]['checkpoint_sha256'])
            cpu.append(dict(pair=i,arm=arm,win=r['victory'],decisions=r['CPU_full_proposals_recomputed'],recruits=r['counts'].get('recruit',0),recruited_quantity=r['recruited_quantity'],replay_sha256=sha(replay)))
            devrows+=r['CPU_full_proposals_recomputed'];rawhashes.update({str(root/'native'/path):h for path,h in audit['raw_sha256'].items()})
        (a.out/'PROGRESS.json').write_text(json.dumps(dict(completed_DEV_pairs=i+1,full_CPU_decisions=devrows)))
    wins={arm:sum(x['win'] for x in cpu if x['arm']==arm) for arm in ('initial','control','curriculum')};assert wins==dev['arm_wins']
    assert all(sha(path)==h for path,h in rawhashes.items()) and all(sha(path)==h for path,h in frozen.items())
    report=dict(passed=True,training=training,TRAIN_pairing=pairing,unique_TRAIN_games=16,TRAIN_decisions=trainrows,raw_audits_reexecuted=40,unique_DEV_games=24,DEV_full_CPU_proposals_recomputed=devrows,DEV_wins=wins,DEV=cpu,all_raw_artifact_sha256=rawhashes,model_promoted=False,final_test_touched=False,new_native_games=0,new_optimizer_steps=0)
    (a.out/'AUDIT.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k not in ('DEV','all_raw_artifact_sha256')},indent=2))
if __name__=='__main__':main()
