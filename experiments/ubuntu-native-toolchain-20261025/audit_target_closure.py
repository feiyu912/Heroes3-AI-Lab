"""Strict relocated target ELF resolution, rejecting stderr and host fallbacks."""
from pathlib import Path
import subprocess,json,re,os,hashlib,sys
H=Path(__file__).resolve().parent
P=Path('/home/kaicheng/Documents/Codex/2026-10-24/hello/outputs/Heroes3-Toolchain-GCC11-01');R=P/'sysroot'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 out=H/sys.argv[1];out.mkdir(exist_ok=False)
 roots=[R/'usr/lib/x86_64-linux-gnu',R/'usr/lib',R/'lib/x86_64-linux-gnu',R/'lib',R/'usr/lib/gcc/x86_64-linux-gnu/11',R/'usr/lib/x86_64-linux-gnu/pulseaudio']
 libpath=':'.join(str(p) for p in roots if p.exists());loader=R/'usr/lib/x86_64-linux-gnu/ld-linux-x86-64.so.2'
 libraries=[];neededmissing={};allnames={p.name for p in R.rglob('*') if p.is_file()}
 for p in sorted((R/'usr/lib').rglob('*')):
  if p.is_symlink() or not p.is_file() or '.so' not in p.name or p.read_bytes()[:4]!=b'\x7fELF' or p.name.startswith('ld-linux'):continue
  dynamic=subprocess.run(['readelf','-d',str(p)],capture_output=True,text=True,check=True).stdout
  needed=re.findall(r'\(NEEDED\).*?\[(.*?)\]',dynamic)
  for name in needed:
   if name not in allnames:neededmissing.setdefault(name,[]).append(str(p.relative_to(P)))
  cmd=[str(loader),'--inhibit-cache','--library-path',libpath,'--list',str(p)]
  proc=subprocess.run(cmd,env={'PATH':'/usr/bin:/bin','LANG':'C','LC_ALL':'C'},capture_output=True,text=True)
  resolved=re.findall(r'=> (/\S+)',proc.stdout);external=[s for s in resolved if not Path(s).resolve().is_relative_to(R.resolve())]
  missing='not found' in proc.stdout+proc.stderr
  libraries.append(dict(path=str(p.relative_to(P)),needed=needed,returncode=proc.returncode,stdout=proc.stdout,stderr=proc.stderr,external=external,passed=proc.returncode==0 and not proc.stderr and not external and not missing))
 old=[json.loads(s) for s in (P/'FILES.jsonl').read_text().splitlines()]
 assert len(old)==4186 and all(sha(P/row['path'])==row['sha256'] for row in old)
 files={str(p.relative_to(P)):sha(p) for p in R.rglob('*') if p.is_file() and not p.is_symlink()}
 links={str(p.relative_to(P)):os.readlink(p) for p in R.rglob('*') if p.is_symlink()}
 for path,target in links.items():assert (P/path).resolve(strict=True).is_relative_to(R.resolve())
 passed=bool(libraries) and all(row['passed'] for row in libraries) and not neededmissing
 result=dict(passed=passed,toolchain_root=str(P),scope='all extracted/supplemented target shared ELF dependency resolution under old loader, no host fallback; separate runtime hostloader qualification remains valid',files=files,links=links,source_sha256=sha(Path(__file__)),old4186_unchanged=True,original_file_manifest_sha256=sha(P/'FILES.jsonl'),library_search_path=libpath,rows=libraries,missing=neededmissing)
 (out/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n')
 if passed:
  result['qualification_evidence']=str(out/'RESULT.json');result['qualification_evidence_sha256']=sha(out/'RESULT.json');(P/'TARGET_DEPENDENCY_CLOSURE.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(dict(passed=passed,elfs=len(libraries),failed=sum(not x['passed'] for x in libraries),missing=list(neededmissing))))
if __name__=='__main__':main()
