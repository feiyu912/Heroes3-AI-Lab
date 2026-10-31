"""Minimal maps for missing boundaries. Preparation never certifies pathfinding."""
import collections,copy,hashlib,json,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parent.parent
SOURCE=HERE.parent/'strategic-refill-retention-qualification-20261025/fixtures/refill-positive.vmap'
TERRAINS=Path('/home/kaicheng/Documents/Codex/2026-10-24/hello/outputs/Heroes3-Native-20261025/runtime/engine-strategic/config/terrains.json')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(x):return (json.dumps(x,indent=2,ensure_ascii=False)+'\n').encode()
def land_connected(grid,start,goal):
 pending=collections.deque([tuple(start[:2])]);seen={tuple(start[:2])}
 while pending:
  x,y=pending.popleft()
  if (x,y)==tuple(goal[:2]):return True
  for dx in (-1,0,1):
   for dy in (-1,0,1):
    nx,ny=x+dx,y+dy
    if (dx or dy) and 0<=ny<len(grid) and 0<=nx<len(grid[ny]) and not grid[ny][nx].startswith('wt') and (nx,ny) not in seen:seen.add((nx,ny));pending.append((nx,ny))
 return False

def main():
 assert sha(SOURCE)=='88bc6f81a9f73fcf2fecd5e70ca8f110131a85b08627b5a4a79599c8f3fc7d66'
 # The profile JSON contains comments; pin actual bytes and read reviewed keys.
 terrain_text=TERRAINS.read_text();water=terrain_text.split('"water" :',1)[1].split('\n\t},',1)[0]
 assert '"shortIdentifier" : "wt"' in water and '"WATER"' in water
 with zipfile.ZipFile(SOURCE) as z:original={i.filename:(i,z.read(i)) for i in z.infolist()}
 objects=json.loads(original['objects.json'][1]);baseheader=json.loads(original['header.json'][1]);basegrid=json.loads(original['surface_terrain.json'][1])
 objects['hero_1']['x']=30;objects['hero_1']['y']=11
 objects['town_1']['options']['army']=[{'type':'core:pikeman','amount':1}]
 full=['core:centaur','core:centaurCaptain','core:gremlin','core:imp','core:skeleton','core:troglodyte','core:gnoll']
 cases={
  'reachable-stock-control':dict(mode='build_recruit_v1',schema='strategy-candidates-v6',factor='Unchanged land/owned town/positive stock; precommit reachable kind4 control.'),
  'unreachable-stock':dict(mode='build_recruit_v1',schema='strategy-candidates-v6',factor='Only surface terrain changes: closed native water rectangle outside the complete town footprint.'),
  'nonowned-stock':dict(mode='build_recruit_v1',schema='strategy-candidates-v6',factor='Only target town owner changes blue→red, retaining stock and terrain.'),
  'arrive-incompatible-stock':dict(mode='build_recruit_v1',schema='strategy-candidates-v6',factor='Only hero army changes to seven incompatible species. Real arrival leaves positive nonreceivable stock; executor remains enabled.'),
  'consumed-pickup':dict(mode='build_recruit_v1',schema='strategy-candidates-v6',factor='Only town stock is emptied. Select original actual gold pickup; consuming it invalidates the old kind3 goal.'),
  'legacy-build':dict(mode='build_v1',schema='strategy-candidates-v5',factor='Identical reachable-control map; only original native build-only mode. Legacy scripted economy remains enabled.'),
  'legacy-v4':dict(mode='',schema='strategy-candidates-v4',factor='Identical reachable-control map; only original native legacy mode. Legacy scripted economy remains enabled.')}
 out=HERE/'fixtures';out.mkdir(exist_ok=False);rows={}
 for case,settings in cases.items():
  o=copy.deepcopy(objects);g=copy.deepcopy(basegrid);header=copy.deepcopy(baseheader)
  if case=='nonowned-stock':o['town_1']['options']['owner']='red'
  if case=='arrive-incompatible-stock':o['hero_1']['options']['army']=[{'type':key,'amount':1} for key in full]
  if case=='consumed-pickup':o['town_1']['options']['army']=[]
  cells=[]
  if case=='unreachable-stock':
   # Town footprint: x26..31/y3..8. Ring leaves every object tile intact.
   cells=sorted({(x,y) for x in range(25,33) for y in range(2,10) if x in (25,32) or y in (2,9)})
   for x,y in cells:g[y][x]='wt0_'
  connected=land_connected(g,[29,11,0],[29,8,0]);assert connected==(case!='unreachable-stock')
  name='boundary-'+case;path=out/(name+'.vmap')
  with zipfile.ZipFile(path,'w') as z:
   for n,(info,b) in original.items():z.writestr(info,dump(o) if n=='objects.json' else dump(g) if n=='surface_terrain.json' else b)
  rows[case]=dict(**settings,path=str(path),sha256=sha(path),map_name=name,seed=2026102602,owned_player=1,opponent='EmptyAI',max_seconds=180,target_town_position=[29,8,0],expected_initial_hero_position=[29,11,0],hero_army=o['hero_1']['options']['army'],target_owner=o['town_1']['options']['owner'],target_source_army=o['town_1']['options']['army'],water_ring_cells=[list(p) for p in cells],terrain_only_overapprox_land_connected=connected,native_pathfinding_qualified=False)
 manifest=dict(schema='refill-boundary-fixtures-v1',registered_date='2026-10-26',status='prepared-not-native-qualified',source=str(SOURCE),source_sha256=sha(SOURCE),native_water_metadata=str(TERRAINS),native_water_metadata_sha256=sha(TERRAINS),terrain_proof_scope='8-neighbor land graph ignores object collision; a disconnected overapproximation proves no ordinary land walk, but does not replace actual native loader/path/candidate evidence.',fixtures=rows,shared_terminal='Existing same native daysPassed3 event, diagnostic only',new_native_games=0,optimizer_steps=0,final_test_used=False)
 (HERE/'FIXTURE_MANIFEST.json').write_bytes(dump(manifest));print(json.dumps({k:v['sha256'] for k,v in rows.items()},indent=2))
if __name__=='__main__':main()
