"""New registered fixture geometry; reuse exactly the compiled v2 source pair."""
from pathlib import Path
import copy,hashlib,json,shutil,zipfile
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'multihero-scheduler-garrison-v2'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    assert not (HERE/'fixture-03.vmap').exists(),'Do not overwrite a fixture'
    with zipfile.ZipFile(OLD/'fixture-02.vmap') as z:
        entries={n:z.read(n) for n in z.namelist()}
    objects=json.loads(entries['objects.json'])
    terrain=json.loads(entries['surface_terrain.json'])
    before=copy.deepcopy(objects);tb=copy.deepcopy(terrain)
    goals={'resource_a1':(4,18),'resource_a2':(4,30),'resource_b1':(18,18),'resource_b2':(18,30)}
    for name,(x,y) in goals.items():objects[name].update(x=x,y=y)
    tiles=[]
    for y in range(36):
        for x in range(36):
            if y==9 or x in (9,26):
                terrain[y][x]='wt0_';tiles.append([x,y,tb[y][x],terrain[y][x]])
    entries['objects.json']=json.dumps(objects).encode()
    entries['surface_terrain.json']=json.dumps(terrain).encode()
    with zipfile.ZipFile(HERE/'fixture-03.vmap','w',zipfile.ZIP_DEFLATED) as z:
        for name,data in entries.items():
            info=zipfile.ZipInfo(name,date_time=(2026,10,23,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(info,data)
    for name in ('capsule_support.py','audit_legacy.py','audit_scheduler.py','build_scheduler.py','derive.py','DERIVATION.json','prepare_runner.py','fixture-02.json'):
        shutil.copy2(OLD/name,HERE/name)
    shutil.copytree(OLD/'candidates',HERE/'candidates')
    runner=(OLD/'run_scheduler.py').read_text()
    runner=runner.replace('multihero-scheduler-garrison-v2.vmap','multihero-scheduler-garrison-v3.vmap')
    runner=runner.replace('Maps/adv/multihero-scheduler-garrison-v2"','Maps/adv/multihero-scheduler-garrison-v3"')
    runner=runner.replace('fixture-02.vmap','fixture-03.vmap')
    runner=runner.replace('inputs += [HERE / "PLAN.md",','inputs += [HERE / "prepare.py", HERE / "FIXTURE_DERIVATION.json", HERE / "PLAN.md",')
    (HERE/'run_scheduler.py').write_text(runner)
    manifest={'map_sha256':sha(HERE/'fixture-03.vmap'),'parent_map_sha256':sha(OLD/'fixture-02.vmap'),
        'changes':{'terrain':tiles,'resource_positions':{n:{'before':[before[n]['x'],before[n]['y']],'after':list(xy)} for n,xy in goals.items()}},
        'hero_town_header_bytes_unchanged':all(objects[n]==v for n,v in before.items() if n not in goals),
        'native_source_pair':'Byte identical copied v2 candidates; reuse capsule-02 build attestations',
        'probe_schema':'multihero-scheduler-garrison-v2 (compiled instrumentation reused unchanged)',
        'rationale':'Real positive-MP garrison plus unreachable town; independent mobile compartments and reachable goals prevent common town attraction and exchange deadlock.',
        'gate_unchanged':True,'seed':2026102501,'native_runs':0,'optimizer_steps':0}
    assert manifest['hero_town_header_bytes_unchanged']
    (HERE/'FIXTURE_DERIVATION.json').write_text(json.dumps(manifest,indent=2))
    f=json.loads((HERE/'fixture-02.json').read_text());f['map_sha256']=manifest['map_sha256'];f['map_bytes']='Explicit v3 geometry change; see FIXTURE_DERIVATION.json'
    (HERE/'fixture-02.json').write_text(json.dumps(f,indent=2))
    print(json.dumps({k:v for k,v in manifest.items() if k!='changes'},indent=2))
if __name__=='__main__':main()
