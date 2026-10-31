"""Read archived legal requests only; never reconstruct pruned native choices."""
from pathlib import Path
import hashlib,json,unittest
from threat_contract import release_gate,choose_existing_retreat_proxy
import test_contract

HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'strategic-economy-v4/acceptance-06'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
suite=unittest.defaultTestLoader.loadTestsFromModule(test_contract)
result=unittest.TextTestRunner().run(suite)
assert result.wasSuccessful()
execution=json.loads((BASE/'EXECUTION.json').read_text());assert execution['status']=='completed'
episodes=[]
for episode in execution['episodes'][4:]:
 auditpath=Path(episode['audit']);audit=json.loads(auditpath.read_text());raw=audit['raw']
 native=Path(raw['native_dir']);agent=Path(raw['agent_dir'])
 states=[(i,json.loads(s))for i,s in enumerate((native/'strategy-trace.jsonl').read_text().splitlines(),1)]
 beforemoves=[i for i,s in states if s['event']=='before_move']
 commits=[json.loads(s)for s in (agent/'broker-trace.jsonl').read_text().splitlines()if json.loads(s)['event']=='decision_committed']
 assert len(beforemoves)==len(commits)
 absence=raw['original_main_first_absent'];main=raw['original_main_id'];rows=[]
 for trace_line,commit in zip(beforemoves,commits):
  path=agent/commit['request_file'];request=json.loads(path.read_text())
  if request['hero']!=main or(absence and trace_line>=absence['line']):continue
  gate=release_gate(request);index,reason=choose_existing_retreat_proxy(request,commit['action'])
  assert 0<=index<len(request['candidates'])
  rows.append(dict(request_id=request['request_id'],day=request['day'],trace_line=trace_line,
      candidate_count=len(request['candidates']),active=gate['keep_full_native_candidates'],
      baseline=commit['action'],cpu_choice=index,reason=reason,request_sha256=sha(path)))
 episodes.append(dict(tag=episode['tag'],requests=len(rows),active=sum(r['active']for r in rows),
     active_single_candidate=sum(r['active']and r['candidate_count']==1 for r in rows),
     existing_candidate_proxy_overrides=sum(r['cpu_choice']!=r['baseline']for r in rows),
     original_raw_audit_sha256=sha(auditpath),rows=rows))
out=HERE/'CPU_REPLAY.json';assert not out.exists()
out.write_text(json.dumps(dict(schema='threat-response-cpu-replay-v1',tests=result.testsRun,passed=True,
 scope='Archived first-life main-hero v3 requests only; no native recalc, counterfactual paths, safety or win evidence',
 candidate_inventions=0,gpu_or_game_runs=0,source_sha256={p.name:sha(p)for p in sorted(HERE.glob('*.py'))},episodes=episodes),indent=2))
print(json.dumps([{k:v for k,v in e.items()if k!='rows'}for e in episodes],indent=2))
