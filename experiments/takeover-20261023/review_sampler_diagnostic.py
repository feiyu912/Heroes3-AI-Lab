"""Independent raw/CPU re-audit of the four fixed TRAIN diagnostic games."""
import argparse,json,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
PACKAGE=HERE.parent/'strategic-sampler-calibration-diagnostic-20261024'
POLICY=HERE.parent/'strategic-active-opponent-policy-v4'
def read(p):return json.loads(Path(p).read_text())
def sha(p):return __import__('hashlib').sha256(Path(p).read_bytes()).hexdigest()
def call(argv,log):
    with log.open('w') as stream:r=subprocess.run(argv,stdout=stream,stderr=subprocess.STDOUT)
    assert r.returncode==0,str(log)
def main():
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    result=read(a.run/'RESULT.json');freeze=read(PACKAGE/'SOURCE_FREEZE.json');assert result['passed'] and len(result['entries'])==4
    assert [e['job']['index'] for e in result['entries']]==[2,3,6,7]
    assert all(sha(path)==h for path,h in freeze['files'].items())
    assert not freeze['registration']['DEV_result_read'] and not freeze['registration']['DEV_result_completed']
    total=0;rows=[];rawhashes={}
    for e in result['entries']:
        i=e['job']['index'];root=a.run/f'cell-{i:02d}';out=a.out/f'cell-{i:02d}'
        call(['/root/heroes3-ai-lab/venv/bin/python',str(PACKAGE/'audit_game_v6.py'),str(root/'native'),str(out)],a.out/f'raw-{i:02d}.log')
        audit=read(out/'AUDIT.json');assert audit==read(root/'raw-audit/AUDIT.json')
        replay=a.out/f'CPU-{i:02d}.json'
        call(['/root/heroes3-ai-lab/venv/bin/python',str(HERE/'independent-evidence-01/replay_priorzero_arm.py'),'--policy',str(POLICY),'--raw',str(root/'native'),'--out',str(replay)],a.out/f'CPU-{i:02d}.log')
        fresh=read(replay);assert fresh==read(root/'CPU-REPLAY.json')
        assert fresh['victory']==e['argmax_win'] and fresh['CPU_full_proposals_recomputed']==audit['actual_decisions_checked']==e['full_CPU_decisions_recomputed']
        original=Path(e['job']['stochastic_native']);assert sha(original/'PLAN.json')==e['job']['stochastic_plan_sha256'] and sha(original/'agent/typed-broker.jsonl')==e['job']['stochastic_proposals_sha256']
        assert e['first_difference']['step']==1 and e['first_difference']['request_equal'] and e['equal_public_request_action_prefix']==0
        assert sha(root/'native/agent/request-00000001.json')==sha(original/'agent/request-00000001.json')
        device=[r for r in result['device_check']['rows'] if r['cell']==i];assert len(device)==1 and device[0]['CPU_CUDA_argmax_equal']
        assert device[0]['stochastic_selected_action']==e['first_difference']['stochastic_action'] and device[0]['argmax_action']==e['first_difference']['argmax_action']
        total+=fresh['CPU_full_proposals_recomputed'];rows.append(dict(cell=i,argmax_win=e['argmax_win'],stochastic_win=e['stochastic_win'],decisions=fresh['CPU_full_proposals_recomputed'],audit_sha256=sha(out/'AUDIT.json'),CPU_replay_sha256=sha(replay)))
        rawhashes.update({str(root/'native'/path):h for path,h in audit['raw_sha256'].items()})
    assert result['argmax_wins']==sum(r['argmax_win'] for r in rows)==1 and result['stochastic_wins']==0 and total==6487
    assert result['device_check']==read(a.run/'DEVICES.json') and result['device_check']['states_checked']==4
    assert all(sha(path)==h for path,h in rawhashes.items())
    report=dict(passed=True,complete_raw_audits_rerun=4,full_CPU_proposals_recomputed=total,argmax_wins=1,stochastic_wins=0,first_public_request_equal_all4=True,first_action_different_all4=True,CPU_CUDA_first_state_argmax_equal_all4=True,maximum_logit_absolute_difference=max(r['max_logit_abs_difference'] for r in result['device_check']['rows']),minimum_first_state_greedy_action_probability=min(r['CPU_argmax_probability'] for r in result['device_check']['rows']),maximum_first_state_greedy_action_probability=max(r['CPU_argmax_probability'] for r in result['device_check']['rows']),rows=rows,raw_sha256=rawhashes,new_native_games=0,new_GPU_operations=0,optimizer_steps=0,PPO_samples_admitted=0,expert_labels=0,final_test_touched=False,claim='TRAIN-only mode/seed diagnostic; cannot uniquely attribute entire outcome to first action or certify strength')
    (a.out/'AUDIT.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k not in ('rows','raw_sha256')},indent=2))
if __name__=='__main__':main()
