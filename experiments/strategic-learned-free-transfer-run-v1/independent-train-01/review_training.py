"""Read live admitted/readout counts; --final actually reruns eight strict raw audits on CPU."""
import argparse,ast,collections,hashlib,json,os,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;RUN=HERE.parent
sys.path.insert(0,str(RUN))
import pipeline_common as common
def read(p):return json.loads(Path(p).read_text())
def safe(p):
 try:return read(p)
 except (FileNotFoundError,json.JSONDecodeError):return None
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rows(p):return [json.loads(s) for s in Path(p).read_text().splitlines() if s]
def summary(train):
 cells=[]
 for i in range(8):
  case=train/f'cell-{i:02d}';e=safe(case/'admitted/episode.json');a=safe(case/'admitted/AUDIT.json');n=safe(case/'raw-audit/AUDIT.json')
  if not(e and a and n and e.get('valid') is True and a.get('passed') is True and n.get('whole_game_valid') is True):continue
  assert e['raw_audit_sha256']==sha(case/'raw-audit/AUDIT.json') and a['samples_admitted']==e['decisions']
  assert e['job']['seed']==2026103700+i and e['job']['logical_update']==0
  assert e['checkpoint_sha256']==common.INITIAL_SHA
  assert all(sha(case/'admitted'/p)==h for p,h in a['output_sha256'].items())
  cells.append(dict(cell=i,episode_id=e['episode_id'],job=e['job'],rows=e['decisions'],reward=e['reward'],policy_moves=a['policy_moves'],policy_builds=a['policy_builds'],policy_end_turns=a['policy_end_turns'],prewindow_transfers=n['prewindow_evidence']['prewindow_transfers'],terminal_day=next(t['day'] for t in reversed(rows(case/'native/strategy-trace.jsonl')) if t['event'] in ['victory','defeat']),cuda_admission_replay_certificate_passed=a['replay_actions_logprobs_values_rng_exact'],admission_cuda_replay_rerun_here=False))
 update=safe(train/'update-01/RESULT.json');outer=safe(train/'RESULT.json')
 completed=bool(update and update.get('completed_update') is True)
 return dict(admitted_cells=len(cells),admitted_rows=sum(x['rows'] for x in cells),wins=sum(x['reward']==1 for x in cells),losses=sum(x['reward']==-1 for x in cells),policy_builds=sum(x['policy_builds'] for x in cells),policy_end_turns=sum(x['policy_end_turns'] for x in cells),prewindow_transfers=sum(x['prewindow_transfers'] for x in cells),cells=cells,
  update_complete_from_actual_readout=completed,reported_cuda_optimizer_steps=update.get('cuda_optimizer_steps') if update else None,reported_optimizer_steps_total=update.get('optimizer_steps_total') if update else None,outer_pipeline_passed=outer.get('passed') if outer else None,
  gradient_evidence='Actual update RESULT readout only; no steps inferred from directories, rows or expected minibatches. No optimizer/GPU execution by this review.')
def main():
 p=argparse.ArgumentParser();p.add_argument('--train',type=Path,default=Path('/root/heroes3-ai-lab/evaluations/strategic-learned-free-transfer-train-01'));p.add_argument('--out',type=Path);p.add_argument('--final',action='store_true');a=p.parse_args();s=summary(a.train)
 if not a.final:
  print(json.dumps({k:v for k,v in s.items() if k!='cells'},indent=2));return
 assert a.out is not None and not a.out.exists();a.out.mkdir(parents=True)
 assert s['admitted_cells']==8 and s['outer_pipeline_passed'] is True and s['update_complete_from_actual_readout']
 b=common.require_qualification();common.validate_capsule(common.DEFAULT_CAPSULE)
 frozen=read(RUN/'SOURCE_FREEZE.json');assert all(sha(p)==h for p,h in frozen['source_sha256'].items())
 trainplan=read(a.train/'PLAN.json');assert all(sha(p)==h for p,h in trainplan['input_sha256'].items())
 proof=read(b['prewindow_qualification_report']);assert proof['passed'] and proof['training_samples']==proof['optimizer_steps']==0
 from free_transfer_evidence import verify
 for case in proof['cases']:
  n=Path(case['folder']);q=rows(n/'agent/typed-broker.jsonl');flow=verify((n/'client.log').read_text(errors='replace'),q,folder=n)
  assert all(sha(n/p)==h for p,h in case['raw_sha256'].items()) and flow['passed']
 raw_reviews=[];episodes=[]
 for i in range(8):
  case=a.train/f'cell-{i:02d}';n=case/'native';dest=a.out/f'raw-{i:02d}'
  proc=subprocess.run([sys.executable,str(RUN/'audit_game_v6.py'),str(n),str(dest)],capture_output=True,text=True,env=dict(os.environ,CUDA_VISIBLE_DEVICES=''))
  (a.out/f'audit-{i:02d}.log').write_text(proc.stdout+'\nSTDERR:\n'+proc.stderr);assert proc.returncode==0,f'raw cell{i} failed'
  actual=read(dest/'AUDIT.json');assert actual==read(case/'raw-audit/AUDIT.json')
  assert actual['prewindow_evidence_verified'] and actual['whole_game_valid']
  e=read(case/'admitted/episode.json');ad=read(case/'admitted/AUDIT.json');samples=rows(case/'admitted/samples.jsonl');proposals=rows(n/'agent/typed-broker.jsonl')
  assert len(samples)==len(proposals)==e['decisions']==ad['samples_admitted']
  assert all(sha(path)==h for path,h in ad['input_sha256'].items())
  assert all(sha(case/'admitted'/path)==h for path,h in ad['output_sha256'].items())
  for sample,proposal in zip(samples,proposals):
   assert sample['request']==proposal['request']
   assert sample['episode_id']==e['episode_id'] and sample['valid'] is True and sample['execution_verified'] is True
  assert ad['sampling_device']=='cuda' and ad['replay_actions_logprobs_values_rng_exact'] is True
  episodes.append(e);raw_reviews.append(dict(cell=i,raw_audit_actually_rerun=True,full_audit_json_exact=True,rows=len(samples),admission_cuda_replay_certificate_verified_only=True))
  print(json.dumps(dict(raw_reaudits_finished=i+1,total=8)),flush=True)
 common.validate_cells(episodes)
 update=read(a.train/'update-01/RESULT.json');assert sha(update['checkpoint'])==update['checkpoint_sha256']
 assert update['training_updates']==1 and update['optimizer_steps_total']==update['cuda_optimizer_steps'] and update['progress']['completed'] is True
 report=dict(passed=True,summary=s,actual_raw_audits_rerun=8,raw_reviews=raw_reviews,qualified_fixture_excluded_from_training=True,complete_eight_cells_same_parent_verified=True,source_capsule_and_wrapper_proof_verified=True,checkpoint_sha256=update['checkpoint_sha256'],optimizer_steps_from_actual_readout=update['cuda_optimizer_steps'],cuda_admission_replay_rerun=False,gpu_restore_rerun=False,native_games_started=0,gpu_runs=0,optimizer_steps_executed_here=0)
 (a.out/'REVIEW.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ['summary','raw_reviews']},indent=2))
if __name__=='__main__':main()
