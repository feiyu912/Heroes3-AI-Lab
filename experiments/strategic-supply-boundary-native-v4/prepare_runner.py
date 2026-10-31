"""Derive a new checkpoint runner; leave prior cargo experiment input unchanged."""
from pathlib import Path
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'strategic-multihero-supply-native-v1'
text=(OLD/'run_native_cargo_v2.py').read_text()
text=text.replace('import argparse,hashlib,json,os,shutil,signal,subprocess,sys,time','import argparse,hashlib,json,os,re,shutil,signal,subprocess,sys,time')
text=text.replace("SUPPLY=HERE.parent/'strategic-multihero-supply-v3'", "SUPPLY=HERE.parent/'strategic-multihero-supply-v4'")
text=text.replace("HERE/'PLAN_CARGO_V2.md'", "HERE/'PLAN.md'")
text=text.replace("HERE/'FIXTURE.json'", "OLD_FIXTURE/'FIXTURE.json'").replace("HERE/'supply-stock-01.vmap'", "OLD_FIXTURE/'supply-stock-01.vmap'")
text=text.replace("HERE=Path(__file__).resolve().parent;LAB=", "HERE=Path(__file__).resolve().parent;OLD_FIXTURE=HERE.parent/'strategic-multihero-supply-native-v1';LAB=")
needle='    a=ap.parse_args();assert a.seconds>0 and a.own_turn_cap>=2'
assert text.count(needle)==1
text=text.replace(needle,'''    ap.add_argument('--mode',choices=['reference','restore'],required=True)
    ap.add_argument('--nonce',default='boundary-01');ap.add_argument('--checkpoint-turn',type=int,default=2)
    ap.add_argument('--load-save',type=Path);ap.add_argument('--bundle',type=Path)
    a=ap.parse_args();assert a.seconds>0 and a.own_turn_cap>=3 and a.checkpoint_turn>=2
    assert re.fullmatch('[A-Za-z0-9_-]{1,64}',a.nonce)
    assert (a.mode=='restore')==bool(a.load_save and a.bundle)
    if a.mode=='reference':assert a.load_save is None and a.bundle is None
''')
text=text.replace("assert len(manifest['files'])==11", "assert len(manifest['files'])>=11")
text=text.replace("'data/vcmi/Maps/adv','cache'", "'data/vcmi/Maps/adv','data/vcmi/Saves','cache'")
needle="    frozen={str(p):sha(p) for p in inputs}"
assert text.count(needle)==1
text=text.replace(needle,'''    loaded_save=None;loaded_bundle=None
    if a.mode=='restore':
        original_save=a.load_save.resolve();original_bundle=a.bundle.resolve()
        header=original_save.read_bytes()[:15]
        assert original_save.suffix=='.vsgm1' and header[:4]==b'VCMI' and header[8:15]==b'VCMISVG'
        loaded_save=work/'data/vcmi/Saves'/original_save.name
        loaded_bundle=work/'recovery-bundle.json'
        shutil.copy2(original_save,loaded_save);shutil.copy2(original_bundle,loaded_bundle)
        inputs.extend([original_save,original_bundle,loaded_save,loaded_bundle])
    frozen={str(p):sha(p) for p in inputs}''')
needle="    command=[str(work/'vcmiclient'),'--headless','--testmap','Maps/adv/supply-stock-01','--nointro','--disable-video','--savefrequency','1']"
assert text.count(needle)==1
text=text.replace(needle,'''    start_args=['--testsave','Saves/'+loaded_save.stem] if loaded_save else ['--testmap','Maps/adv/supply-stock-01']
    command=[str(work/'vcmiclient'),'--headless']+start_args+['--nointro','--disable-video','--savefrequency','1']''')
text=text.replace("schema='scripted-supply-cargo-native-probe-v2'", "schema='scripted-supply-boundary-native-v4',mode=a.mode,nonce=a.nonce,checkpoint_turn=a.checkpoint_turn,load_save=str(loaded_save) if loaded_save else None,bundle=str(loaded_bundle) if loaded_bundle else None")
needle="    loaded={};child=None;result=dict("
assert text.count(needle)==1
text=text.replace(needle,'''    env['LAB_ADV_RECOVERY_EVENTS']=str(work/'recovery.jsonl')
    env['LAB_ADV_RECOVERY_NONCE']=a.nonce
    env['LAB_ADV_RECOVERY_CHECKPOINT_TURN']=str(a.checkpoint_turn if a.mode=='reference' else 0)
    env.pop('LAB_ADV_RECOVERY_BUNDLE',None)
    if loaded_bundle:env['LAB_ADV_RECOVERY_BUNDLE']=str(loaded_bundle)
    loaded={};child=None;result=dict(''')
text=text.replace("    result['controlled_stop_is_not_safe_save_boundary']=True", "    result['controlled_stop_is_not_safe_save_boundary']=True\n    result['mode']=a.mode\n    result['checkpoint_and_hydration_require_independent_audit']=True")
p=HERE/'run_native_boundary_v4.py';assert not p.exists();p.write_text(text);compile(text,str(p),'exec')
print('Prepared new boundary runner; no process started.')
