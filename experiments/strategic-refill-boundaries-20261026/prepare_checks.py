"""Read-only CPU preparation validation, explicitly not native qualification."""
import argparse,difflib,hashlib,importlib.util,json,py_compile,subprocess,sys,zipfile
from pathlib import Path
from boundary_common import HERE,V1,load,sha,write,fixture
from prepare_fixtures import land_connected

def ziprows(path):
 with zipfile.ZipFile(path) as z:return {n:z.read(n) for n in z.namelist()}
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 result=dict(passed=False,new_native_games=0,GPU_runs=0,optimizer_steps=0,final_test_used=False,scope='CPU map/tool preparation and rechecking existing raw, not new native qualification')
 try:
  scripts=sorted(HERE.glob('*.py'))
  for script in scripts:py_compile.compile(str(script),cfile=str(a.out/(script.stem+'.pyc')),doraise=True)
  result['syntax_checked']=[p.name for p in scripts]
  checks=[]
  for name in ['collect_boundary.py','selector.py','audit_boundary.py','audit_pair.py','audit_natural_boundaries.py']:
   call=subprocess.run([sys.executable,str(HERE/name),'--help'],capture_output=True,text=True);assert call.returncode==0,(name,call.stderr)
   (a.out/(name+'.help.txt')).write_text(call.stdout);checks.append(dict(script=name,exit_code=call.returncode))
  result['CLI_help_checks']=checks
  m=load(HERE/'FIXTURE_MANIFEST.json');control=ziprows(m['fixtures']['reachable-stock-control']['path']);co=json.loads(control['objects.json']);terrain=json.loads(control['surface_terrain.json']);mapchecks=[]
  for case,entry in m['fixtures'].items():
   fixture(case);rows=ziprows(entry['path']);o=json.loads(rows['objects.json']);g=json.loads(rows['surface_terrain.json']);h=json.loads(rows['header.json'])
   assert rows['header.json']==control['header.json'] and h['triggeredEvents']['diagnosticCalendarEnd']['condition']==['daysPassed',{'value':3}]
   assert sum(v['type']=='hero' and v['options']['owner']=='blue' for v in o.values())==1
   assert o['hero_1']['x']==30 and o['hero_1']['y']==11
   assert land_connected(g,[29,11,0],[29,8,0])==(case!='unreachable-stock')
   if case=='unreachable-stock':
    assert rows['objects.json']==control['objects.json']
    changes={(x,y) for y in range(len(g)) for x in range(len(g[y])) if g[y][x]!=terrain[y][x]}
    assert changes=={tuple(v) for v in entry['water_ring_cells']} and all(g[y][x]=='wt0_' for x,y in changes)
    assert not any(26<=x<=31 and 3<=y<=8 for x,y in changes)
   else:
    assert rows['surface_terrain.json']==control['surface_terrain.json']
    if case=='nonowned-stock':o['town_1']['options']['owner']='blue';assert o==co
    elif case=='arrive-incompatible-stock':
     army=o['hero_1']['options']['army'];assert len(army)==len({s['type'] for s in army})==7 and 'core:pikeman' not in {s['type'] for s in army}
     o['hero_1']['options']['army']=co['hero_1']['options']['army'];assert o==co
    elif case=='consumed-pickup':o['town_1']['options']['army']=co['town_1']['options']['army'];assert o==co
    else:assert rows==control
   mapchecks.append(dict(case=case,sha256=sha(entry['path']),single_factor_structure_passed=True,native_qualified=False))
  result['fixture_checks']=mapchecks
  # New schema6 path in the derived raw auditor must still accept actual
  # already-qualified native evidence, without admitting it as a boundary game.
  spec=importlib.util.spec_from_file_location('_boundary_raw_preflight',HERE/'boundary_raw_contract.py');raw=importlib.util.module_from_spec(spec);spec.loader.exec_module(raw)
  old=HERE.parent/'strategic-refill-paired-build-20261026/native-01/candidate-positive'
  r=raw.audit_game(old,HERE,mechanism=False);assert r['passed'] and r['actual_decisions_checked']==8
  result['existing_schema6_raw_regression']=dict(passed=True,source=str(old),actual_decisions_checked=r['actual_decisions_checked'],existing_game_not_recounted=True,legacy_runtime_qualification_claimed=False)
  for parent,new in [('collect_mechanism.py','collect_boundary.py'),('raw_contract_auditor.py','boundary_raw_contract.py')]:
   (a.out/(new+'.diff')).write_text(''.join(difflib.unified_diff((V1/parent).read_text().splitlines(True),(HERE/new).read_text().splitlines(True),fromfile=str(V1/parent),tofile=str(HERE/new))))
  result['passed']=True
 except BaseException as error:result['error']=repr(error);raise
 finally:write(a.out/'RESULT.json',result)
 print(json.dumps(result,indent=2))
if __name__=='__main__':main()
