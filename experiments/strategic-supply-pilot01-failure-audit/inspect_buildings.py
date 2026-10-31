"""Read historical run-local native faction configs and own town building traces."""
import hashlib
import json
from pathlib import Path
import re
from inspect_failure import HERE,V2


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


old=json.loads((V2.parent/'strategic-nk-failure-audit-20261018/AUDIT.json').read_text())
execution=json.loads((V2/'supply-native-pilot-01/EXECUTION.json').read_text())
inputs=[dict(source='four_original_train_losses',seed=e['config']['seed'],root=Path(e['native']['run_dir']))for e in old['episodes']]
for ep in execution['episodes']:
    raw=json.loads(Path(ep['audit']).read_text())
    inputs.append(dict(source='stopped_supply_pilot_valid_prefix',seed=ep['seed'],mode=ep['mode'],root=Path(raw['native_dir'])))
rows=[]
snap=HERE/'native-faction-config-snapshots';snap.mkdir(exist_ok=True)
for entry in inputs:
    root=entry['root'];cfg=root/'config/factions/castle.json';trace=root/'strategy-trace.jsonl'
    cpp=root/'source-snapshot/CDirectorAI.cpp'
    text=cfg.read_text();sourcetext=cpp.read_text();h=sha(cfg)
    copy=snap/(h+'-castle.json')
    if not copy.exists():copy.write_bytes(cfg.read_bytes())
    assert sha(copy)==h
    cfgrows=text.splitlines()
    relevant=[dict(line=i,text=line)for i,line in enumerate(cfgrows,1)if re.search(r'"(dwellingLvl[1-7]|special2)"\s*:',line)]
    assert re.search(r'"dwellingLvl3"\s*:\s*\{\s*"requires"\s*:\s*\[\s*"dwellingLvl4"',text)
    priority=re.search(r'const BuildingID priorities\[\]\s*=\s*\{([^}]+)\}',sourcetext).group(1)
    assert 'DWELL_LVL_3' in priority and 'DWELL_LVL_4' not in priority
    states=[(i,json.loads(x))for i,x in enumerate(trace.read_text().splitlines(),1)]
    town_id=states[0][1]['towns'][0]['id'];maxdwell=set();daily=[]
    for line,s in states:
        for t in s['towns']:
            if t['id']!=town_id:continue
            d=[x for x in t['buildings']if 30<=x<=43];maxdwell.update(d)
            if s['event']in ('turn_start','turn_end','defeat','victory'):
                daily.append(dict(line=line,day=s['day'],event=s['event'],buildings=t['buildings'],
                    dwelling_ids=d,gold=s['gold'],wood=s['wood'],ore=s['ore']))
    rows.append(dict(**{k:v for k,v in entry.items()if k!='root'},native_dir=str(root),
        config=str(cfg),config_sha256=h,config_snapshot=str(copy),config_requires_lines=relevant,
        cpp_snapshot=str(cpp),cpp_sha256=sha(cpp),missing_dwelling4_in_priority=True,
        starting_own_town_id=town_id,ever_observed_starting_town_dwelling_ids=sorted(maxdwell),
        observed_new_dwelling3_or_above=any(x>=32 for x in maxdwell),trace_sha256=sha(trace),own_town_daily=daily))
out=HERE/'BUILDING_AUDIT.json';assert not out.exists()
out.write_text(json.dumps(dict(schema='native-run-local-building-dependency-audit-v1',rows=rows,
    inference='For Castle starting towns, dwelling3 requires dwelling4 absent from the fixed construction list; only existing/inherited higher dwellings can bypass this planner omission.'),indent=2,ensure_ascii=False))
print(json.dumps([dict(seed=r['seed'],source=r['source'],config_sha256=r['config_sha256'],
    starting_own_town_id=r['starting_own_town_id'],dwelling_ids=r['ever_observed_starting_town_dwelling_ids'])for r in rows[:4]],ensure_ascii=False))
