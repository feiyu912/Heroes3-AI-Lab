#!/usr/bin/env python3
"""Future isolated engineering runner. Default is prepare-only; no install/build."""
import argparse,hashlib,json,os,shutil,signal,subprocess,time
from pathlib import Path
from audit_run import audit
from capsule_support import verify_attestation,idle_locks,session_evidence,thread_server_gate
HERE=Path(__file__).resolve().parent
LAB=Path('/root/heroes3-ai-lab')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def run(args):
    args.out=args.out.resolve();args.capsule=args.capsule.resolve()
    attestation=verify_attestation(args.capsule,args.variant)
    args.bin_dir=args.capsule/'bin';args.source_tree=args.capsule/'source-snapshot'
    assert args.bin_dir!= (LAB/'src/vcmi-adv-build/bin').resolve(),'Current training binaries forbidden'
    assert args.source_tree!=(LAB/'src/vcmi-adv').resolve(),'Current training source tree forbidden'
    variant=HERE/'candidates-02'/args.variant
    for name in ('CDirectorAI.cpp','CDirectorAI.h'):
        assert (args.source_tree/'AI/DirectorAI'/name).resolve()!=(LAB/'src/vcmi-adv/AI/DirectorAI'/name).resolve()
        assert sha(args.source_tree/'AI/DirectorAI'/name)==sha(variant/name),'Installed future candidate differs'
    required=[args.bin_dir/name for name in ('vcmiclient','vcmiserver','libvcmi.so')]
    assert all(p.is_file() for p in required)
    # A dynamically linked client can remain byte-identical. Verify compilation
    # attestation and implementation-bearing library, then actual /proc maps.
    manifest=json.loads((HERE.parent/'adv-server-battle-barrier-v1/installed-source-sha256.json').read_text())
    assert all(sha(args.source_tree/path)==digest for path,digest in manifest.items()),'Retain certified server barrier sources'
    assert not os.environ.get('LAB_ADV_AGENT_DIR'),'Policy broker forbidden'
    args.out.mkdir(parents=True,exist_ok=False)
    work=args.out
    for name in ('data/vcmi/Maps/adv','data/vcmi/config','cache'):(work/name).mkdir(parents=True,exist_ok=True)
    shutil.copytree(args.bin_dir/'config',work/'config')
    shutil.copytree(LAB/'src/vcmi-adv/scripts',work/'scripts')
    build_manifest=json.loads((args.capsule/'build-source-manifest.json').read_text())
    script_inputs=[p for p in (work/'scripts').rglob('*') if p.is_file()]
    assert {str(p.relative_to(work)) for p in script_inputs}=={p for p,e in build_manifest.items() if p.startswith('scripts/') and 'sha256' in e}
    assert script_inputs and all(sha(p)==build_manifest[str(p.relative_to(work))]['sha256'] for p in script_inputs)
    # Native Unix developmentMode requires config + Mods + an executable in cwd.
    # These run-local links select the copied config without mutating the capsule.
    (work/'vcmiclient').symlink_to(args.bin_dir/'vcmiclient')
    (work/'Mods').symlink_to(LAB/'data/vcmi/Mods')
    for name in ('Data','Mods'):(work/'data/vcmi'/name).symlink_to(LAB/'data/vcmi'/name)
    fixture=work/'data/vcmi/Maps/adv/multihero-native-mechanism-probe-v1.vmap'
    shutil.copy2(HERE/'fixture-01.vmap',fixture)
    settings={'mods':{'validation':'off'},'general':{'music':0,'sound':0,'showIntro':False},
        'adventure':{'enemyMoveTime':0,'heroMoveTime':0},'server':{'seed':args.seed,'useProcess':False},'session':{'onlyai':True}}
    for folder in (work/'config',work/'data/vcmi/config'):
        (folder/'settings.json').write_text(json.dumps(settings))
        (folder/'modSettings.json').write_text(json.dumps({'activePreset':'adv','presets':{'adv':{'mods':['core','vcmi'],'settings':{}}}}))
        for name in ('persistentStorage.json','keyBindingsConfig.json'):(folder/name).write_text('{}')
    command=[str(work/'vcmiclient'),'--headless','--testmap','Maps/adv/multihero-native-mechanism-probe-v1',
        '--nointro','--disable-video','--savefrequency','1']
    inputs=required+[args.source_tree/'AI/DirectorAI'/n for n in ('CDirectorAI.cpp','CDirectorAI.h')]
    inputs += [args.source_tree/p for p in manifest]+[fixture,Path(__file__),HERE/'audit_run.py',HERE/'capsule_support.py',args.capsule/'BUILD_ATTESTATION.json',args.capsule.parent/'EXECUTION.json',HERE.parent/'adv-server-battle-barrier-v1/installed-source-sha256.json']
    inputs += [args.capsule/path for path in attestation['artifacts']]
    # Native settings persistence rewrites user settings/modSettings. Preserve
    # their exact initial bytes separately; never confuse mutable outputs with
    # the immutable capsule, source, fixture and configuration snapshots.
    initial=work/'initial-config';initial.mkdir()
    for folder,label in ((work/'config','config'),(work/'data/vcmi/config','user-config')):
        shutil.copytree(folder,initial/label)
    inputs += sorted(initial.rglob('*.json'))+script_inputs
    plan={'engineering_only':True,'policy_broker':False,'variant':args.variant,'seed':args.seed,'command':command,
        'source_tree':str(args.source_tree),'bin_dir':str(args.bin_dir),'out':str(work),
        'build_attestation':str(args.capsule/'BUILD_ATTESTATION.json'),'build_kind':attestation['build_kind'],
        'native_server_mode':'thread','settings_server_useProcess':False,
        'hashes':{str(p):sha(p) for p in inputs},'training_samples':0,'optimizer_steps':0,
        'game_completed':False,'winner':None,'execute_requested':args.execute}
    (work/'plan.json').write_text(json.dumps(plan,indent=2))
    if not args.execute:return {'prepared_only':True,'game_started':False}
    env=dict(os.environ,LD_LIBRARY_PATH=str(args.bin_dir),SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',
        XDG_DATA_HOME=str(work/'data'),XDG_CONFIG_HOME=str(work),XDG_CACHE_HOME=str(work/'cache'),
        LAB_ADV_AI_0='DirectorAI',LAB_ADV_AI_1='EmptyAI',LAB_ADV_TRACE=str(work/'strategy-trace.jsonl'),
        LAB_HERO_PROBE_LOG=str(work/'probe.jsonl'))
    env.pop('LAB_ADV_DECISIONS',None)
    execution={'controlled_stop':False,'timed_out':False,'game_completed':False,'winner':None,'optimizer_steps':0}
    loaded={};load_errors=[]
    with idle_locks():
        start=time.monotonic()
        with (work/'client.log').open('w') as log:
            child=subprocess.Popen(command,cwd=work,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            try:
                while child.poll() is None:
                    for observation in session_evidence(child.pid,args.bin_dir):
                        # Loader may not have mapped libvcmi on the first poll.
                        if not observation['libraries']:continue
                        old=loaded.get(str(observation['pid']),{})
                        proof={t['tid']:t for t in old.get('run_server_threads',[])}
                        proof.update({t['tid']:t for t in observation.get('run_server_threads',[])})
                        observation['run_server_threads']=list(proof.values())
                        loaded[str(observation['pid'])]=observation
                        if not observation['valid']:load_errors.append(observation)
                    if load_errors:
                        execution['stop_reason']='loaded_capsule_identity_failure';break
                    events=(work/'probe.jsonl').read_text() if (work/'probe.jsonl').exists() else ''
                    native=(work/'client.log').read_text(errors='replace')
                    if '"event":"endturn_ack"' in events and '"event":"close_ack"' in events:
                        execution['controlled_stop']=True;execution['stop_reason']='proved_EndTurn_ACK';break
                    if args.variant=='original-unhandled' and '"event":"exchange_callback"' in events and ('has to answer queries' in native or 'Got false in applying' in native):
                        execution['controlled_stop']=True;execution['stop_reason']='negative_control_native_query_rejection';break
                    if time.monotonic()-start>args.seconds:
                        execution['timed_out']=True;execution['stop_reason']='engineering_timeout_no_winner';break
                    time.sleep(.01)
            finally:
                try:os.killpg(child.pid,signal.SIGTERM)
                except ProcessLookupError:pass
                try:child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid,signal.SIGKILL);child.wait()
                # Clean only the session this subprocess created, including surviving server children.
                try:os.killpg(child.pid,signal.SIGKILL)
                except ProcessLookupError:pass
                execution['engine_exit']=child.returncode
                execution['wall_seconds']=time.monotonic()-start
    execution['loaded_library_observations']=list(loaded.values())
    execution['loaded_library_errors']=load_errors
    execution['loaded_library_verified']=bool(loaded) and not load_errors and all(o['valid'] for o in loaded.values()) and any(Path(o['executable']).name=='vcmiclient' for o in loaded.values())
    try:execution['thread_server_verification']=thread_server_gate(list(loaded.values()),(work/'client.log').read_text(errors='replace'),settings['server']['useProcess'])
    except AssertionError as error:execution['thread_server_verification']={'passed':False,'mode':'thread','error':str(error)}
    (work/'execution.json').write_text(json.dumps(execution,indent=2))
    try:result=audit(work)
    except Exception as error:result={'engineering_pass':False,'error':repr(error),'game_completed':False,'winner':None,'optimizer_steps':0}
    (work/'AUDIT.json').write_text(json.dumps(result,indent=2));return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--variant',choices=('original-unhandled','close-only','transfer-close'),required=True)
    p.add_argument('--capsule',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--seed',type=int,default=2026102501)
    p.add_argument('--seconds',type=int,default=20);p.add_argument('--execute',action='store_true')
    args=p.parse_args()
    try:result=run(args)
    except BaseException as error:
        result={'engineering_pass':False,'error':repr(error),'winner':None,'game_completed':False}
        if args.out.is_dir():(args.out/'BLOCKED_OR_FAILED.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
    raise SystemExit(0 if result.get('prepared_only') or result.get('engineering_pass') or (
        result.get('negative_control_unhandled_callback_observed') and result.get('native_rejection_observed') and not result.get('execution',{}).get('timed_out')) else 1)
