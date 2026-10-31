"""Independent capsule readback and actual host-loader dependency check."""
import argparse,fcntl,hashlib,importlib.util,json,os,re,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
Q=HERE.parent/'strategic-refill-retention-qualification-20261025'
sys.path.insert(0,str(Q))
import common

def main():
 p=argparse.ArgumentParser();p.add_argument('--arm',choices=['baseline','candidate'],required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 contract=common.load(HERE/'build-contract-v1.json');capsule=Path(contract['capsule_root'])/a.arm
 result={'passed':False,'arm':a.arm,'native_games':0,'optimizer_steps':0,'scope':'independent source/binary readback and host-loader --list; not a game or capability test'}
 handles=[]
 try:
  common.verify_source_freeze()
  for path in common.leases.PATHS:
   assert path.is_file();handle=path.open('r+');handles.append(handle);fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
  entries=[common.leases.metadata(h,p) for h,p in zip(handles,common.leases.PATHS)]
  proof=common.leases.verify(entries,common.leases.PATHS);common.write(a.out/'LEASES.json',proof)
  pin=common.validate_capsule(capsule,a.arm);att=pin['attestation'];stage=Path(pin['execution']['stage'])
  assert common.load(stage/'RESULT.json')['passed']
  for key in ('PROTECTED_BEFORE.json','PROTECTED_AFTER.json'):assert (stage/key).is_file()
  assert common.load(stage/'PROTECTED_BEFORE.json')==common.load(stage/'PROTECTED_AFTER.json')
  log=(stage/'command.log').read_text(errors='replace');scratch=Path(contract['scratch_root'])
  configured=common.load(scratch/'CONFIGURED.json')
  assert common.sha(scratch/'CONFIGURED.json')==att['configured_sha256']
  assert common.sha(scratch/'BUILD_ADMISSION.json')==att['build_admission_sha256']
  closure=att['dependency_closure'];assert closure==configured['dependency_closure']
  assert common.sha(closure['path'])==closure['sha256']
  closure_data=common.load(closure['path']);assert closure_data['passed']
  prefix=Path(contract['toolchain_root'])
  for rel,expected in closure_data['files'].items():assert common.sha(prefix/rel)==expected
  for rel,target in closure_data['links'].items():assert os.readlink(prefix/rel)==target
  configure_stage=Path(configured['stage'])
  for name,expected in att['configure_evidence_sha256'].items():assert common.sha(configure_stage/name)==expected
  assert ' -c '+str(scratch/'source/AI/DirectorAI/CDirectorAI.cpp') in log and 'FAILED:' not in log
  assert common.load(stage/'COMMAND.json')['exit_code']==0
  elf=[]
  env={'PATH':'/usr/bin:/bin','LANG':'C','LC_ALL':'C','LD_LIBRARY_PATH':str(capsule/'bin')+':'+str(common.PROFILE/'runtime/runtime-libs')+':'+str(common.PROFILE/'heroes3-ai-lab/onnxruntime/lib')}
  loader=Path('/lib64/ld-linux-x86-64.so.2').resolve(strict=True)
  for name in ('vcmiclient','vcmiserver','libvcmi.so'):
   target=capsule/'bin'/name
   info=subprocess.run(['/usr/bin/readelf','-d',str(target)],capture_output=True,text=True,check=True)
   proc=subprocess.run([str(loader),'--inhibit-cache','--list',str(target)],env=env,capture_output=True,text=True)
   common.write(a.out/(name+'.loader.json'),{'command':[str(loader),'--inhibit-cache','--list',str(target)],'returncode':proc.returncode,'stdout':proc.stdout,'stderr':proc.stderr,'readelf_dynamic':info.stdout})
   assert proc.returncode==0 and not proc.stderr and 'not found' not in proc.stdout,name
   if name!='libvcmi.so':assert 'libvcmi.so => '+str(capsule/'bin/libvcmi.so') in proc.stdout,name
   elf.append({'name':name,'sha256':common.sha(target),'hostloader_dependencies_resolved':True})
  result.update(passed=True,full_source_manifest_readback=True,source_entries=len(pin['manifest']),compiled_director_command_observed=True,protected_before_after_equal=True,elf=elf,attestation_sha256=common.sha(capsule/'BUILD_ATTESTATION.json'),toolchain_certificate_sha256=att['toolchain_certificate_sha256'],dependency_closure_sha256=closure['sha256'],qualification_freeze_sha256=common.sha(Q/'SOURCE_FREEZE.json'))
 except BaseException as error:result['error']=repr(error)
 finally:
  common.write(a.out/'AUDIT.json',result)
  for handle in reversed(handles):handle.close()
 print(json.dumps(result,indent=2));return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
