"""One serial diagnostic native game. Explicit Ubuntu resources and inherited locks."""
import argparse,fcntl,json,os,shutil,signal,subprocess,time
from pathlib import Path
from boundary_common import HERE,PROFILE,RESOURCE,LEASE_SOURCE,REGISTRY_SOURCE,SUPPORT_SOURCE,CONTRACT,leases,support,registry,fixture,load,sha,write,validate_capsule,verify_native_fds,verify_source_freeze

def memory(out,phase,initial=False):
 values={k:int(v.split()[0]) for k,v in (line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines())}
 item=dict(phase=phase,available_mib=values['MemAvailable']/1024,swap_mib=(values['SwapTotal']-values['SwapFree'])/1024)
 with (out/'RESOURCES.jsonl').open('a') as f:f.write(json.dumps(item)+'\n')
 assert item['available_mib']>(4096 if initial else 2048) and item['swap_mib']<256,'Resource gate failed'

def run(args):
 verify_source_freeze()
 assert os.environ.get('LAB_ADV_THREAT_REPLAN') in (None,'','off')
 assert not os.environ.get('LAB_ADV_MODE')
 assert os.environ.get('LAB_ADV_LEARNED_ECONOMY') in (None,'','build_recruit_v1')
 assert Path(os.environ['HEROES3_RESOURCE_ROOT']).resolve()==RESOURCE.resolve()
 assert Path(os.environ['HEROES3_RUNTIME_ROOT']).resolve()==(PROFILE/'runtime').resolve()
 assert Path(os.environ['HEROES3_LAB_ROOT']).resolve()==(PROFILE/'heroes3-ai-lab').resolve()
 python=Path(os.environ['LAB_PYTHON']);assert python.is_file()
 pin=validate_capsule(args.capsule,args.arm);manifest,f=fixture(args.case)
 if args.execute:
  admission=load(HERE/'RUN_ADMISSION.json')
  assert admission['passed'] is True and admission['source_freeze_sha256']==sha(HERE/'SOURCE_FREEZE.json')
  assert args.case in admission['allowed_cases'] and admission['fixture_sha256'][args.case]==f['sha256']
  assert admission['capsule_attestation_sha256'][args.arm]==sha(args.capsule/'BUILD_ATTESTATION.json')
 capsule=args.capsule.resolve();work=args.out.resolve();bins=capsule/'bin'
 assert args.seconds==f['max_seconds'],'Timeout is preregistered; make a new experiment rather than relax it'
 work.mkdir(parents=True,exist_ok=False)
 result=dict(schema='refill-boundary-native-execution-v1',game_completed=False,transport_drained=False,client_exit=None,broker_exit=None,training_samples=0,optimizer_steps=0,final_test_touched=False,arm=args.arm,case=args.case)
 handles=[];child=None;broker=None;loaded={};freeze={};entries=[];native_fd_proof=[]
 try:
  memory(work,'before',True)
  for path in leases.PATHS:
   assert path.is_file(),'Never silently create a new lock namespace'
   handle=path.open('a+');handles.append(handle);fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
  entries=[leases.metadata(h,p) for h,p in zip(handles,leases.PATHS)]
  leaseproof=leases.verify(entries,leases.PATHS);write(work/'LEASES.json',leaseproof)
  for directory in ('config','data/vcmi/config','data/vcmi/Maps/adv','agent','cache'):(work/directory).mkdir(parents=True,exist_ok=True)
  shutil.copytree(bins/'config',work/'config',dirs_exist_ok=True)
  shutil.copytree(capsule/'source-snapshot/scripts',work/'scripts')
  expected_scripts={r for r,e in pin['manifest'].items() if r.startswith('scripts/') and 'sha256' in e}
  actual_scripts={str(p.relative_to(work)) for p in (work/'scripts').rglob('*') if p.is_file()}
  assert actual_scripts==expected_scripts and actual_scripts
  for rel in actual_scripts:assert sha(work/rel)==pin['manifest'][rel]['sha256']
  assets=PROFILE/'runtime/game-assets/vcmi'
  (work/'vcmiclient').symlink_to(bins/'vcmiclient');(work/'Mods').symlink_to(assets/'Mods')
  for name in ('Data','Mods'):(work/'data/vcmi'/name).symlink_to(assets/name)
  source=Path(f['path']);mapname=source.stem;shutil.copy2(source,work/'data/vcmi/Maps/adv'/source.name)
  settings=dict(mods=dict(validation='off'),general=dict(music=0,sound=0,showIntro=False),adventure=dict(enemyMoveTime=0,heroMoveTime=0),server=dict(seed=f['seed'],useProcess=False),session=dict(onlyai=True))
  for folder in (work/'config',work/'data/vcmi/config'):
   write(folder/'settings.json',settings);write(folder/'modSettings.json',dict(activePreset='adv',presets=dict(adv=dict(mods=['core','vcmi'],settings={}))))
   for name in ('persistentStorage.json','keyBindingsConfig.json'):write(folder/name,{})
  shutil.copytree(work/'config',work/'initial-config');shutil.copytree(work/'data/vcmi/config',work/'initial-user-config')
  inputs=set(pin['inputs']+[Path(manifest['source']),Path(manifest['native_water_metadata']),source,HERE/'FIXTURE_MANIFEST.json',HERE/'SOURCE_FREEZE.json',HERE/'PLAN.md',LEASE_SOURCE,REGISTRY_SOURCE,SUPPORT_SOURCE,PROFILE/'runtime/env.sh',PROFILE/'runtime/native-paths.so'])
  inputs.update(HERE.glob('*.py'))
  if args.execute:inputs.add(HERE/'RUN_ADMISSION.json')
  for root in (assets,PROFILE/'runtime/runtime-libs',PROFILE/'heroes3-ai-lab/onnxruntime/lib',work/'scripts',work/'initial-config',work/'initial-user-config'):
   inputs.update(p for p in root.rglob('*') if p.is_file())
  freeze={str(p):sha(p) for p in sorted(inputs)}
  plan=dict(schema='refill-boundary-plan-v1',capsule=str(capsule),arm=args.arm,case=args.case,map=mapname,seed=f['seed'],owned_player=f['owned_player'],opponent=f['opponent'],classification='diagnostic_only',checkpoint=None,sampling='scripted_actual_candidates_no_PPO',training_samples=0,optimizer_steps=0,final_test_used=False,action_schema=f['schema'],economy_epoch=('learned-economy-build-recruit-v1' if f['mode']=='build_recruit_v1' else 'learned-economy-build-v1' if f['mode']=='build_v1' else None),threat_replan='off',contract_sha256=sha(CONTRACT),hashes=freeze,resource_locks=entries,seconds=args.seconds)
  write(work/'PLAN.json',plan)
  if not args.execute:
   result['stop_reason']='prepared_only_no_native_launch';return 0
  env=dict(os.environ,LD_LIBRARY_PATH=str(bins)+':'+str(PROFILE/'runtime/runtime-libs')+':'+str(PROFILE/'heroes3-ai-lab/onnxruntime/lib'),CUDA_VISIBLE_DEVICES='',SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',XDG_DATA_HOME=str(work/'data'),XDG_CONFIG_HOME=str(work),XDG_CACHE_HOME=str(work/'cache'),LAB_ADV_AI_0=f['opponent'],LAB_ADV_AI_1='DirectorAI',LAB_ADV_TRACE=str(work/'strategy-trace.jsonl'),LAB_ADV_DECISIONS=str(work/'strategy-decisions.jsonl'),LAB_ADV_AGENT_DIR=str(work/'agent'),LAB_ADV_TYPED_EVENTS=str(work/'typed.jsonl'),LAB_ADV_THREAT_REPLAN='off',LAB_ADV_LEARNED_ECONOMY=f['mode'],LAB_ADV_BUILD_PACKS=str(work/'build-packs.jsonl'),TERMINAL_CREDIT_LEASES=json.dumps(entries),TERMINAL_CREDIT_POOL_LEASE=json.dumps(entries[1]),REFILL_NATIVE_LEASE_PROOF=str(work/'NATIVE_LEASES.json'))
  (work/'build-packs.jsonl').touch(exist_ok=False)
  pass_fds=tuple(h.fileno() for h in handles)
  with (work/'broker.log').open('w') as blog,(work/'client.log').open('w') as clog:
   broker=subprocess.Popen([str(python),str(HERE/'selector.py'),'--agent-dir',str(work/'agent'),'--case',args.case,'--idle-seconds',str(args.seconds+30)],env=env,pass_fds=pass_fds,stdout=blog,stderr=subprocess.STDOUT,start_new_session=True)
   leases.ACTIVE_GROUPS.add(broker.pid)
   ready_start=time.monotonic()
   while not (work/'agent/broker-ready.json').exists():
    assert broker.poll() is None,'Broker exited before ready'
    assert time.monotonic()-ready_start<30,'Broker startup timeout'
    time.sleep(.01)
   ready=load(work/'agent/broker-ready.json');assert ready['lease_verified'] and ready['device']=='cpu' and not ready['neural_network']
   child=subprocess.Popen([str(python),str(HERE/'lease_exec.py'),str(work/'vcmiclient'),'--headless','--testmap','Maps/adv/'+mapname,'--nointro','--disable-video','--savefrequency','1'],cwd=work,env=env,pass_fds=pass_fds,stdout=clog,stderr=subprocess.STDOUT,start_new_session=True)
   leases.ACTIVE_GROUPS.add(child.pid)
   start=time.monotonic();last_memory=start
   while child.poll() is None:
    for observed in support.session_evidence(child.pid,bins):
     if not observed['libraries']:continue
     assert observed['valid'],'Actual executable/library identity mismatch'
     previous=loaded.get(observed['pid'],{});threads={r['tid']:r for r in previous.get('run_server_threads',[])};threads.update({r['tid']:r for r in observed['run_server_threads']});observed['run_server_threads']=list(threads.values());loaded[observed['pid']]=observed
     if not native_fd_proof:native_fd_proof=verify_native_fds(observed['pid'],entries)
    log=(work/'client.log').read_text(errors='replace')
    assert 'Script layer not found' not in log,'Missing native Lua script layer'
    # Raw audit later verifies the complete flushed JSONL and log mirrors.
    assert '"event":"typed_protocol_error"' not in log,'Typed native protocol error'
    assert time.monotonic()-start<args.seconds,'engineering_timeout'
    if time.monotonic()-last_memory>5:memory(work,'native_live');last_memory=time.monotonic()
    time.sleep(.005)
   result['client_exit']=child.returncode
  assert result['client_exit']==0,'Native client did not exit normally'
  assert not leases.live_group_members(child.pid),'Client descendants survived exit'
  log=(work/'client.log').read_text(errors='replace')
  events=[json.loads(line) for line in (work/'typed.jsonl').read_text().splitlines() if line]
  result['game_completed']=any(e['event']=='game_over' and e.get('completed') is True and e['player']==f['owned_player'] for e in events)
  result['transport_drained']=result['game_completed'] and registry.MARKER in log
  result['thread_server_verification']=support.thread_server_gate(list(loaded.values()),log,False)
  result['drain']=registry.verify(log,f['owned_player'])
  assert native_fd_proof and load(work/'NATIVE_LEASES.json')['inherited_flock_verified']
  result['stop_reason']='native_completed_normal_drain'
 except BaseException as error:
  result['error']=repr(error);result['stop_reason']='engineering_stop'
 finally:
  # Own both subprocess sessions until all their live descendants have ended.
  for process in (child,broker):
   if process is not None:
    if process.poll() is None or leases.live_group_members(process.pid):
     try:leases.stop_group(process)
     except BaseException as error:result['cleanup_error']=repr(error)
  leases.finish_owned_groups()
  result['client_exit']=None if child is None else child.returncode;result['broker_exit']=None if broker is None else broker.returncode
  result['loaded_library_observations']=list(loaded.values());result['native_inherited_fd_observations']=native_fd_proof
  result['optional_raw_target_logs']={str(p.relative_to(work)):sha(p) for p in sorted(work.glob('strategy-trace.jsonl.*')) if p.is_file()}
  result['input_sha_unchanged']=bool(freeze) and all(sha(p)==h for p,h in freeze.items())
  result['owned_children_cleaned_before_release']=all(p is None or not leases.live_group_members(p.pid) for p in (child,broker))
  result['passed']=bool(args.execute and result.get('stop_reason')=='native_completed_normal_drain' and result['game_completed'] and result['transport_drained'] and result['input_sha_unchanged'] and result['owned_children_cleaned_before_release'])
  write(work/'EXECUTION.json',result)
  for handle in reversed(handles):handle.close()
 return 0 if result['passed'] else 1

def interrupt(signum,frame):raise KeyboardInterrupt('Diagnostic collector interrupted')
def main():
 p=argparse.ArgumentParser();p.add_argument('--capsule',type=Path,required=True);p.add_argument('--arm',choices=['baseline','candidate'],required=True);p.add_argument('--case',choices=['reachable-stock-control','unreachable-stock','nonowned-stock','arrive-incompatible-stock','consumed-pickup','legacy-build','legacy-v4'],required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--seconds',type=float,default=180);p.add_argument('--execute',action='store_true');a=p.parse_args()
 return run(a)
if __name__=='__main__':
 signal.signal(signal.SIGINT,interrupt);signal.signal(signal.SIGTERM,interrupt)
 raise SystemExit(main())
