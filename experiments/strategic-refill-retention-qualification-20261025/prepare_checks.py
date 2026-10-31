"""CPU preparation checks only; no lock acquisition or native/model execution."""
import argparse,copy,difflib,json,py_compile,subprocess,sys,zipfile
from pathlib import Path
from common import HERE,PROJECT,CONTRACT,CONTRACT_SHA,REGISTRY_SOURCE,SUPPORT_SOURCE,LEASE_SOURCE,sha,load,write,fixture,validate_capsule
import raw_contract_auditor as raw

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 result=dict(passed=False,scope='CPU preparation only, not runtime qualification',native_games=0,GPU_runs=0,optimizer_steps=0,final_test_used=False)
 try:
  compiled=[]
  for file in sorted(HERE.glob('*.py')):
   py_compile.compile(str(file),cfile=str(a.out/(file.stem+'.pyc')),doraise=True);compiled.append(file.name)
  result['syntax_checked']=compiled
  manifest=load(HERE/'FIXTURE_MANIFEST.json');fixturechecks=[]
  for case in manifest['fixtures']:
   _,f=fixture(case)
   with zipfile.ZipFile(f['path']) as z:
    objects=json.loads(z.read('objects.json'));header=json.loads(z.read('header.json'))
    assert header['triggeredEvents']['diagnosticCalendarEnd']['condition']==['daysPassed',{'value':3}]
    assert objects['town_1']['options']['army']==[] and objects['hero_1']['options']['owner']=='blue'
    assert (objects['hero_1']['x'],objects['hero_1']['y'])==(30,8)
    assert len([v for v in objects.values() if v['type']=='hero' and v['options']['owner']=='blue'])==1
    assert objects['hero_1']['options']['army']==f['source_hero_army']
    if case.startswith('full-'):
     army=objects['hero_1']['options']['army'];assert len(army)==7 and len({s['type'] for s in army})==7
     assert ('core:pikeman' in {s['type'] for s in army})==(case=='full-merge')
   fixturechecks.append(dict(case=case,map_sha256=f['sha256'],passed=True,loader_or_path_coverage_claimed=False))
  result['fixture_checks']=fixturechecks
  before=Path('/home/kaicheng/Documents/Codex/2026-10-24/hello/outputs/Heroes3-Refill-Capsules-20261025-01/baseline')
  # Before any final capsule exists, admission must reject it. Once real final
  # capsules exist this preflight is superseded by their full runtime gate.
  if not (before/'BUILD_ATTESTATION.json').is_file():
   try:validate_capsule(before,'baseline')
   except (AssertionError,FileNotFoundError,KeyError) as error:result['incomplete_capsule_rejected']=repr(error)
   else:raise AssertionError('Incomplete capsule accepted')
  helpchecks=[]
  for name in ['collect_mechanism.py','audit_mechanism.py','audit_pair.py','selector.py']:
   command=[sys.executable,str(HERE/name),'--help'];call=subprocess.run(command,capture_output=True,text=True)
   assert call.returncode==0,(name,call.stderr)
   (a.out/(name+'.help.txt')).write_text(call.stdout);helpchecks.append(dict(command=command,exit_code=call.returncode))
  result['CLI_help_checks']=helpchecks
  # Actual archived raw transaction states exercise the unchanged conservation
  # auditor. Deliberate resource/army corruptions must be rejected.
  old=PROJECT/'experiments/takeover-20261023/strategic-delivery-01/archive/linux/evaluations/strategic-learned-recruitment-train-20261023-01/cell-07/native/typed.jsonl'
  events=raw.lines(old);recruits=[e for e in events if e['event']=='recruit_ack_state'];transfers=[e for e in events if e['event']=='free_transfer_native_sent']
  assert recruits and transfers
  e=recruits[0];raw.recruit_state(e['candidate'],e['before_state'],e['state'])
  altered=copy.deepcopy(e['state']);altered['resources']['gold']+=1
  try:raw.recruit_state(e['candidate'],e['before_state'],altered)
  except AssertionError:pass
  else:raise AssertionError('Corrupt recruitment resources accepted')
  t=transfers[0];_,ack=raw.unique(events,lambda e:e['event']=='free_transfer_ack_state' and e['native_request_id']==t['native_request_id'] and e['player']==t['player'])
  raw.transfer_state(t,ack['before_state'],ack['state']);altered=copy.deepcopy(ack['state'])
  slot=next(x for x in altered['visitor']['army'] if x is not None);slot['count']+=1
  try:raw.transfer_state(t,ack['before_state'],altered)
  except AssertionError:pass
  else:raise AssertionError('Corrupt transfer army accepted')
  result['archived_state_conservation_checks']=dict(source=str(old),sha256=sha(old),actual_recruit_state_accepted=True,actual_transfer_state_accepted=True,corrupt_resource_rejected=True,corrupt_army_rejected=True,old_native_runs_not_recounted=True)
  parent=PROJECT/'experiments/takeover-20261023/independent-evidence-01/audit_mechanism.py'
  (a.out/'raw-auditor-derivation.diff').write_text(''.join(difflib.unified_diff(parent.read_text().splitlines(True),(HERE/'raw_contract_auditor.py').read_text().splitlines(True),fromfile=str(parent),tofile=str(HERE/'raw_contract_auditor.py'))))
  result['parent_raw_auditor_sha256']=sha(parent);result['passed']=True
 except BaseException as error:result['error']=repr(error);raise
 finally:write(a.out/'RESULT.json',result)
 print(json.dumps(result,indent=2))
if __name__=='__main__':main()
