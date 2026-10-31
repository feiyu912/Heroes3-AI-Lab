"""Independent full native and CPU-proposal re-audit of fixed12 TRAIN calibration."""
from pathlib import Path
import argparse,hashlib,json,subprocess,time
ROOT=Path('/mnt/g/Heroes3-AI-Lab');HERE=Path(__file__).resolve().parent
PACKAGE=ROOT/'experiments/strategic-active-opponent-curriculum-v2-20261023'
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def call(command,log):
    with log.open('w') as out:run=subprocess.run(command,stdout=out,stderr=subprocess.STDOUT)
    assert run.returncode==0,log
def main():
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False,parents=True)
    plan=read(a.run/'PLAN.json');assert len(plan['jobs'])==12 and plan['TRAIN_only'] and not plan['DEV_read'] and plan['optimizer_steps']==0
    rows=[];proposals=0
    for i,item in enumerate(plan['jobs']):
        folder=a.run/f'cell-{i:02d}';saved=folder/'raw-audit/AUDIT.json'
        while not saved.exists():
            if (a.run/'RESULT.json').exists():assert read(a.run/'RESULT.json')['passed'],'Invalid calibration cell; retain partial review'
            time.sleep(1)
        call(['/root/heroes3-ai-lab/venv/bin/python',str(PACKAGE/'audit_game.py'),str(folder/'native'),str(a.out/f'raw-{i:02d}')],a.out/f'raw-{i:02d}.log')
        fresh=read(a.out/f'raw-{i:02d}/AUDIT.json');assert fresh==read(saved)
        replay=a.out/f'replay-{i:02d}.json'
        call(['/root/heroes3-ai-lab/venv/bin/python',str(HERE/'replay_priorzero_arm.py'),'--policy',str(ROOT/'experiments/strategic-learned-recruitment-policy-v3'),'--raw',str(folder/'native'),'--out',str(replay)],a.out/f'replay-{i:02d}.log')
        r=read(replay);assert r['CPU_full_proposals_recomputed']==fresh['actual_decisions_checked'] and r['model_sha256']==plan['checkpoint_sha256']
        assert r['counts'].get('recruit',0)==fresh['actual_recruits_checked']
        proposals+=r['CPU_full_proposals_recomputed']
        rows.append(dict(cell=i,job=item['job'],win=r['victory'],decisions=r['CPU_full_proposals_recomputed'],recruits=r['counts'].get('recruit',0),creatures=r['recruited_quantity'],raw_audit_sha256=sha(saved),fresh_raw_audit_sha256=sha(a.out/f'raw-{i:02d}/AUDIT.json'),full_CPU_replay_sha256=sha(replay)))
        (a.out/'PROGRESS.json').write_text(json.dumps(dict(cells=len(rows),complete_CPU_proposals=proposals,final_certificate=False)))
    while not (a.run/'RESULT.json').exists():time.sleep(1)
    result=read(a.run/'RESULT.json');assert result['passed'] and len(result['results'])==12
    for r,s in zip(rows,result['results']):assert r['job']==s['job'] and r['win']==s['win']
    wins={m:sum(r['win'] for r in rows if r['job']['multiplier']==m) for m in (1,2,4)}
    selected=next((m for m in (2,4) if wins[m]>=2),None)
    assert selected==result['selection']['selected_multiplier'] and {str(k):v for k,v in wins.items()}==result['selection']['wins_by_multiplier']
    assert all(sha(p)==h for p,h in plan['input_sha256'].items())
    report=dict(passed=True,unique_TRAIN_calibration_games=12,complete_native_audits_rerun=12,complete_CPU_proposals_recomputed=proposals,wins_by_multiplier=wins,selected_multiplier=selected,cells=rows,new_native_games=0,GPU_operations=0,optimizer_steps=0,expert_labels=0,independent_strength_claim=False,final_test_touched=False)
    (a.out/'AUDIT.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='cells'},indent=2))
if __name__=='__main__':main()
