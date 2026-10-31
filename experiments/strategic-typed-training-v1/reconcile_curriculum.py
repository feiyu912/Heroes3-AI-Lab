"""Preserve failed observer report; derive complete ledger from eight raw-certified cells."""
import hashlib,json
from pathlib import Path
from load_admitted import load
HERE=Path(__file__).resolve().parent
ROOT=Path('/root/heroes3-ai-lab/evaluations/typed-onpolicy-balanced-ack-01')
OUT=HERE/'balanced-ack-certified-01';OUT.mkdir(exist_ok=False)
plan=json.loads((ROOT/'PLAN.json').read_text());entries=[];all_rows=[];all_manifest=[]
for i,job in enumerate(plan['jobs']):
    directory=ROOT/f'cell-{i:02d}/admitted' if i<7 else ROOT.parent/'typed-onpolicy-balanced-ack-reconcile-01/admitted'
    rows,manifest,report=load(directory);e=manifest[0]
    assert (e['job']['map'],e['job']['opponent'],e['job']['owned_player'],e['job']['seed'],e['job']['logical_update'])==(job['map'],job['opponent'],job['player'],job['seed'],job['logical_update'])
    assert e['checkpoint_sha256']==plan['checkpoint_sha256'] and e['transport_drained'] is True
    entries.append(dict(cell=i,job=job,admission=str(directory),admission_sha256=hashlib.sha256((directory/'AUDIT.json').read_bytes()).hexdigest(),episode_id=e['episode_id'],reward=e['reward'],decisions=len(rows),policy_end_turns=report['policy_end_turns']))
    all_rows.extend(rows);all_manifest.extend(manifest)
assert len({e['episode_id'] for e in entries})==8
assert all(e['runtime']==all_manifest[0]['runtime'] for e in all_manifest)
assert {e['reward'] for e in entries}=={-1.,1.},'No mixed terminal signal'
result=dict(passed=True,episodes=entries,rows=len(all_rows),policy_end_turns=sum(e['policy_end_turns'] for e in entries),
    wins=sum(e['reward']==1 for e in entries),losses=sum(e['reward']==-1 for e in entries),same_parent_policy=True,
    same_runtime_epoch=True,last_cell_final_event_reconciled_from_original_raw=True,additional_native_games=0,optimizer_steps=0,
    original_failed_batch_result_sha256=hashlib.sha256((ROOT/'RESULT.json').read_bytes()).hexdigest())
(OUT/'RESULT.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='episodes'},indent=2))
