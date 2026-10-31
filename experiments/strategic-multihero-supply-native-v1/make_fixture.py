"""New deterministic engineering map; no installation or frozen-map mutation."""
import copy,hashlib,json,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
SOURCE=HERE.parent/'multihero-mechanism-probe-v1/fixture-01.vmap'
def main():
    target=HERE/'supply-stock-01.vmap';assert not target.exists()
    with zipfile.ZipFile(SOURCE) as z:entries={n:z.read(n) for n in z.namelist()}
    h=json.loads(entries['header.json']);o=json.loads(entries['objects.json'])
    o['hero_0'].update(x=11,y=10);o['hero_0']['options'].update(name='ENGINEERING scripted main',army=[dict(type='core:pikeman',amount=5)])
    o['hero_2'].update(x=9,y=10);o['hero_2']['options'].update(name='ENGINEERING scripted courier',army=[dict(type='core:archer',amount=3)])
    o['town_0']['options']['army']=[dict(type='core:pikeman',amount=10)]
    h['name']='scripted-supply-stock-engineering-v1'
    h['description']='ENGINEERING ONLY: two real owned heroes, finite initial town stock. No learned economy, curriculum or strategic score.'
    entries['header.json']=json.dumps(h,sort_keys=True,indent=2).encode()
    entries['objects.json']=json.dumps(o,sort_keys=True,indent=2).encode()
    with zipfile.ZipFile(target,'w') as z:
        for name,data in sorted(entries.items()):
            info=zipfile.ZipInfo(name,date_time=(2026,10,18,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,data)
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    (HERE/'FIXTURE.json').write_text(json.dumps(dict(source=str(SOURCE),source_sha256=sha(SOURCE),map=str(target),map_sha256=sha(target),
        script_sha256=sha(Path(__file__)),installed=False,native_loaded=False,initial_total_armies=dict(pikeman=15,archer=3),
        role_rule='Actual minimum owned hero ID is main; maximum is courier. Actual runtime roster must verify fixture assignment.',
        stock_schema_source='Actual CGTownInstance::serializeJsonOptions calls CArmedInstance::serializeJsonOptions. Native loaded army still requires observation.',
        qualification_scope='One real town pickup, one compatible delivery with reserve, query/ACK close, sustained control across two own turns. Finite initial stock; no repeat recruitment or normal-game score claim.'),indent=2))
    print(json.dumps(dict(prepared=True,installed=False,native_loaded=False,sha256=sha(target))))
if __name__=='__main__':main()
