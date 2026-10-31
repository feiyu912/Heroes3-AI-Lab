"""Independent archived evidence and semantic-trajectory review; no native runs."""
from pathlib import Path
import hashlib,json

HERE=Path(__file__).resolve().parent
WORKSPACE=HERE.parents[1]
RUN=HERE.parent/'strategic-threat-response-v1/native-pilot-02'
DIRECTOR='/root/heroes3-ai-lab/src/vcmi-adv/AI/DirectorAI/CDirectorAI.cpp'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(path):return json.loads(Path(path).read_text())
def digest(data):return hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def lines(path):return [json.loads(s)for s in Path(path).read_text().splitlines()if s.strip()]
def verify_manifest(manifest):
 for path,value in manifest.items():assert sha(path)==value,('Evidence changed',path)
def canonical_tail(states):
 term=[i for i,s in enumerate(states)if s['event']in ('victory','defeat')];assert len(term)==1
 target=states[term[0]];payload={k:v for k,v in target.items()if k!='event'}
 for row in states[term[0]+1:]:
  assert row['event']=='native_battle_ready'
  assert digest({k:v for k,v in row.items()if k!='event'})==digest(payload)
 return len(states)-term[0]-1

arms={name:load(RUN/name/'results.json')for name in ('baseline','candidate')}
assert all(a['status']=='completed'and len(a['rows'])==8 for a in arms.values())
for path,value in load(RUN/'baseline-seal.json').items():
 p=Path(path.replace('\\','/'));p=p if p.is_absolute()else WORKSPACE/p
 assert sha(p)==value
for arm in arms.values():verify_manifest(arm['immutable_evidence'])
freezes={a:load(RUN/a/'input-freeze.json')['hashes']for a in arms}
build=load(RUN/'candidate-build.json')
assert set(freezes['candidate'])-set(freezes['baseline'])=={str(RUN/'candidate-build.json')}
changed={p for p in freezes['baseline']if freezes['baseline'][p]!=freezes['candidate'][p]}
assert DIRECTOR in changed and changed-{DIRECTOR} and changed-{DIRECTOR}<=set(build['binaries'])
assert all(freezes['candidate'][p]==value for p,value in build['binaries'].items())
assert freezes['candidate'][DIRECTOR]==build['candidate_source_sha256']
assert load(RUN/'plan.json')['checkpoint_sha256']=='9a6b15c6be3866d61d8af5fe830471089c39972e57eee6e326828213d5453159'

pairs=[];arm_totals={name:dict(wins=0,moves=0,queries=0,releases=0,target_switches=0,step_reversals=0)for name in arms}
for index,(br,cr)in enumerate(zip(arms['baseline']['rows'],arms['candidate']['rows'])):
 assert br['job']==cr['job']and br['pair_index']==cr['pair_index']==index
 data={}
 for name,row in (('baseline',br),('candidate',cr)):
  audit=load(row['audit']);smoke=load(row['summary']);native=smoke['native_result'];raw=audit['raw']
  assert audit['passed']and raw['normal']and smoke['passed']and smoke['io_hashes_verified']and smoke['inputs_unchanged']
  assert native['completed']and not any(native[k]for k in ('timed_out','crashed','interrupted'))
  assert not audit['rejection_lines']and audit['io_native_execution']['native_event_audit']['valid']
  verify_manifest(raw['evidence_sha256'])
  for r in raw['request_manifest']:
   path=Path(r['path']);assert sha(path)==r['sha256']
   assert sha(path.with_name(path.name.replace('request-','action-',1)))==r['action_sha256']
  root=Path(native['run_dir']);states=lines(root/'strategy-trace.jsonl');decisions=lines(root/'strategy-decisions.jsonl')
  tail=canonical_tail(states)
  semantic=[{k:d[k]for k in ('player','day','hero','from','destination','step')}for d in decisions]
  physical=[s for s in states if s['event']!='threat_commit_released']
  requests=[load(Path(raw['agent_dir'])/f'request-{i:08d}.json')for i in range(1,len(decisions)+1)]
  release_proofs=audit['release_proofs']
  assert len(release_proofs)==len(audit['release_lines'])==row['releases']
  data[name]=dict(won=row['won'],days=native['native_calendar_last_day'],main_loss_day=raw['original_main_loss_day'],
      main_status=raw['original_main_status'],delivered=raw['delivered_count'],
      decisions=len(decisions),queries=audit['query_replies'],releases=row['releases'],
      release_single_candidate=sum(p['candidate_count']==1 for p in release_proofs),
      release_multi_candidate=sum(p['candidate_count']>1 for p in release_proofs),
      target_switches=row['target_switches'],step_reversals=row['step_reversals'],
      terminal_ready_rows=tail,native_execution_classification=audit['io_native_execution']['native_event_audit']['classification'],
      semantic=semantic,semantic_sha256=digest(semantic),physical_trace_sha256=digest(physical),requests=requests,
      raw_audit=str(row['audit']),raw_audit_sha256=sha(row['audit']))
  for metric,source in (('wins','won'),('moves','decisions'),('queries','queries'),('releases','releases'),('target_switches','target_switches'),('step_reversals','step_reversals')):
   arm_totals[name][metric]+=data[name][source]
 bs,cs=data['baseline']['semantic'],data['candidate']['semantic']
 first=next((i for i,(b,c)in enumerate(zip(bs,cs),1)if b!=c),None)
 if first is None and len(bs)!=len(cs):first=min(len(bs),len(cs))+1
 common_prefix=min(len(bs),len(cs))if first is None else first-1
 exposures=sum(b['candidates']!=c['candidates']for b,c in zip(data['baseline']['requests'][:common_prefix],data['candidate']['requests'][:common_prefix]))
 pair=dict(index=index,job=br['job'],win_delta=cr['won']-br['won'],
      same_semantic_trajectory=bs==cs,first_semantic_difference=first,
      same_physical_trace_after_excluding_release=data['baseline']['physical_trace_sha256']==data['candidate']['physical_trace_sha256'],
      common_prefix_requests_with_different_candidates=exposures,arms={})
 for name,entry in data.items():pair['arms'][name]={k:v for k,v in entry.items()if k not in ('semantic','requests')}
 pairs.append(pair)
result=dict(schema='threat-response-native-paired-independent-audit-v1',passed=True,
 plan_sha256=sha(RUN/'plan.json'),candidate_build_sha256=sha(RUN/'candidate-build.json'),
 only_input_deltas=sorted(changed),totals=arm_totals,pairs=pairs,
 net_win_delta=sum(p['win_delta']for p in pairs),same_semantic_trajectory_pairs=sum(p['same_semantic_trajectory']for p in pairs),
 optimizer_steps=0,mechanism_development=True,learning_improvement=False,two_map_clusters=True,
 no_independent_map_or_high_winrate_certification=True)
target=HERE/'AUDIT.json';assert not target.exists();target.write_text(json.dumps(result,indent=2))
print(json.dumps({k:v for k,v in result.items()if k!='pairs'},indent=2))
