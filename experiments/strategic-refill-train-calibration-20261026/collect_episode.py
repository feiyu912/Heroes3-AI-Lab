"""Serial original-T1 CUDA calibration; no optimizer and no PPO admission."""
import argparse,json,os,shutil,signal,subprocess,time,traceback
from pathlib import Path
from common import *
from ownership import owned_resources,finish_session,session_processes
def resources(out,phase,initial=False):
 v={k:int(x.split()[0]) for k,x in (line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines())}
 row=dict(phase=phase,available_mib=v['MemAvailable']/1024,swap_mib=(v['SwapTotal']-v['SwapFree'])/1024)
 with (out/'RESOURCES.jsonl').open('a') as stream:stream.write(json.dumps(row)+'\n')
 assert row['available_mib']>(4096 if initial else 2048) and row['swap_mib']<256,'Original resource gate'
def prepare(args):
 verify_freeze();v=validate_job(args.arm,args.seed,args.checkpoint)
 c=CAPSULE_ROOT/args.arm;pin=validate_capsule(c,args.arm);out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
 for name in ('config','data/vcmi/config','data/vcmi/Maps/adv','agent','cache'):(out/name).mkdir(parents=True,exist_ok=True)
 shutil.copytree(c/'bin/config',out/'config',dirs_exist_ok=True)
 shutil.copytree(c/'source-snapshot/scripts',out/'scripts')
 expected={r:e['sha256'] for r,e in pin['manifest'].items() if r.startswith('scripts/') and 'sha256' in e}
 assert {str(p.relative_to(out)):sha(p) for p in (out/'scripts').rglob('*') if p.is_file()}==expected
 assets=PROFILE/'runtime/game-assets/vcmi'
 (out/'vcmiclient').symlink_to(c/'bin/vcmiclient');(out/'Mods').symlink_to(assets/'Mods')
 for name in ('Data','Mods'):(out/'data/vcmi'/name).symlink_to(assets/name)
 canonical,player=REGISTERED[args.seed]
 shutil.copyfile(v['path'],out/('data/vcmi/Maps/adv/'+canonical+'.vmap'))
 settings=dict(mods=dict(validation='off'),general=dict(music=0,sound=0,showIntro=False),adventure=dict(enemyMoveTime=0,heroMoveTime=0),server=dict(seed=args.seed,useProcess=False),session=dict(onlyai=True))
 for folder in (out/'config',out/'data/vcmi/config'):
  write(folder/'settings.json',settings);write(folder/'modSettings.json',dict(activePreset='adv',presets=dict(adv=dict(mods=['core','vcmi'],settings={}))));write(folder/'persistentStorage.json',{});write(folder/'keyBindingsConfig.json',{})
 shutil.copytree(out/'config',out/'initial-config');shutil.copytree(out/'data/vcmi/config',out/'initial-user-config')
 inputs=set(Path(p) for p in verify_freeze()['files'])|set(pin['inputs'])|{HERE/'SOURCE_FREEZE.json',Path(v['path']),INITIAL}
 for root in (out/'scripts',out/'initial-config',out/'initial-user-config'):
  inputs.update(p for p in root.rglob('*') if p.is_file())
 frozen={str(p):sha(p) for p in sorted(inputs)}
 plan=dict(schema='refill-fixed-TRAIN-calibration-plan-v1',pipeline_epoch=EPOCH,arm=args.arm,capsule=str(c),map=canonical,seed=args.seed,owned_player=player,opponent='Nullkiller2',logical_update=0,multiplier=4,map_variant=v,checkpoint=str(INITIAL),checkpoint_sha256=INITIAL_SHA,sampling_seed=sampling_seed(args.seed,canonical,player),sampling='original T1 CUDA multinomial',classification='new_policy',training_samples=0,optimizer_steps=0,new_PPO_admissions=0,final_test_used=False,threat_replan='off',action_schema='strategy-candidates-v6',economy_epoch='learned-economy-build-recruit-v1',seconds=120,hashes=frozen)
 write(out/'PLAN.json',plan)
 write(out/'PREPARED.json',dict(passed=True,native_games=0,GPU_operations=0,optimizer_steps=0,locks_acquired=False))
 return out,plan
def run(args):
 if args.execute:require_native_admission()
 out,plan=prepare(args)
 if not args.execute:return 0
 assert Path(os.environ['HEROES3_RUNTIME_ROOT']).resolve()==(PROFILE/'runtime').resolve()
 assert Path(os.environ['HEROES3_RESOURCE_ROOT']).resolve()==RESOURCE.resolve()
 assert os.environ.get('LAB_ADV_THREAT_REPLAN') in (None,'','off') and not os.environ.get('LAB_ADV_MODE')
 assert os.environ.get('LAB_ADV_LEARNED_ECONOMY') in (None,'','build_recruit_v1')
 python=Path(os.environ['LAB_PYTHON']);bins=Path(plan['capsule'])/'bin'
 admission=HERE/'NATIVE_ADMISSION.json';plan['hashes'][str(admission)]=sha(admission);write(out/'PLAN.json',plan)
 result=dict(passed=False,pipeline_epoch=EPOCH,game_completed=False,transport_drained=False,training_samples=0,new_PPO_admissions=0,optimizer_steps=0)
 broker=child=None;loaded={};fdproof=[]
 resources(out,'before',True)
 with owned_resources(out) as entries:
  env=dict(os.environ,LD_LIBRARY_PATH=':'.join(map(str,(bins,PROFILE/'runtime/runtime-libs',LAB/'onnxruntime/lib'))),XDG_DATA_HOME=str(out/'data'),XDG_CONFIG_HOME=str(out),XDG_CACHE_HOME=str(out/'cache'),SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',LAB_ADV_AI_0='DirectorAI' if plan['owned_player']==0 else 'Nullkiller2',LAB_ADV_AI_1='DirectorAI' if plan['owned_player']==1 else 'Nullkiller2',LAB_ADV_TRACE=str(out/'strategy-trace.jsonl'),LAB_ADV_DECISIONS=str(out/'strategy-decisions.jsonl'),LAB_ADV_AGENT_DIR=str(out/'agent'),LAB_ADV_TYPED_EVENTS=str(out/'typed.jsonl'),LAB_ADV_BUILD_PACKS=str(out/'build-packs.jsonl'),LAB_ADV_THREAT_REPLAN='off',LAB_ADV_LEARNED_ECONOMY='build_recruit_v1',TERMINAL_CREDIT_LEASES=json.dumps(entries),REFILL_NATIVE_LEASE_PROOF=str(out/'NATIVE_LEASES.json'))
  (out/'build-packs.jsonl').touch()
  pass_fds=tuple(e['fd'] for e in entries)
  try:
   with (out/'broker.log').open('w') as blog,(out/'client.log').open('w') as clog:
    broker=subprocess.Popen([str(python),str(HERE/'onpolicy_broker.py'),'--agent-dir',str(out/'agent'),'--checkpoint',str(INITIAL),'--sampling-seed',str(plan['sampling_seed']),'--gpu-lock-fd',str(entries[0]['fd']),'--pool-lock-fd',str(entries[1]['fd']),'--idle-seconds','150'],env=env,pass_fds=pass_fds,stdout=blog,stderr=subprocess.STDOUT,start_new_session=True)
    ready_start=time.monotonic()
    while not (out/'agent/broker-ready.json').exists():
     assert broker.poll() is None and time.monotonic()-ready_start<30,'Broker startup failure';time.sleep(.01)
    ready=load(out/'agent/broker-ready.json');assert ready['mode']=='onpolicy_cuda' and ready['model_sha256']==INITIAL_SHA and ready['device']=='cuda'
    child=subprocess.Popen([str(python),str(HERE/'lease_exec.py'),str(out/'vcmiclient'),'--headless','--testmap','Maps/adv/'+plan['map'],'--nointro','--disable-video','--savefrequency','1'],cwd=out,env=env,pass_fds=pass_fds,stdout=clog,stderr=subprocess.STDOUT,start_new_session=True)
    start=last=time.monotonic()
    while child.poll() is None:
     for observed in support.session_evidence(child.pid,bins):
      if not observed['libraries']:continue
      assert observed['valid'];old=loaded.get(observed['pid'],{});threads={e['tid']:e for e in old.get('run_server_threads',[])};threads.update({e['tid']:e for e in observed['run_server_threads']});observed['run_server_threads']=list(threads.values());loaded[observed['pid']]=observed
      if not fdproof:fdproof=verify_native_fds(observed['pid'],entries)
     text=(out/'client.log').read_text(errors='replace');assert 'Script layer not found' not in text
     assert time.monotonic()-start<120,'engineering_timeout_not_loss'
     if time.monotonic()-last>5:resources(out,'live');last=time.monotonic()
     time.sleep(.005)
    assert child.returncode==0,'Native must exit normally'
    events=[json.loads(x) for x in (out/'typed.jsonl').read_text().splitlines() if x.strip()]
    log=(out/'client.log').read_text(errors='replace')
    assert not any(e['event']=='typed_protocol_error' for e in events)
    assert any(e['event']=='game_over' and e.get('completed') is True for e in events)
    drain=registry.verify(log,plan['owned_player'])
    result.update(game_completed=True,transport_drained=True,drain=drain,thread_server_verification=support.thread_server_gate(list(loaded.values()),log,False))
    assert fdproof
   result['passed']=True
  except BaseException as error:result.update(error=repr(error),traceback=traceback.format_exc())
  finally:
   finish_session(child);finish_session(broker)
   result.update(client_exit=None if child is None else child.returncode,broker_exit=None if broker is None else broker.returncode,loaded_library_observations=list(loaded.values()),native_fd_proof=fdproof,owned_sessions_empty=all(not session_processes(p.pid) for p in (child,broker) if p is not None),input_sha_unchanged=all(sha(p)==h for p,h in plan['hashes'].items()))
   result['passed']=bool(result['passed'] and result['owned_sessions_empty'] and result['input_sha_unchanged'] and result['broker_exit']==0 and (out/'agent/sampling-state.pt').is_file())
   write(out/'EXECUTION.json',result)
 resources(out,'after')
 return 0 if result['passed'] else 1
def main():
 p=argparse.ArgumentParser();p.add_argument('--arm',choices=['baseline','candidate'],required=True);p.add_argument('--seed',type=int,choices=sorted(REGISTERED),required=True);p.add_argument('--checkpoint',type=Path,default=INITIAL);p.add_argument('--out',type=Path,required=True);p.add_argument('--execute',action='store_true');a=p.parse_args()
 def interrupted(sig,frame):raise InterruptedError('Calibration interrupted '+str(sig))
 signal.signal(signal.SIGTERM,interrupted)
 return run(a)
if __name__=='__main__':raise SystemExit(main())
