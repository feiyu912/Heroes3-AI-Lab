"""Explicit Ubuntu capsule and frozen-input admission; no old-path aliases."""
import hashlib,importlib.util,json,os
from pathlib import Path
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parent.parent;EXP=HERE.parent
PROFILE=Path('/home/kaicheng/Documents/Codex/2026-10-24/hello/outputs/Heroes3-Native-20261025')
CONTRACT=EXP/'strategic-refill-paired-build-20261026/build-contract-v1.json'
CONTRACT_SHA='94fababf70089e1d944b17280c0d6e003ba39dc34c6a34fcb853316dc4308cf2'
RESOURCE=Path('/home/kaicheng/Documents/Codex/2026-10-24/hello/outputs/WSL迁出-20261025/files/root/heroes3-ai-lab/evaluations')
LEASE_SOURCE=EXP/'ubuntu-native-takeover-20261025/leases.py'
REGISTRY_SOURCE=EXP/'strategic-director-terminal-drain-v4/director_registry_v1.py'
SUPPORT_SOURCE=EXP/'multihero-mechanism-probe-v1/build-driver-frozen-03/capsule_support.py'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
 return h.hexdigest()
def load(p):return json.loads(Path(p).read_text())
def write(p,v):Path(p).write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n')
def module(name,p):
 spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
# Set canonical lock namespace before loading frozen lock helpers. No alternate lock root.
os.environ.setdefault('HEROES3_LAB_ROOT',str(PROFILE/'heroes3-ai-lab'))
os.environ.setdefault('HEROES3_RESOURCE_ROOT',str(RESOURCE))
assert Path(os.environ['HEROES3_RESOURCE_ROOT']).resolve()==RESOURCE.resolve()
leases=module('_refill_leases',LEASE_SOURCE)
registry=module('_refill_registry',REGISTRY_SOURCE)
support=module('_refill_support',SUPPORT_SOURCE)

def validate_capsule(capsule,arm):
 assert sha(CONTRACT)==CONTRACT_SHA,'Registered build contract changed'
 contract=load(CONTRACT);c=Path(capsule).resolve()
 assert arm in contract['arms'] and c==(Path(contract['capsule_root'])/arm).resolve()
 a=load(c/'BUILD_ATTESTATION.json');execution=load(c/'EXECUTION.json');sm=load(c/'build-source-manifest.json');bins=load(c/'binary-sha256.json')
 # This epoch never mutates accepted trees. No old shared-tree restoration flags.
 assert execution['passed'] is True and a['arm']==arm and a['contract_sha256']==CONTRACT_SHA
 assert a['protected_inputs_before_and_after_equal'] is True
 assert a['source_manifest_sha256']==sha(c/'build-source-manifest.json')
 assert a['binary_sha256']==bins and set(bins)=={'vcmiclient','vcmiserver','libvcmi.so'}
 tc=Path(contract['toolchain_root'])/'QUALIFIED_TOOLCHAIN.json'
 assert load(tc)['passed'] is True and a['toolchain_certificate_sha256']==sha(tc)
 assert a['actual_commands_and_exit_codes'] and all(x['exit_code']==0 for x in a['actual_commands_and_exit_codes'])
 assert a['lease_inode_and_inherited_fd_evidence'] and a['resource_peaks']
 for name,h in bins.items():
  p=c/'bin'/name;assert p.is_file() and not p.is_symlink() and sha(p)==h
 for relative,entry in contract['payloads'].items():assert sha(c/'source-snapshot'/relative)==sm[relative]['sha256']==entry[arm+'_sha256']
 # Re-check complete source snapshot, including every explicit source link.
 actual=support.source_manifest(c/'source-snapshot')
 assert actual==sm,'Complete capsule source snapshot differs from compiled manifest'
 for rel,entry in sm.items():
  if 'symlink' in entry:
   # Every link is pinned by the compiled manifest. External and dangling links
   # additionally require the builder's explicit reviewed record.
   assert rel in a['source_link_review'] and a['source_link_review'][rel]==entry
 inputs=[CONTRACT,c/'BUILD_ATTESTATION.json',c/'EXECUTION.json',c/'build-source-manifest.json',c/'binary-sha256.json',tc]
 inputs += [c/'bin'/n for n in bins]
 inputs += [p for p in (c/'bin/config').rglob('*') if p.is_file()]
 inputs += [c/'source-snapshot'/r for r,e in sm.items() if 'sha256' in e]
 return dict(attestation=a,execution=execution,manifest=sm,inputs=inputs)

def fixture(case):
 m=load(HERE/'FIXTURE_MANIFEST.json');f=m['fixtures'][case]
 assert sha(f['path'])==f['sha256'] and sha(m['source'])==m['source_sha256']
 return m,f

def verify_native_fds(pid,entries):
 observations=[]
 for e in entries:
  p=Path('/proc')/str(pid)/'fd'/str(e['fd']);st=p.stat()
  assert (st.st_dev,st.st_ino)==(e['device'],e['inode'])
  observations.append(dict(pid=pid,fd=e['fd'],device=st.st_dev,inode=st.st_ino,target=os.readlink(p)))
 return observations

def verify_source_freeze():
 pin=load(HERE/'SOURCE_FREEZE.json')
 assert pin['schema']=='refill-mechanism-source-freeze-v1' and pin['files']
 for filename,expected in pin['files'].items():assert sha(filename)==expected,'Frozen qualification input changed: '+filename
 return pin
