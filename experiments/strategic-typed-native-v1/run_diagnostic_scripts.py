"""Real typed transport probe; four diagnostic decisions, controlled nonterminal stop."""
import argparse,json,os,shutil,signal,subprocess,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'multihero-mechanism-probe-v1/build-driver-frozen-03'))
from capsule_support import idle_locks,sha,write,session_evidence,thread_server_gate
LAB=Path('/root/heroes3-ai-lab');BROKER=HERE.parent/'strategic-policy-v3/broker.py'

def stop(child):
    if child is None:return
    try:os.killpg(child.pid,signal.SIGTERM)
    except ProcessLookupError:pass
    try:child.wait(timeout=5)
    except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()

def run(capsule,work):
    capsule=capsule.resolve();work=work.resolve();att=json.loads((capsule/'EXECUTION.json').read_text())
    assert att['passed'] and att['accepted_binaries_restored'] and not att['rebuild_required']
    assert all(sha(capsule/p)==h for p,h in att['candidate_artifacts'].items())
    bins=capsule/'bin';work.mkdir(parents=True,exist_ok=False)
    for d in ['config','data/vcmi/config','data/vcmi/Maps/adv','agent','cache']:(work/d).mkdir(parents=True,exist_ok=True)
    shutil.copytree(bins/'config',work/'config',dirs_exist_ok=True)
    shutil.copytree(LAB/'src/vcmi-adv/scripts',work/'scripts')
    source_manifest=json.loads((capsule/'build-source-manifest.json').read_text())
    script_inputs=[p for p in (work/'scripts').rglob('*') if p.is_file()]
    assert {str(p.relative_to(work)) for p in script_inputs}=={p for p,e in source_manifest.items() if p.startswith('scripts/') and 'sha256' in e}
    assert script_inputs and all(sha(p)==source_manifest[str(p.relative_to(work))]['sha256'] for p in script_inputs)
    (work/'vcmiclient').symlink_to(bins/'vcmiclient');(work/'Mods').symlink_to(LAB/'data/vcmi/Mods')
    for name in ['Data','Mods']:(work/'data/vcmi'/name).symlink_to(LAB/'data/vcmi'/name)
    source=LAB/'data/vcmi/Maps/adv/takeover-v2-train-01-mines.vmap'
    assert source.is_file(),str(source)
    shutil.copy2(source,work/'data/vcmi/Maps/adv'/source.name)
    settings=dict(mods=dict(validation='off'),general=dict(music=0,sound=0,showIntro=False),adventure=dict(enemyMoveTime=0,heroMoveTime=0),server=dict(seed=2026102601,useProcess=False),session=dict(onlyai=True))
    for d in [work/'config',work/'data/vcmi/config']:
        write(d/'settings.json',settings);write(d/'modSettings.json',dict(activePreset='adv',presets=dict(adv=dict(mods=['core','vcmi'],settings={}))))
        for n in ['persistentStorage.json','keyBindingsConfig.json']:write(d/n,{})
    shutil.copytree(work/'config',work/'initial-config');shutil.copytree(work/'data/vcmi/config',work/'initial-user-config')
    inputs=[Path(__file__),source,BROKER,capsule/'EXECUTION.json']+script_inputs+list((HERE.parent/'strategic-policy-v3').glob('*.py'))+list((work/'initial-config').rglob('*.json'))+list((work/'initial-user-config').rglob('*.json'))
    frozen={str(p):sha(p) for p in inputs};write(work/'PLAN.json',dict(capsule=str(capsule),seed=2026102601,classification='diagnostic_only',max_responses=4,training_samples=0,optimizer_steps=0,winner=None,game_completed=False,hashes=frozen))
    env=dict(os.environ,LD_LIBRARY_PATH=str(bins),SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',XDG_DATA_HOME=str(work/'data'),XDG_CONFIG_HOME=str(work),XDG_CACHE_HOME=str(work/'cache'),LAB_ADV_AI_0='DirectorAI',LAB_ADV_AI_1='EmptyAI',LAB_ADV_TRACE=str(work/'strategy-trace.jsonl'),LAB_ADV_DECISIONS=str(work/'strategy-decisions.jsonl'),LAB_ADV_AGENT_DIR=str(work/'agent'),LAB_ADV_TYPED_EVENTS=str(work/'typed.jsonl'))
    loaded={};child=None;broker=None;result={'controlled_stop':False,'game_completed':False,'winner':None,'optimizer_steps':0,'training_samples':0}
    with idle_locks(),(work/'broker.log').open('w') as blog,(work/'client.log').open('w') as log:
        try:
            broker=subprocess.Popen([str(LAB/'venv/bin/python'),str(BROKER),'--agent-dir',str(work/'agent'),'--mode','diagnostic-only','--diagnostic-action','alternate','--max-requests','4'],stdout=blog,stderr=subprocess.STDOUT,start_new_session=True)
            start=time.monotonic()
            while not (work/'agent/broker-ready.json').exists():
                assert broker.poll() is None,'Broker exited before ready'
                assert time.monotonic()-start<30,'Broker startup timeout'
                time.sleep(.01)
            child=subprocess.Popen([str(work/'vcmiclient'),'--headless','--testmap','Maps/adv/takeover-v2-train-01-mines','--nointro','--disable-video','--savefrequency','1'],cwd=work,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            while child.poll() is None:
                for o in session_evidence(child.pid,bins):
                    if not o['libraries']:continue
                    previous=loaded.get(o['pid'],{})
                    old={t['tid']:t for t in previous.get('run_server_threads',[])};old.update({t['tid']:t for t in o['run_server_threads']});o['run_server_threads']=list(old.values());loaded[o['pid']]=o
                    assert o['valid'],'Loaded capsule identity mismatch'
                path=work/'typed.jsonl';rows=[json.loads(s) for s in path.read_text().splitlines()] if path.exists() else []
                if 'Script layer not found' in (work/'client.log').read_text(errors='replace'):result['stop_reason']='missing_required_native_script';break
                if any(r['event']=='typed_protocol_error' for r in rows):result['stop_reason']='typed_protocol_error';break
                if any(r['event']=='package_applied' and r['decision_id']==4 for r in rows):result.update(controlled_stop=True,stop_reason='fourth_diagnostic_action_ACK');break
                if time.monotonic()-start>45:result['stop_reason']='engineering_timeout';break
                time.sleep(.005)
        finally:
            stop(child);stop(broker)
            result['client_exit']=None if child is None else child.returncode
            result['broker_exit']=None if broker is None else broker.returncode
    result['loaded_library_observations']=list(loaded.values())
    result['input_sha_unchanged']=all(sha(Path(p))==h for p,h in frozen.items())
    try:result['thread_server_verification']=thread_server_gate(list(loaded.values()),(work/'client.log').read_text(errors='replace'),False)
    except AssertionError as error:result['thread_server_verification']={'passed':False,'error':str(error)}
    write(work/'EXECUTION.json',result);print(json.dumps(result,indent=2))
    return 0 if result['controlled_stop'] and result['input_sha_unchanged'] and result['thread_server_verification']['passed'] else 1

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--capsule',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    raise SystemExit(run(a.capsule,a.out))
