"""Copy completed evidence to G and independently rehash every regular file; preserve links."""
import argparse,hashlib,json,os,shutil,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;RUN=HERE.parent;EXP=RUN.parent;LAB=Path('/root/heroes3-ai-lab')
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as stream:
  for block in iter(lambda:stream.read(4*1024*1024),b''):h.update(block)
 return h.hexdigest()
def read(p):return json.loads(p.read_text())
def collect(root):
 if root.is_symlink():return [(root,'link')]
 if root.is_file():return [(root,'file')]
 result=[]
 for child in sorted(root.iterdir()):
  if child.is_symlink():result.append((child,'link'))
  elif child.is_file():result.append((child,'file'))
  elif child.is_dir():result+=collect(child)
 return result
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=HERE/'delivery-01');a=p.parse_args();out=a.out.resolve()
 assert out.parent==HERE.resolve() and not out.exists(),'Delivery must be a fresh immediate child of the independent review directory'
 train=LAB/'evaluations/strategic-learned-free-transfer-train-01';dev=LAB/'evaluations/strategic-learned-free-transfer-dev-01'
 assert read(train/'RESULT.json')['passed'] and read(dev/'RESULT.json')['passed'] and read(HERE/'review-01/REVIEW.json')['passed']
 roots={'TRAIN':train,'DEV':dev,'capsule02':LAB/'evaluations/strategic-learned-economy-build-capsule-02','policy':EXP/'strategic-learned-free-transfer-policy-v1','native-v2':EXP/'strategic-learned-economy-native-v2','mechanism-startup-failed-01':LAB/'evaluations/strategic-free-stock-qualification-01','mechanism-uncovered-02':LAB/'evaluations/strategic-free-stock-qualification-02','mechanism-fixture-01':LAB/'evaluations/strategic-free-stock-fixture-01','independent-TRAIN-review':RUN/'independent-train-01','independent-DEV-review':HERE}
 tasks=[]
 # Snapshot source lists BEFORE creating the nested archive: no self-recursion.
 for label,root in roots.items():
  assert root.exists()
  for source,kind in collect(root):tasks.append((source,Path(label)/source.relative_to(root),kind))
 inputs={}
 for plan in [read(train/'PLAN.json'),read(dev/'PLAN.json')]:inputs.update(plan['input_sha256'])
 for source,h in inputs.items():
  source=Path(source);assert source.is_file() and sha(source)==h
  relative=Path('frozen-inputs')/str(source).lstrip('/')
  tasks.append((source,relative,'file'))
 for source in [RUN/'SOURCE_FREEZE.json',RUN/'SOURCE_STATUS.md',RUN/'DRAFT_BINDINGS.json',RUN/'PLAN.md']:
  tasks.append((source,Path('run-metadata')/source.name,'file'))
 assert len({str(t) for s,t,k in tasks})==len(tasks)
 need=sum(s.stat().st_size for s,t,k in tasks if k=='file');assert shutil.disk_usage(out.parent).free>need+100*1024*1024
 out.mkdir();manifest=[];last=time.monotonic();bytes_copied=0
 for index,(source,relative,kind) in enumerate(tasks):
  target=out/relative;target.parent.mkdir(parents=True,exist_ok=True)
  if kind=='link':
   link=os.readlink(source);target.symlink_to(link,target_is_directory=source.is_dir());assert target.is_symlink() and os.readlink(target)==link
   manifest.append(dict(source=str(source),target=str(relative),kind=kind,link_target=link,link_identity_sha256=hashlib.sha256(('symlink\0'+link).encode()).hexdigest()))
  else:
   before=sha(source);size=source.stat().st_size;shutil.copy2(source,target);assert sha(target)==before==sha(source)
   manifest.append(dict(source=str(source),target=str(relative),kind=kind,sha256=before,bytes=size));bytes_copied+=size
  if time.monotonic()-last>20:
   print(json.dumps(dict(copied=index+1,total=len(tasks),bytes=bytes_copied)),flush=True);last=time.monotonic()
 # Independent second pass of all copied identities, without trusting copy success.
 for record in manifest:
  target=out/record['target']
  if record['kind']=='file':assert sha(target)==record['sha256']
  else:assert target.is_symlink() and os.readlink(target)==record['link_target']
 report=dict(passed=True,regular_files=sum(r['kind']=='file' for r in manifest),symlinks=sum(r['kind']=='link' for r in manifest),regular_bytes=bytes_copied,every_regular_file_independently_rehashed=True,all_link_targets_preserved=True,links_limitation='Raw runtime links retain original targets; external Data/Mods asset trees are not duplicated. Full native capsule binaries/config/source artifacts are archived as regular files.',records=manifest,native_runs=0,gpu_runs=0,optimizer_steps=0)
 (out/'ARCHIVE_MANIFEST.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='records'},indent=2));print('manifest_sha256',sha(out/'ARCHIVE_MANIFEST.json'))
if __name__=='__main__':main()
