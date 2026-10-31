"""Add one copied actual resource definition beside own town; old maps remain untouched."""
import copy,hashlib,json,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
SOURCE=HERE.parent.parent/'strategic-learned-economy-native-v2/qualification/fixture-01/free-stock-rescue-stock-mechanism-v2-01.vmap'
NAME='schema6-recruit-neighbor-mechanism-v1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 before_sha=sha(SOURCE);assert before_sha=='466b2bac6dcd89975191f9745d9f7b951c26d50f81da91d751954e87bd59e1c5'
 with zipfile.ZipFile(SOURCE) as z:
  entries={i.filename:(i,z.read(i.filename)) for i in z.infolist()};objects=json.loads(entries['objects.json'][1]);original=copy.deepcopy(objects)
  template_key='resource_left_gold';key='schema6_mechanism_neighbor_gold';assert key not in objects
  assert objects[template_key]['type']=='resource' and objects[template_key]['subtype']=='core:gold'
  assert not any(v.get('x')==29 and v.get('y')==9 and v.get('l',0)==0 for v in objects.values())
  added=copy.deepcopy(objects[template_key]);added['x']=29;added['y']=9;objects[key]=added
  assert all(objects[k]==v for k,v in original.items())
  target=HERE/(NAME+'.vmap');assert not target.exists()
  with zipfile.ZipFile(target,'w') as out:
   for n,(info,b) in entries.items():out.writestr(info,json.dumps(objects,indent=2).encode() if n=='objects.json' else b)
 with zipfile.ZipFile(target) as z:assert all(z.read(n)==b for n,(info,b) in entries.items() if n!='objects.json')
 assert sha(SOURCE)==before_sha
 manifest=dict(mechanism_only=True,training_samples=0,optimizer_steps=0,source_map=str(SOURCE),source_map_sha256=before_sha,fixture_map=str(target),fixture_map_sha256=sha(target),changed_zip_entries=['objects.json'],added_object_key=key,added_object=added,copied_actual_template_key=template_key,all_previous_objects_identical=True,all_other_zip_entries_byte_identical=True,legality='No preclaimed reachability: selector must observe an actual kind3 position==next candidate; missing it is uncovered')
 (HERE/'FIXTURE_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(manifest,indent=2))
if __name__=='__main__':main()
