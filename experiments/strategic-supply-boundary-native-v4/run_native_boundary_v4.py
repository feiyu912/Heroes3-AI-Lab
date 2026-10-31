"""Plan by default. A bounded SCRIPTED mechanism probe, never a whole-game score."""
import argparse,hashlib,json,os,re,shutil,signal,subprocess,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;OLD_FIXTURE=HERE.parent/'strategic-multihero-supply-native-v1';LAB=Path('/root/heroes3-ai-lab')
SUPPLY=HERE.parent/'strategic-multihero-supply-v4'
sys.path.insert(0,str(HERE.parent/'multihero-mechanism-probe-v1/build-driver-frozen-03'))
from capsule_support import idle_locks,session_evidence,thread_server_gate
sys.path.insert(0,str(HERE.parent/'strategic-typed-training-v1'))
from live_jsonl import read as rows
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,indent=2))
def stop(child):
    if child is None:return
    try:os.killpg(child.pid,signal.SIGTERM)
    except ProcessLookupError:pass
    try:child.wait(timeout=5)
    except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--capsule',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--execute',action='store_true');ap.add_argument('--seconds',type=float,default=30);ap.add_argument('--own-turn-cap',type=int,default=6);ap.add_argument('--seed',type=int,default=2026111901)
    ap.add_argument('--mode',choices=['reference','restore'],required=True)
    ap.add_argument('--nonce',default='boundary-01');ap.add_argument('--checkpoint-turn',type=int,default=2)
    ap.add_argument('--load-save',type=Path);ap.add_argument('--bundle',type=Path)
    a=ap.parse_args();assert a.seconds>0 and a.own_turn_cap>=3 and a.checkpoint_turn>=2
    assert re.fullmatch('[A-Za-z0-9_-]{1,64}',a.nonce)
    assert (a.mode=='restore')==bool(a.load_save and a.bundle)
    if a.mode=='reference':assert a.load_save is None and a.bundle is None

    cap=a.capsule.resolve();work=a.out.resolve();att=json.loads((cap/'EXECUTION.json').read_text());assert att['passed'] and att['accepted_binaries_restored']
    assert all(sha(cap/p)==h for p,h in att['candidate_artifacts'].items())
    manifest=json.loads((SUPPLY/'CANDIDATE_MANIFEST.json').read_text());source=json.loads((cap/'build-source-manifest.json').read_text())
    assert len(manifest['files'])>=11
    for relative,e in manifest['files'].items():
        assert sha(SUPPLY/'candidate'/relative)==sha(cap/'source-snapshot'/relative)==source[relative]['sha256']==e['candidate_sha256']
    bins=cap/'bin';work.mkdir(parents=True,exist_ok=False)
    for n in ('config','data/vcmi/config','data/vcmi/Maps/adv','data/vcmi/Saves','cache'):(work/n).mkdir(parents=True,exist_ok=True)
    shutil.copytree(bins/'config',work/'config',dirs_exist_ok=True)
    shutil.copytree(LAB/'src/vcmi-adv/scripts',work/'scripts')
    scripts=[p for p in (work/'scripts').rglob('*') if p.is_file()];assert len(scripts)==41
    assert {str(p.relative_to(work)) for p in scripts}=={p for p in source if p.startswith('scripts/') and 'sha256' in source[p]}
    for p in scripts:assert sha(p)==source[str(p.relative_to(work))]['sha256']
    (work/'vcmiclient').symlink_to(bins/'vcmiclient');(work/'Mods').symlink_to(LAB/'data/vcmi/Mods')
    for n in ('Data','Mods'):(work/'data/vcmi'/n).symlink_to(LAB/'data/vcmi'/n)
    fixture=work/'data/vcmi/Maps/adv/supply-stock-01.vmap';shutil.copy2(OLD_FIXTURE/'supply-stock-01.vmap',fixture)
    settings=dict(mods=dict(validation='off'),general=dict(music=0,sound=0,showIntro=False),adventure=dict(enemyMoveTime=0,heroMoveTime=0),server=dict(seed=a.seed,useProcess=False),session=dict(onlyai=True))
    for folder in (work/'config',work/'data/vcmi/config'):
        write(folder/'settings.json',settings);write(folder/'modSettings.json',dict(activePreset='adv',presets=dict(adv=dict(mods=['core','vcmi'],settings={}))))
        for n in ('persistentStorage.json','keyBindingsConfig.json'):write(folder/n,{})
    shutil.copytree(work/'config',work/'initial-config');shutil.copytree(work/'data/vcmi/config',work/'initial-user-config')
    inputs=[Path(__file__),HERE/'PLAN.md',OLD_FIXTURE/'FIXTURE.json',OLD_FIXTURE/'supply-stock-01.vmap',fixture,SUPPLY/'CANDIDATE_MANIFEST.json',cap/'EXECUTION.json',cap/'build-source-manifest.json']+scripts
    inputs+=list((work/'initial-config').rglob('*.json'))+list((work/'initial-user-config').rglob('*.json'))
    inputs+=[SUPPLY/'candidate'/p for p in manifest['files']]
    inputs+=[cap/p for p in att['candidate_artifacts']]
    inputs+=[Path(sys.modules[name].__file__) for name in ('capsule_support','live_jsonl')]
    loaded_save=None;loaded_bundle=None
    if a.mode=='restore':
        original_save=a.load_save.resolve();original_bundle=a.bundle.resolve()
        header=original_save.read_bytes()[:15]
        assert original_save.suffix=='.vsgm1' and header[:4]==b'VCMI' and header[8:15]==b'VCMISVG'
        loaded_save=work/'data/vcmi/Saves'/original_save.name
        loaded_bundle=work/'recovery-bundle.json'
        shutil.copy2(original_save,loaded_save);shutil.copy2(original_bundle,loaded_bundle)
        inputs.extend([original_save,original_bundle,loaded_save,loaded_bundle])
    frozen={str(p):sha(p) for p in inputs}
    start_args=['--testsave','Saves/'+loaded_save.stem] if loaded_save else ['--testmap','Maps/adv/supply-stock-01']
    command=[str(work/'vcmiclient'),'--headless']+start_args+['--nointro','--disable-video','--savefrequency','1']
    write(work/'PLAN.json',dict(schema='scripted-supply-boundary-native-v4',mode=a.mode,nonce=a.nonce,checkpoint_turn=a.checkpoint_turn,load_save=str(loaded_save) if loaded_save else None,bundle=str(loaded_bundle) if loaded_bundle else None,execute=a.execute,command=command,capsule=str(cap),candidate_root=str(SUPPLY),seed=a.seed,hashes=frozen,
        own_turn_cap=a.own_turn_cap,engineering_timeout_seconds=a.seconds,scripted_only=True,optimizer_steps=0,training_samples=0,expert_labels=0,game_score_eligible=False,restoration_qualified=False))
    if not a.execute:print(json.dumps(dict(prepared=True,native_started=False)));return 0
    env=dict(os.environ,LD_LIBRARY_PATH=str(bins),SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',XDG_DATA_HOME=str(work/'data'),XDG_CONFIG_HOME=str(work),XDG_CACHE_HOME=str(work/'cache'),LAB_ADV_AI_0='DirectorAI',LAB_ADV_AI_1='EmptyAI',LAB_ADV_MODE='scripted_supply_v1',LAB_ADV_SUPPLY_TRACE=str(work/'supply.jsonl'),LAB_ADV_TRACE=str(work/'strategy-trace.jsonl'))
    for n in ('LAB_ADV_AGENT_DIR','LAB_ADV_SUPPLY_RESTORE','LAB_ADV_TYPED_EVENTS'):env.pop(n,None)
    env['LAB_ADV_RECOVERY_EVENTS']=str(work/'recovery.jsonl')
    env['LAB_ADV_RECOVERY_NONCE']=a.nonce
    env['LAB_ADV_RECOVERY_CHECKPOINT_TURN']=str(a.checkpoint_turn if a.mode=='reference' else 0)
    env.pop('LAB_ADV_RECOVERY_BUNDLE',None)
    if loaded_bundle:env['LAB_ADV_RECOVERY_BUNDLE']=str(loaded_bundle)
    loaded={};child=None;result=dict(game_completed=False,winner=None,optimizer_steps=0,training_samples=0,expert_labels=0,mechanics_qualified=False,restoration_qualified=False)
    with idle_locks(),(work/'client.log').open('w') as log:
        try:
            child=subprocess.Popen(command,cwd=work,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True);start=time.monotonic()
            while child.poll() is None:
                for item in session_evidence(child.pid,bins):
                    if not item['libraries']:continue
                    previous=loaded.get(item['pid'],{});threads={t['tid']:t for t in previous.get('run_server_threads',[])}
                    threads.update({t['tid']:t for t in item['run_server_threads']});item['run_server_threads']=list(threads.values());loaded[item['pid']]=item;assert item['valid']
                text=(work/'client.log').read_text(errors='replace')
                if 'DirectorTypedProtocolError' in text or 'Script layer not found' in text:
                    result['stop_reason']='native_protocol_or_asset_error';break
                observed=rows(work/'supply.jsonl')
                if any(r['own_turn']>=a.own_turn_cap for r in observed):result['stop_reason']='controlled_partial_turn_cap';break
                if time.monotonic()-start>a.seconds:result['stop_reason']='engineering_timeout';break
                time.sleep(.005)
            if child.poll() is not None:result.setdefault('stop_reason','native_exit_requires_separate_review')
        except BaseException as e:result.update(stop_reason='exception',error=repr(e))
        finally:stop(child);result['native_exit']=None if child is None else child.returncode
    result['loaded_library_observations']=list(loaded.values());result['input_sha_unchanged']=all(sha(Path(p))==h for p,h in frozen.items())
    try:result['thread_server_verification']=thread_server_gate(list(loaded.values()),(work/'client.log').read_text(errors='replace'),False)
    except AssertionError as e:result['thread_server_verification']=dict(passed=False,error=str(e))
    result['controlled_stop_is_not_safe_save_boundary']=True
    result['mode']=a.mode
    result['checkpoint_and_hydration_require_independent_audit']=True
    write(work/'EXECUTION.json',result);print(json.dumps(result,indent=2))
    return 0 if result.get('stop_reason')=='controlled_partial_turn_cap' and result['input_sha_unchanged'] and result['thread_server_verification']['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
