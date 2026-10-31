"""Own-side initial-condition mechanism fixture. No enemy-state diagnosis or native execution."""
import copy,hashlib,json,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;QUAL=HERE.parent
SOURCE=Path('/root/heroes3-ai-lab/data/vcmi/Maps/adv/takeover-v2-train-02-development.vmap')
NAME='free-stock-rescue-stock-mechanism-v2-01'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def once(t,a,b):assert t.count(a)==1,(a,t.count(a));return t.replace(a,b,1)
def main():
 old_sha=sha(SOURCE)
 with zipfile.ZipFile(SOURCE) as z:
  entries={i.filename:(i,z.read(i.filename)) for i in z.infolist()}
  objects=json.loads(entries['objects.json'][1]);before=copy.deepcopy(objects)
  own=[k for k,v in objects.items() if v.get('options',{}).get('owner')=='blue']
  heroes=[k for k in own if objects[k]['type']=='hero'];towns=[k for k in own if objects[k]['type']=='town']
  assert len(heroes)==len(towns)==1
  hero,town=heroes[0],towns[0];stock=copy.deepcopy(objects[hero]['options']['army'])
  assert len(stock)==2 and len({s['type'] for s in stock})==2 and all(s['amount']>0 for s in stock)
  assert 'core:tavern' in objects[town]['options']['buildings']['allOf'] and 'army' not in objects[town]['options']
  del objects[hero];objects[town]['options']['army']=stock
  assert all(objects[k]==v for k,v in before.items() if k not in [hero,town])
  target=HERE/(NAME+'.vmap');assert not target.exists()
  with zipfile.ZipFile(target,'w') as out:
   for key,(info,data) in entries.items():out.writestr(info,json.dumps(objects,indent=2).encode() if key=='objects.json' else data)
 with zipfile.ZipFile(target) as z:
  assert all(z.read(n)==data for n,(info,data) in entries.items() if n!='objects.json')
  j=json.loads(z.read('objects.json'));assert j==objects
 assert sha(SOURCE)==old_sha
 manifest=dict(mechanism_only=True,training_samples=0,optimizer_steps=0,source_map=str(SOURCE),source_map_sha256=old_sha,fixture_map=str(target),fixture_map_sha256=sha(target),fixed_seed=2026103501,owned_player=1,opponent='Nullkiller2',changed_zip_entries=['objects.json'],unchanged_zip_entry_sha256={n:hashlib.sha256(data).hexdigest() for n,(info,data) in entries.items() if n!='objects.json'},removed_own_hero={hero:before[hero]},modified_own_town=dict(object_key=town,before=before[town],after=objects[town]),all_other_objects_structurally_identical=True,header_resources_factions_tavern_preserved=True)
 (HERE/'FIXTURE_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
 t=(QUAL/'collect_mechanism.py').read_text()
 t=once(t,'LOCAL=DEV_TOOLS','LOCAL=DEV_TOOLS.parent')
 t=once(t,'assert args.map in ("takeover-v2-train-01-mines","takeover-v2-train-02-development"),"Mechanism-only uses fixed TRAIN maps"',f'assert args.map=="{NAME}","Mechanism-only fixed own-side fixture"')
 t=once(t,"source=LAB/('data/vcmi/Maps/adv/'+args.map+'.vmap')","source=DEV_TOOLS/(args.map+'.vmap')")
 t=once(t,'assert source.is_file(),str(source)',"assert source.is_file(),str(source)\n    fixture=json.loads((DEV_TOOLS/'FIXTURE_MANIFEST.json').read_text())\n    assert sha(source)==fixture['fixture_map_sha256'] and sha(Path(fixture['source_map']))==fixture['source_map_sha256']\n    assert args.player==1 and args.opponent=='Nullkiller2' and args.seed==2026103501")
 t=once(t,"choices=['takeover-v2-train-01-mines','takeover-v2-train-02-development'],default='takeover-v2-train-02-development'",f"choices=['{NAME}'],default='{NAME}'")
 t=once(t,"inputs.extend(sorted(DEV_TOOLS.glob('*.py'))+[DEV_TOOLS/'PLAN.md',OLD/'collect_episode_v5.py'])","inputs.extend(sorted(DEV_TOOLS.glob('*.py'))+[DEV_TOOLS/'PLAN.md',DEV_TOOLS/'FIXTURE_MANIFEST.json',LOCAL/'PLAN.md',Path(fixture['source_map']),OLD/'collect_episode_v5.py'])")
 (HERE/'collect_fixture.py').write_text(t)
 print(json.dumps({k:v for k,v in manifest.items() if k not in ['removed_own_hero','modified_own_town']},indent=2))
if __name__=='__main__':main()
