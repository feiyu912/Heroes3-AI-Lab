"""Deterministically derive diagnostic fixtures; never modify or execute old maps."""
import copy,hashlib,json,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
PROJECT=HERE.parent.parent
BASE=PROJECT/'experiments/strategic-learned-economy-native-v2/qualification/fixture-01'
SOURCE=BASE/'free-stock-rescue-stock-mechanism-v2-01.vmap'
CAT=PROJECT/'experiments/takeover-20261023/strategic-delivery-01/archive/linux/evaluations/strategic-learned-recruitment-train-20261023-01/cell-07/native/agent/creature-catalog.json'
NAMES=('positive','empty','full-incompatible','full-merge')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(v):return (json.dumps(v,indent=2,ensure_ascii=False)+'\n').encode()
def main():
 assert sha(SOURCE)=='466b2bac6dcd89975191f9745d9f7b951c26d50f81da91d751954e87bd59e1c5'
 with zipfile.ZipFile(SOURCE) as z:original={i.filename:(i,z.read(i)) for i in z.infolist()}
 objects=json.loads(original['objects.json'][1]);header=json.loads(original['header.json'][1])
 own=objects['town_1'];own['options']['army']=[]
 hero=copy.deepcopy(json.loads((BASE/'FIXTURE_MANIFEST.json').read_text())['removed_own_hero']['hero_1'])
 # Native hero anchor x=30 corresponds to its visitable x=29; native request
 # must prove the loader really made it the town's visitor before coverage.
 hero['x']=30;hero['y']=8;hero['l']=0;objects['hero_1']=hero
 header['name']='refill-retention-diagnostic-only'
 header['description']='Mechanism fixture. No expertise, PPO admission or strength interpretation. Native calendar victory ends after day 3.'
 event=copy.deepcopy(header['triggeredEvents']['standardVictory'])
 event['condition']=['daysPassed',{'value':3}]
 header['triggeredEvents']['diagnosticCalendarEnd']=event
 known={e['canonical_key'] for e in json.loads(CAT.read_text())['entries']}
 incompatible=['core:centaur','core:centaurCaptain','core:gremlin','core:imp','core:skeleton','core:troglodyte','core:gnoll']
 assert set(incompatible+['core:pikeman'])<=known
 outdir=HERE/'fixtures';outdir.mkdir(exist_ok=False)
 rows={}
 for name in NAMES:
  o=copy.deepcopy(objects)
  if name.startswith('full-'):
   species=list(incompatible)
   if name=='full-merge':species[1]='core:pikeman'
   o['hero_1']['options']['army']=[{'type':key,'amount':1} for key in species]
  path=outdir/('refill-'+name+'.vmap')
  with zipfile.ZipFile(path,'w') as z:
   for filename,(info,raw) in original.items():z.writestr(info,dump(o) if filename=='objects.json' else dump(header) if filename=='header.json' else raw)
  with zipfile.ZipFile(path) as z:assert z.read('surface_terrain.json')==original['surface_terrain.json'][1]
  rows[name]=dict(path=str(path),sha256=sha(path),selector_case=name,source_hero_army=o['hero_1']['options']['army'],expected_refill=name in ('positive','full-merge'),initial_upper_army_empty=True,seed=2026102601,owned_player=1,opponent='EmptyAI',max_seconds=180,reachability_claimed=False)
 manifest=dict(schema='refill-retention-fixtures-v1',status='prepared-not-native-qualified',source=str(SOURCE),source_sha256=sha(SOURCE),creature_key_source=str(CAT),creature_key_source_sha256=sha(CAT),same_map_bytes_across_arms=True,training_samples=0,optimizer_steps=0,final_test_used=False,changed_zip_entries=['header.json','objects.json'],unchanged_terrain_sha256=hashlib.sha256(original['surface_terrain.json'][1]).hexdigest(),terminal='Native daysPassed(value=3) victory event in same bytes for both arms. Calendar terminal is diagnostic only; winner has no strength meaning.',fixtures=rows,deferred_boundaries={k:dict(status='registered-not-constructed-or-run',coverage=False) for k in ['unreachable-own-town','non-owned-town','current-tile','committed-kind4-deduplication','invalidated-old-commit','legacy-build-only']})
 (HERE/'FIXTURE_MANIFEST.json').write_bytes(dump(manifest));print(json.dumps(manifest,indent=2))
if __name__=='__main__':main()
