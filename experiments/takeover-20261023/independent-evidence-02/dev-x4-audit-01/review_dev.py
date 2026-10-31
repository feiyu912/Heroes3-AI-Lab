"""Independent 32-unique-game four-arm raw audits and strict CPU full NN replay."""
import argparse,hashlib,json,subprocess,time
from pathlib import Path
ROOT=Path('/mnt/g/Heroes3-AI-Lab');RUN=ROOT/'experiments/strategic-learned-recruitment-run-v2';HERE=Path(__file__).parent
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(command,log):
 r=subprocess.run(command,capture_output=True,text=True);log.write_text(r.stdout+'\nSTDERR:\n'+r.stderr);assert r.returncode==0,r.stderr
def main():
 p=argparse.ArgumentParser();p.add_argument('--dev',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--follow-completed-arms',action='store_true');a=p.parse_args()
 plan=load(a.dev/'PLAN.json')
 if a.follow_completed_arms:result=dict(pairs=[dict(index=i,job=job,arms={k:None for k in ['minus4_initial','minus4_updated','zero_initial','zero_updated']}) for i,job in enumerate(plan['jobs'])])
 else:
  result=load(a.dev/'RESULT.json');assert result['passed'] and len(result['pairs'])==8
 assert plan['training_samples']==plan['optimizer_steps']==0 and not plan['finaltest_touched']
 assert all(sha(Path(path))==h for path,h in plan['input_sha256'].items())
 arms=['minus4_initial','minus4_updated','zero_initial','zero_updated'];assert set(plan['model_sha256'])==set(arms)
 a.out.mkdir(exist_ok=False,parents=True);pairs=[];replays=0;raw_dirs=[];inputs={}
 for pair in result['pairs']:
  i=pair['index'];assert pair['job']['seed']==2026104200+i and set(pair['arms'])==set(arms)
  current=dict(pair=i,job=pair['job'],arms={});requests={}
  for arm in arms:
   folder=a.dev/f'pair-{i:02d}'/arm;raw=folder/'native';review=a.out/f'raw-{i:02d}-{arm}';raw_dirs.append(str(raw.resolve()))
   while not (folder/'raw-audit/AUDIT.json').exists():
    if (a.dev/'RESULT.json').exists():assert load(a.dev/'RESULT.json')['passed'],'Parent evaluation failed before all32 native arms'
    time.sleep(1)
   run(['/root/heroes3-ai-lab/venv/bin/python',str(RUN/'audit_game_v6.py'),str(raw),str(review)],a.out/f'raw-{i:02d}-{arm}.log')
   fresh=load(review/'AUDIT.json');assert fresh==load(folder/'raw-audit/AUDIT.json')
   policy=ROOT/'experiments'/('strategic-learned-recruitment-policy-v2' if arm.startswith('minus4') else 'strategic-learned-recruitment-policy-v3')
   replaypath=a.out/f'replay-{i:02d}-{arm}.json'
   run(['/root/heroes3-ai-lab/venv/bin/python',str(HERE/'replay_arm.py'),'--policy',str(policy),'--raw',str(raw),'--out',str(replaypath)],a.out/f'replay-{i:02d}-{arm}.log')
   replay=load(replaypath);assert replay['model_sha256']==plan['model_sha256'][arm]
   assert replay['CPU_full_proposals_recomputed']==fresh['actual_decisions_checked']
   assert replay['counts'].get('recruit',0)==fresh['actual_recruits_checked']
   win=fresh['winner']==('red' if pair['job']['player']==0 else 'blue');assert win==replay['victory']
   if not a.follow_completed_arms:assert win==pair['arms'][arm]['win']
   replays+=replay['CPU_full_proposals_recomputed'];requests[arm]=replay.pop('requests')
   replay.update(actual_free_transfers=fresh['actual_transfers_checked']);current['arms'][arm]=replay
   inputs[str(folder/'raw-audit/AUDIT.json')]=sha(folder/'raw-audit/AUDIT.json')
   (a.out/'PROGRESS.json').write_text(json.dumps(dict(actual_complete_raw_audits_rerun=len(inputs),CPU_proposals_recomputed=replays,not_a_final_certificate=True),indent=2)+'\n')
  current['comparisons']=[]
  for aa,bb in [('minus4_initial','zero_initial'),('minus4_updated','zero_updated'),('minus4_initial','minus4_updated'),('zero_initial','zero_updated')]:
   prefix=0;first_action=None
   for qa,qb in zip(requests[aa],requests[bb]):
    if qa['request_sha256']!=qb['request_sha256']:break
    prefix+=1
    if first_action is None and qa['action']!=qb['action']:first_action=qa['request_id']
   current['comparisons'].append(dict(arms=[aa,bb],identical_public_request_prefix=prefix,first_different_action_on_identical_request=first_action))
  pairs.append(current)
 assert len(raw_dirs)==len(set(raw_dirs))==32
 while not (a.dev/'RESULT.json').exists():time.sleep(1)
 result=load(a.dev/'RESULT.json');assert result['passed'] and len(result['pairs'])==8
 wins={arm:sum(pair['arms'][arm]['victory'] for pair in pairs) for arm in arms};assert wins==result['arm_wins']
 summaries={arm:dict(wins=wins[arm],rows=sum(p['arms'][arm]['CPU_full_proposals_recomputed'] for p in pairs),recruits=sum(p['arms'][arm]['counts'].get('recruit',0) for p in pairs),recruited_quantity=sum(p['arms'][arm]['recruited_quantity'] for p in pairs),free_transfers=sum(p['arms'][arm]['actual_free_transfers'] for p in pairs),builds=sum(p['arms'][arm]['counts'].get('build',0) for p in pairs),income_builds=sum(p['arms'][arm]['counts'].get('income_builds',0) for p in pairs),town_moves=sum(p['arms'][arm]['own_town_moves'] for p in pairs),observed_owned_unit_count_decreases=sum(p['arms'][arm]['observed_owned_unit_count_decreases'] for p in pairs)) for arm in arms}
 out=dict(passed=True,unique_native_games_reviewed=32,actual_complete_raw_audits_rerun=32,all_complete_raw_audits_equal=True,actual_complete_CPU_proposals_recomputed=replays,strict_epoch_specific_brokers_used=True,arm_summary=summaries,pairs=pairs,input_sha256=inputs,native_runs_by_reviewer=0,GPU_calls=0,optimizer_steps=0,ability_improvement_claim=False,finaltest_touched=False,limitation='Small historically seen DEV map set; public unit decreases are not separately certified combat casualties. Prior0 is manual initialization, not learned expertise.')
 (a.out/'AUDIT.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k not in ['pairs','input_sha256']},indent=2))
if __name__=='__main__':main()

