"""Prepare-only by default. Explicit independent baseline/candidate stages; never compiles."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
EXP=HERE.parent
LAB=Path('/root/heroes3-ai-lab')
NATIVE=LAB/'src/vcmi-adv'
BIN=LAB/'src/vcmi-adv-build/bin'
DIRECTOR=NATIVE/'AI/DirectorAI/CDirectorAI.cpp'
V2=EXP/'strategic-policy-v2'
VECTOR=EXP/'strategic-vector-v1'
CHECKPOINT=VECTOR/'native-cuda-boundary-clean-4env-01/continuous-2/update-2.pt'
WEIGHT_SHA='9a6b15c6be3866d61d8af5fe830471089c39972e57eee6e326828213d5453159'
BASE_SHA='e198e32f9d3c787e14d575f2fe1c33bba44a8d1351403ffc833c54e4a3079b00'
CAND_SHA='9a8dda3d323691f597ee5ffea70dcd82a9aa4f8f5081cb0e4231b7cabfdd0541'
SERVER_SHA={
 'server/CGameHandler.h':'7f0b41235e28b7854e92600d4b1ee31cb4ce33aa51454ff40af7abf7024342d9',
 'server/CGameHandler.cpp':'d7c0b037dfaacd7bcb9f0a801ac19b024da281a2262eb9049bb8e1afed750755',
 'server/battles/BattleProcessor.cpp':'ac38eaa096f2cc8156fc9ff733046ca5b90650b57b75185fedfaf805f50d8565'}
SEEDS=(2026101881,2026101882)
MAPS=('Maps/adv/takeover-v2-train-01-mines','Maps/adv/takeover-v2-train-02-development')

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path,data):
 temp=path.with_suffix(path.suffix+'.tmp');temp.write_text(json.dumps(data,indent=2));os.replace(temp,path)
def hashes(paths):return {str(p):sha(p)for p in sorted(set(paths))}
def verify(values):
 if not all(Path(p).is_file()and sha(p)==s for p,s in values.items()):raise ValueError('Frozen input changed/missing')

def jobs():
 return [dict(pair_index=i,map=m,role=r,seed=s,opponent='Nullkiller2')
         for i,(m,r,s)in enumerate((m,r,s)for m in MAPS for r in ('red','blue')for s in SEEDS)]

def native_sources():
 return hashes(p for p in NATIVE.rglob('*')if p.is_file()and '.git'not in p.parts
               and p.suffix.lower()in ('.cpp','.h','.hpp','.json','.cmake','.in','.txt'))

def binaries():
 return hashes([BIN/'vcmiclient',BIN/'vcmiserver',BIN/'libvcmi.so']+
               [p for p in BIN.rglob('*.so*')if p.is_file()])

def common_files():
 files=[CHECKPOINT,EXP/'adventure_runner_v5.py',VECTOR/'collect_vector.py',VECTOR/'evaluate_dev.py']
 files+=list(V2.glob('*.py'))+list((EXP/'strategic-policy-v1').glob('*.py'))
 files+=list(HERE.glob('*.py'))+[HERE/n for n in ('PHASE_A_NATIVE_PREREG.md','LAUNCHER_PROTOCOL.md','CANDIDATE_MANIFEST.json',
         'baseline-CDirectorAI.cpp','candidate-CDirectorAI.cpp','candidate.diff')]
 files+=[LAB/('data/vcmi/'+m+'.vmap')for m in MAPS]
 files+=[p for p in (BIN/'config').rglob('*')if p.is_file()]
 files+=[p for p in (LAB/'data/vcmi/Mods').rglob('*.json')if p.is_file()]
 files+=list((EXP/'cpu-simulator-throughput-v1').glob('*.py'))
 return hashes(files)

def compare_sources(baseline,current,stage):
 if set(baseline)!=set(current):raise ValueError('Native source set changed')
 allowed={str(DIRECTOR)}if stage=='candidate'else set()
 changed={p for p in baseline if baseline[p]!=current[p]}
 if changed!=allowed:raise ValueError('Unexpected native source delta: '+repr(changed))
 expected=CAND_SHA if stage=='candidate'else BASE_SHA
 if current.get(str(DIRECTOR))!=expected:raise ValueError('Director differs from reviewed source')
 for rel,value in SERVER_SHA.items():
  if current.get(str(NATIVE/rel))!=value:raise ValueError('Server barrier source changed: '+rel)

def seed_values(value,key=''):
 if isinstance(value,dict):
  return [v for k,x in value.items()for v in seed_values(x,k)]
 if isinstance(value,list):return [v for x in value for v in seed_values(x,key)]
 return [value]if isinstance(value,int)and not isinstance(value,bool)and('seed'in key.lower())else[]

def seed_conflicts(root):
 found=[]
 for p in root.rglob('*.json'):
  if p.parent==HERE or '__pycache__'in p.parts:continue
  if not any(token in p.name.lower()for token in ('plan','execution','training','result','episode','config','index','metadata','protocol')):continue
  try:
   if p.stat().st_size>12_000_000:continue
   data=json.loads(p.read_text())
  except (OSError,ValueError,UnicodeError):continue
  overlap=set(seed_values(data))&set(SEEDS)
  if overlap:found.append(dict(file=str(p),seeds=sorted(overlap)))
 return found

def repeat_seed_coverage(reference):
 old=json.loads((reference/'plan.json').read_text())
 if old['jobs']!=jobs()or old['checkpoint_sha256']!=WEIGHT_SHA:
  raise ValueError('Repeat must preserve complete original jobs and model')
 state=json.loads((reference/'baseline/results.json').read_text())
 if state['status']!='failed':raise ValueError('Only explicit failed engineering protocol can be repeated here')
 allowed=[reference.resolve()]
 for summary in reference.glob('baseline/*/smoke-result.json'):
  record=json.loads(summary.read_text())
  allowed.extend([Path(record['agent_dir']).resolve(),Path(record['native_result']['run_dir']).resolve()])
 return allowed

def prepare(out,repeat_of=None):
 if out.exists():raise ValueError('Fresh output required')
 if sha(CHECKPOINT)!=WEIGHT_SHA:raise ValueError('Wrong fixed trained checkpoint')
 if sha(HERE/'baseline-CDirectorAI.cpp')!=BASE_SHA or sha(HERE/'candidate-CDirectorAI.cpp')!=CAND_SHA:
  raise ValueError('Review source changed')
 collisions=seed_conflicts(EXP)+seed_conflicts(LAB/'workers')+seed_conflicts(LAB/'evaluations')
 allowed=repeat_seed_coverage(repeat_of)if repeat_of else[]
 unexpected=[row for row in collisions if not any(Path(row['file']).resolve().is_relative_to(root)for root in allowed)]
 if unexpected:raise ValueError('Native seed collision outside explicit failed-protocol repeat: '+json.dumps(unexpected))
 sources=native_sources();compare_sources(sources,sources,'baseline')
 plan=dict(schema='threat-response-phase-a-native-v1',status='prepared_only',jobs=jobs(),
  stages=['baseline','candidate'],checkpoint=str(CHECKPOINT),checkpoint_sha256=WEIGHT_SHA,
  source_hashes=sources,baseline_binaries=binaries(),common_hashes=common_files(),
  interpreter=sys.executable,timeout_seconds=120,broker_mode='new-policy',policy_override=False,
  source_expected=dict(baseline=BASE_SHA,candidate=CAND_SHA),server_expected=SERVER_SHA,
  seed_index_check=dict(conflicts=collisions,unexpected=[],scanned_roots=[str(EXP),str(LAB/'workers'),str(LAB/'evaluations')],
       method='Seed-named fields in plan/execution/training/result/episode/config/index/metadata/protocol JSON <=12MB'),
  repeat_of=str(repeat_of.resolve())if repeat_of else None,
  repeat_plan_sha256=sha(repeat_of/'plan.json')if repeat_of else None,
  engineering_repeat_not_new_capability_samples=bool(repeat_of),
  optimizer_steps=0,mechanism_development=True,learning_improvement=False,test_split_touched=False)
 out.mkdir();write(out/'plan.json',plan)
 snap=out/'source-snapshot';snap.mkdir()
 selected=[Path(p)for p in plan['common_hashes']if Path(p).suffix in ('.py','.md','.cpp')]
 selected +=[DIRECTOR,NATIVE/'AI/DirectorAI/CDirectorAI.h']+[NATIVE/p for p in SERVER_SHA]
 for i,p in enumerate(dict.fromkeys(selected)):shutil.copy2(p,snap/f'{i:03d}-{p.name}')
 write(out/'status.json',dict(status='prepared_only',games_started=0,optimizer_steps=0))
 return plan

def validate_build(build,current_binaries):
 if build.get('candidate_source_sha256')!=CAND_SHA or build.get('binaries')!=current_binaries:
  raise ValueError('Candidate build attestation differs from current full runtime')

def terminal_tail(states):
 terminals=[(i,n,s)for i,(n,s)in enumerate(states)if s['event']in ('victory','defeat')]
 if len(terminals)!=1:raise ValueError('Exactly one terminal required')
 def payload(state):return json.dumps({k:v for k,v in state.items()if k!='event'},sort_keys=True,separators=(',',':'),allow_nan=False)
 i,line,state=terminals[0];expected_payload=payload(state)
 tail=[]
 for n,s in states[i+1:]:
  if s['event']!='native_battle_ready'or payload(s)!=expected_payload:
   raise ValueError('Forbidden terminal event/state change')
  tail.append(dict(line=n,event=s['event']))
 return dict(terminal_line=line,transport=tail)

def audit(summary_path,stage):
 sys.path.insert(0,str(VECTOR));sys.path.insert(0,str(V2))
 from evaluate_dev import verify_native_consumption
 from audit_supply_raw import audit_episode,records
 smoke=json.loads(summary_path.read_text());native=smoke['native_result'];agent=Path(smoke['agent_dir'])
 if smoke.get('mode')!='new-policy'or native.get('winner')not in ('red','blue'):raise ValueError('Wrong mode/terminal')
 io=verify_native_consumption(agent,native,WEIGHT_SHA)
 raw=audit_episode(summary_path)
 states=records(Path(native['run_dir'])/'strategy-trace.jsonl');tail=terminal_tail(states)
 releases=[n for n,s in states if s['event']=='threat_commit_released']
 if stage=='baseline'and releases:raise ValueError('Baseline emitted candidate event')
 text=(Path(native['run_dir'])/'client.log').read_text(errors='replace').splitlines()
 rejected=[dict(line=i,text=s)for i,s in enumerate(text,1)if any(x in s for x in
   ('Got false in applying','Player is not allowed','has to answer queries before attempting'))]
 qsent=sum('Sending a request "10QueryReply"'in s for s in text)
 qdone=sum('Message 10QueryReply successfully applied!'in s for s in text)
 if rejected or qsent!=qdone:raise ValueError('Native rejection/query service gate failed')
 from threat_contract import release_gate
 decisions=records(Path(native['run_dir'])/'strategy-decisions.jsonl')
 before=[(n,s)for n,s in states if s['event']=='before_move']
 if len(before)!=len(decisions):raise ValueError('Decision/trace count mismatch')
 by_line={n:(d,json.loads((agent/f'request-{i:08d}.json').read_text()))for i,((n,_),(_,d))in enumerate(zip(before,decisions),1)}
 commits={};proofs=[];switches=0;reversals=0;previous_moves={}
 for n,s in states:
  if s['event']=='turn_start':commits.clear();previous_moves.clear()
  elif s['event']=='threat_commit_released':
   following=next((line for line,_ in before if line>n),None)
   if following is None:raise ValueError('Release lacks following real decision')
   d,request=by_line[following];hero=d['hero']
   if hero not in commits or not release_gate(request)['keep_full_native_candidates']:
    raise ValueError('Release lacks actual prior commit/visible-pressure proof')
   proofs.append(dict(trace_line=n,request_id=request['request_id'],prior_commit=commits.pop(hero),
                      request_sha256=sha(agent/f'request-{request["request_id"]:08d}.json'),candidate_count=len(request['candidates'])))
  elif s['event']=='before_move':
   d,r=by_line[n];hero=d['hero'];chosen=r['candidates'][d['selected_candidate']]
   previous=previous_moves.get(hero)
   if previous:
    switches+=previous['destination']!=d['destination']
    reversals+=previous['from']==d['step']and previous['step']==d['from']
   previous_moves[hero]=d
   commits[hero]=dict(destination=d['destination'],kind=chosen['kind'])
 return dict(passed=True,raw=raw,io_native_execution=io,terminal_tail_transport=tail,
             release_lines=releases,query_replies=qsent,rejection_lines=rejected,
             release_proofs=proofs,same_turn_target_switches=switches,same_turn_step_reversals=reversals,
             optimizer_steps=0,learning_improvement=False)

def run_stage(out,stage,build_manifest):
 plan=json.loads((out/'plan.json').read_text());verify(plan['common_hashes'])
 current=native_sources();compare_sources(plan['source_hashes'],current,stage)
 runtime=binaries()
 if stage=='baseline':
  if runtime!=plan['baseline_binaries']:raise ValueError('Baseline runtime changed since prepare')
 else:
  state=json.loads((out/'baseline/results.json').read_text())
  if state['status']!='completed'or len(state['rows'])!=8:raise ValueError('All eight valid baselines required first')
  verify(state['immutable_evidence'])
  if build_manifest is None:raise ValueError('Explicit compiled-candidate build manifest required')
  validate_build(json.loads(build_manifest.read_text()),runtime)
  if runtime==plan['baseline_binaries']:raise ValueError('Candidate has not changed any built binary')
 arm=out/stage;arm.mkdir(exist_ok=False)
 frozen=dict(plan['common_hashes'],**current,**runtime)
 if build_manifest:frozen[str(build_manifest.resolve())]=sha(build_manifest)
 write(arm/'input-freeze.json',dict(hashes=frozen,build_manifest_sha256=sha(build_manifest)if build_manifest else None))
 report=dict(status='running',stage=stage,rows=[],optimizer_steps=0,learning_improvement=False)
 write(arm/'results.json',report);proc=None;start=time.monotonic()
 sys.path.insert(0,str(V2));from run_supply_pilot import terminate_owned
 def stop(*_):raise InterruptedError('Explicit stop; no timeout/loss imputation')
 oldterm=signal.signal(signal.SIGTERM,stop);oldint=signal.signal(signal.SIGINT,stop)
 try:
  for job in plan['jobs']:
   verify(frozen);episode=arm/f"{job['pair_index']:02d}";episode.mkdir()
   assigned=dict(red='DirectorAI'if job['role']=='red'else'Nullkiller2',blue='DirectorAI'if job['role']=='blue'else'Nullkiller2')
   cmd=[sys.executable,str(V2/'smoke_game.py'),'--mode','new-policy','--checkpoint',plan['checkpoint'],
        '--map',job['map'],'--red',assigned['red'],'--blue',assigned['blue'],'--seed',str(job['seed']),
        '--seconds','120','--tag',f'threat-a-{out.name}-{stage}-{job["pair_index"]}']
   with (episode/'smoke.log').open('w')as log:
    proc=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,
          env=dict(os.environ,CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='1'))
    code=proc.wait() # Native runner holds pool and owns its natural 120s game deadline.
   text=(episode/'smoke.log').read_text();found=re.search(r'^AGENT_DIR=(.+)$',text,re.M)
   if found:
    source=Path(found[1].strip())/'smoke-result.json'
    if source.exists():shutil.copy2(source,episode/'smoke-result.json')
   if code!=0 or not(episode/'smoke-result.json').exists():raise ValueError('Native/protocol game failed')
   summary=json.loads((episode/'smoke-result.json').read_text());native=summary['native_result']
   if(native.get('actual_ai')!=assigned or native['config']['seed']!=job['seed']or native['config']['map']!=job['map']
      or native['config']['seconds']!=120 or native['config'].get('save_file')or native['config'].get('gdb')):
    raise ValueError('Native job/role/seed differs from preregistration')
   verification=audit(episode/'smoke-result.json',stage);write(episode/'RAW_AUDIT.json',verification)
   verify(frozen)
   row=dict(pair_index=job['pair_index'],job=job,won=verification['raw']['won'],audit=str(episode/'RAW_AUDIT.json'),
       summary=str(episode/'smoke-result.json'),main_loss_day=verification['raw']['original_main_loss_day'],
       deliveries=verification['raw']['delivered_count'],releases=len(verification['release_lines']),
       target_switches=verification['same_turn_target_switches'],step_reversals=verification['same_turn_step_reversals'])
   report['rows'].append(row);write(arm/'results.json',report);print(json.dumps(row),flush=True)
  evidence=[arm/'input-freeze.json']+[Path(r[k])for r in report['rows']for k in ('audit','summary')]
  evidence_hash=hashes(evidence)
  for r in report['rows']:
   raw=json.loads(Path(r['audit']).read_text())['raw'];evidence_hash.update(raw['evidence_sha256'])
   for manifest in raw['request_manifest']:
    evidence_hash[manifest['path']]=manifest['sha256']
    action=Path(manifest['path']).with_name(Path(manifest['path']).name.replace('request-','action-',1))
    evidence_hash[str(action)]=manifest['action_sha256']
  report.update(status='completed',wall_seconds=time.monotonic()-start,immutable_evidence=evidence_hash)
  write(arm/'results.json',report)
 except BaseException as problem:
  if proc is not None:terminate_owned(proc)
  report.update(status='failed',error=repr(problem),invalid_not_scored=True,wall_seconds=time.monotonic()-start)
  write(arm/'results.json',report);raise
 finally:
  signal.signal(signal.SIGTERM,oldterm);signal.signal(signal.SIGINT,oldint)
 write(out/'status.json',dict(status=stage+'_completed',games_completed=8 if stage=='baseline'else 16,
       optimizer_steps=0,learning_improvement=False))
 if stage=='candidate':
  baseline=json.loads((out/'baseline/results.json').read_text())
  pairs=[dict(job=a['job'],baseline_win=a['won'],candidate_win=b['won'],win_delta=b['won']-a['won'])
         for a,b in zip(baseline['rows'],report['rows'])]
  if not all(a['job']==b['job']for a,b in zip(baseline['rows'],report['rows'])):raise ValueError('Pair mismatch')
  write(out/'paired-results.json',dict(status='completed',pairs=pairs,net_win_delta=sum(p['win_delta']for p in pairs),
       optimizer_steps=0,mechanism_development=True,learning_improvement=False,
       confidence_interval=None,two_map_clusters=True,no_independent_map_or_strength_certification=True))

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True)
 parser.add_argument('--stage',choices=('baseline','candidate'));parser.add_argument('--execute',action='store_true')
 parser.add_argument('--candidate-build-manifest',type=Path)
 parser.add_argument('--repeat-validation-of',type=Path,help='Explicit failed-protocol engineering repeat; preserves every seed/job/model')
 args=parser.parse_args()
 if not args.execute:
  if args.stage:parser.error('Prepare-only mode has no stage; execution requires explicit --execute')
  prepare(args.out,args.repeat_validation_of);print('Prepared only: zero games, no resource lock');return
 if args.repeat_validation_of:parser.error('Repeat binding is prepare-only and immutable during execution')
 if args.stage is None:parser.error('--execute requires a separate explicit stage')
 run_stage(args.out,args.stage,args.candidate_build_manifest)

if __name__=='__main__':main()
