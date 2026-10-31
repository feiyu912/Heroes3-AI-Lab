"""Independent16 native/NN re-audit of the fixed post-pilot control validation."""
from pathlib import Path
import argparse,hashlib,json,subprocess
HERE=Path(__file__).resolve().parent
PACKAGE=HERE.parent/'strategic-control-replication-20261024'
POLICY=HERE.parent/'strategic-active-opponent-policy-v4'
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def call(command,log):
    with log.open('w') as stream:r=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT)
    assert r.returncode==0,str(log)
def main():
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    result=read(a.run/'RESULT.json');freeze=read(PACKAGE/'SOURCE_FREEZE.json');assert result['passed'] and len(result['pairs'])==8
    assert all(sha(path)==h for path,h in freeze['files'].items())
    rows=[];total=0;rawhashes={}
    for index,pair in enumerate(result['pairs']):
        rep=index//4;cell=(2,3,6,7)[index%4];assert pair['job']['rep']==rep and pair['job']['cell']==cell and pair['job']['seed']==(2026108800,2026108900)[rep]+cell
        for arm in ('initial','control'):
            root=a.run/f'pair-{index:02d}'/arm;target=a.out/f'raw-{index:02d}-{arm}'
            call(['/root/heroes3-ai-lab/venv/bin/python',str(PACKAGE/'audit_game_v6.py'),str(root/'native'),str(target)],a.out/f'raw-{index:02d}-{arm}.log')
            audit=read(target/'AUDIT.json');assert audit==read(root/'raw-audit/AUDIT.json')
            replay=a.out/f'CPU-{index:02d}-{arm}.json'
            call(['/root/heroes3-ai-lab/venv/bin/python',str(HERE/'independent-evidence-01/replay_priorzero_arm.py'),'--policy',str(POLICY),'--raw',str(root/'native'),'--out',str(replay)],a.out/f'CPU-{index:02d}-{arm}.log')
            cpu=read(replay);assert cpu==read(root/'CPU-REPLAY.json') and cpu['victory']==pair['arms'][arm]['win'] and cpu['CPU_full_proposals_recomputed']==audit['actual_decisions_checked']==pair['arms'][arm]['decisions']
            plan=read(root/'native/PLAN.json');assert plan['DEV_only'] and plan['replication_only'] and plan['seed']==pair['job']['seed']
            native_map=root/'native/data/vcmi/Maps/adv'/(pair['job']['map']+'.vmap');registered=Path('/root/heroes3-ai-lab/data/vcmi/Maps/adv')/native_map.name
            assert sha(native_map)==sha(registered)==freeze['files'][str(registered)]
            assert all(sha(path)==h for path,h in plan['hashes'].items())
            rows.append(dict(pair=index,job=pair['job'],arm=arm,win=cpu['victory'],decisions=cpu['CPU_full_proposals_recomputed'],full_CPU_replay_sha256=sha(replay),raw_audit_sha256=sha(target/'AUDIT.json')))
            total+=cpu['CPU_full_proposals_recomputed'];rawhashes.update({str(root/'native'/path):h for path,h in audit['raw_sha256'].items()})
        assert pair['initial_request_equal'] and sha(a.run/f'pair-{index:02d}/initial/native/agent/request-00000001.json')==sha(a.run/f'pair-{index:02d}/control/native/agent/request-00000001.json')
        (a.out/'PROGRESS.json').write_text(json.dumps(dict(pairs=index+1,complete_CPU_decisions=total)))
    wins={arm:sum(r['win'] for r in rows if r['arm']==arm) for arm in ('initial','control')};assert wins==result['wins'] and total==result['full_CPU_proposals_recomputed']
    assert all(sha(path)==h for path,h in rawhashes.items()) and all(sha(path)==h for path,h in freeze['files'].items())
    report=dict(passed=True,unique_native_games=16,complete_raw_audits_rerun=16,complete_CPU_proposals_recomputed=total,wins=wins,positive_flips=result['positive_flips'],negative_flips=result['negative_flips'],all8_initial_public_requests_equal=True,rows=rows,raw_sha256=rawhashes,post_pilot_followup=True,new_native_games=0,optimizer_steps=0,PPO_samples_admitted=0,model_promoted=False,final_test_touched=False)
    (a.out/'AUDIT.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k not in ('rows','raw_sha256')},indent=2))
if __name__=='__main__':main()
