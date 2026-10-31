"""One on-policy CUDA sampled native episode. No optimizer; admission is separate."""
import argparse,fcntl,hashlib,json,os,shutil,signal,subprocess,sys,time
from contextlib import contextmanager
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'multihero-mechanism-probe-v1/build-driver-frozen-03'))
from capsule_support import idle_locks,sha,write,session_evidence,thread_server_gate
LAB=Path('/root/heroes3-ai-lab');BROKER=HERE/'onpolicy_broker.py'

@contextmanager
def owned_resources():
    handles=[]
    try:
        for name in ['.gpu-learner-lock','.pool-lock']:
            handle=(LAB/'evaluations'/name).open('a+');handles.append(handle)
            fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        yield tuple(h.fileno() for h in handles)
    finally:
        for h in reversed(handles):h.close()

def stop(child):
    if child is None:return
    try:os.killpg(child.pid,signal.SIGTERM)
    except ProcessLookupError:pass
    try:child.wait(timeout=5)
    except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()

def run(args):
    capsule,work,checkpoint=args.capsule,args.out,args.checkpoint
    checkpoint=checkpoint.resolve();assert checkpoint.is_file()
    capsule=capsule.resolve();work=work.resolve();att=json.loads((capsule/'EXECUTION.json').read_text())
    assert att['passed'] and att['accepted_binaries_restored'] and not att['rebuild_required']
    assert all(sha(capsule/p)==h for p,h in att['candidate_artifacts'].items())
    bins=capsule/'bin';work.mkdir(parents=True,exist_ok=False)
    for d in ['config','data/vcmi/config','data/vcmi/Maps/adv','agent','cache']:(work/d).mkdir(parents=True,exist_ok=True)
    shutil.copytree(bins/'config',work/'config',dirs_exist_ok=True)
    # Native damage/spell mechanics are runtime Lua assets. They are part of
    # the compiled epoch's full source manifest, not optional UI resources.
    shutil.copytree(LAB/'src/vcmi-adv/scripts',work/'scripts')
    source_manifest=json.loads((capsule/'build-source-manifest.json').read_text())
    script_inputs=[]
    for p in (work/'scripts').rglob('*'):
        if p.is_file():
            relative=str(p.relative_to(work));assert sha(p)==source_manifest[relative]['sha256'],relative
            script_inputs.append(p)
    expected_scripts={p for p,e in source_manifest.items() if p.startswith('scripts/') and 'sha256' in e}
    assert {str(p.relative_to(work)) for p in script_inputs}==expected_scripts and expected_scripts
    (work/'vcmiclient').symlink_to(bins/'vcmiclient');(work/'Mods').symlink_to(LAB/'data/vcmi/Mods')
    for name in ['Data','Mods']:(work/'data/vcmi'/name).symlink_to(LAB/'data/vcmi'/name)
    source=LAB/('data/vcmi/Maps/adv/'+args.map+'.vmap')
    assert source.is_file(),str(source)
    shutil.copy2(source,work/'data/vcmi/Maps/adv'/source.name)
    settings=dict(mods=dict(validation='off'),general=dict(music=0,sound=0,showIntro=False),adventure=dict(enemyMoveTime=0,heroMoveTime=0),server=dict(seed=args.seed,useProcess=False),session=dict(onlyai=True))
    for d in [work/'config',work/'data/vcmi/config']:
        write(d/'settings.json',settings);write(d/'modSettings.json',dict(activePreset='adv',presets=dict(adv=dict(mods=['core','vcmi'],settings={}))))
        for n in ['persistentStorage.json','keyBindingsConfig.json']:write(d/n,{})
    shutil.copytree(work/'config',work/'initial-config');shutil.copytree(work/'data/vcmi/config',work/'initial-user-config')
    inputs=[Path(__file__),source,BROKER,checkpoint,capsule/'EXECUTION.json']+script_inputs+list((HERE.parent/'strategic-policy-v3').glob('*.py'))+list((work/'initial-config').rglob('*.json'))+list((work/'initial-user-config').rglob('*.json'))
    if args.load_save:
        original=args.load_save.resolve();head=original.read_bytes()[:15]
        assert original.suffix=='.vsgm1' and head[:4]==b'VCMI' and head[8:15]==b'VCMISVG','Native save header required'
        target=work/'data/vcmi/Saves/resume-snapshot.vsgm1';target.parent.mkdir();shutil.copy2(original,target);inputs.extend([original,target])
    seed_material=json.dumps(dict(seed=args.seed,map=args.map,player=args.player,opponent=args.opponent,logical_update=args.logical_update),sort_keys=True).encode()
    sampling_seed=int.from_bytes(hashlib.sha256(seed_material).digest()[:8],'little')%(2**63-1)
    frozen={str(p):sha(p) for p in inputs};write(work/'PLAN.json',dict(capsule=str(capsule),seed=args.seed,map=args.map,owned_player=args.player,opponent=args.opponent,load_save=str(args.load_save) if args.load_save else None,classification='new_policy',checkpoint=str(checkpoint),sampling='onpolicy CUDA multinomial',sampling_seed=sampling_seed,logical_update=args.logical_update,training_samples=0,optimizer_steps=0,winner=None,game_completed=False,hashes=frozen))
    env=dict(os.environ,LD_LIBRARY_PATH=str(bins),SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',XDG_DATA_HOME=str(work/'data'),XDG_CONFIG_HOME=str(work),XDG_CACHE_HOME=str(work/'cache'),LAB_ADV_AI_0='DirectorAI' if args.player==0 else args.opponent,LAB_ADV_AI_1='DirectorAI' if args.player==1 else args.opponent,LAB_ADV_TRACE=str(work/'strategy-trace.jsonl'),LAB_ADV_DECISIONS=str(work/'strategy-decisions.jsonl'),LAB_ADV_AGENT_DIR=str(work/'agent'),LAB_ADV_TYPED_EVENTS=str(work/'typed.jsonl'))
    loaded={};child=None;broker=None;result={'controlled_stop':False,'game_completed':False,'winner':None,'optimizer_steps':0,'training_samples':0}
    with owned_resources() as lease_fds,(work/'broker.log').open('w') as blog,(work/'client.log').open('w') as log:
        try:
            broker=subprocess.Popen([str(LAB/'gpu-venv/bin/python'),str(BROKER),'--agent-dir',str(work/'agent'),'--checkpoint',str(checkpoint),
                '--sampling-seed',str(sampling_seed),'--gpu-lock-fd',str(lease_fds[0]),'--pool-lock-fd',str(lease_fds[1]),
                '--idle-seconds',str(args.seconds+30)],pass_fds=lease_fds,stdout=blog,stderr=subprocess.STDOUT,start_new_session=True)
            start=time.monotonic()
            while not (work/'agent/broker-ready.json').exists():
                assert broker.poll() is None,'Broker exited before ready'
                assert time.monotonic()-start<30,'Broker startup timeout'
                time.sleep(.01)
            ready=json.loads((work/'agent/broker-ready.json').read_text())
            assert ready['mode']=='onpolicy_cuda' and ready['device']=='cuda' and ready['model_sha256']==sha(checkpoint)
            start_args=['--testsave','Saves/resume-snapshot'] if args.load_save else ['--testmap','Maps/adv/'+args.map]
            child=subprocess.Popen([str(work/'vcmiclient'),'--headless']+start_args+['--nointro','--disable-video','--savefrequency','1'],cwd=work,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            while child.poll() is None:
                for o in session_evidence(child.pid,bins):
                    if not o['libraries']:continue
                    previous=loaded.get(o['pid'],{})
                    old={t['tid']:t for t in previous.get('run_server_threads',[])};old.update({t['tid']:t for t in o['run_server_threads']});o['run_server_threads']=list(old.values());loaded[o['pid']]=o
                    assert o['valid'],'Loaded capsule identity mismatch'
                path=work/'typed.jsonl';rows=[json.loads(s) for s in path.read_text().splitlines()] if path.exists() else []
                if 'Script layer not found' in (work/'client.log').read_text(errors='replace'):
                    result['stop_reason']='missing_required_native_script';break
                if any(r['event']=='typed_protocol_error' for r in rows):result['stop_reason']='typed_protocol_error';break
                if any(r['event']=='game_over' and r['completed'] for r in rows):
                    result.update(game_completed=True,stop_reason='native_game_over')
                    time.sleep(.05) # Preserve the final native apply/ACK if it arrives.
                    break
                if time.monotonic()-start>args.seconds:result['stop_reason']='engineering_timeout';break
                time.sleep(.005)
        finally:
            stop(child);stop(broker)
            result['client_exit']=None if child is None else child.returncode
            result['broker_exit']=None if broker is None else broker.returncode
    result['loaded_library_observations']=list(loaded.values())
    result['input_sha_unchanged']=all(sha(Path(p))==h for p,h in frozen.items())
    if args.load_save:
        native_log=(work/'client.log').read_text(errors='replace')
        result['load_markers']={m:m in native_log for m in ['Preparing to start loaded game','Game has been successfully loaded!','Game loaded, initialize interfaces.']}
        result['native_load_verified']=all(result['load_markers'].values())
    try:result['thread_server_verification']=thread_server_gate(list(loaded.values()),(work/'client.log').read_text(errors='replace'),False)
    except AssertionError as error:result['thread_server_verification']={'passed':False,'error':str(error)}
    write(work/'EXECUTION.json',result);print(json.dumps(result,indent=2))
    return 0 if result['game_completed'] and result['input_sha_unchanged'] and result['thread_server_verification']['passed'] and (not args.load_save or result['native_load_verified']) else 1

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--capsule',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--checkpoint',type=Path,required=True)
    p.add_argument('--map',choices=['takeover-v2-train-01-mines','takeover-v2-train-02-development'],default='takeover-v2-train-01-mines')
    p.add_argument('--player',type=int,choices=[0,1],default=0);p.add_argument('--opponent',choices=['EmptyAI','Nullkiller2'],default='EmptyAI')
    p.add_argument('--seed',type=int,default=2026102701);p.add_argument('--seconds',type=float,default=120);p.add_argument('--load-save',type=Path)
    p.add_argument('--logical-update',type=int,default=0);a=p.parse_args()
    assert a.seconds>0
    assert a.logical_update>=0
    raise SystemExit(run(a))
