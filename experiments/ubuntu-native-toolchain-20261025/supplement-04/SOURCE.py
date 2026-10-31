"""Authenticated package-only minimal supplements; never overwrite existing bytes."""
from pathlib import Path,PurePosixPath
import json,hashlib,subprocess,tarfile,io,os,stat,re,lzma,sys
H=Path(__file__).resolve().parent
A=H.parent/'strategic-refill-paired-build-20261026/ubuntu-archive'
P=Path('/home/kaicheng/Documents/Codex/2026-10-24/hello/outputs/Heroes3-Toolchain-GCC11-01');R=P/'sysroot'
def sha(x):return hashlib.sha256(x).hexdigest()
def main():
 out=H/sys.argv[1];out.mkdir(exist_ok=False);stage=out/'staging';stage.mkdir()
 wanted=[];unavailable=[]
 for name in sys.argv[2:]:
  report=json.loads((A/name).read_text());assert all(r['verified'] for r in report['rows'] if r['found']);wanted.extend(r for r in report['rows'] if r['found']);unavailable.extend(r for r in report['rows'] if not r['found'])
 assert wanted
 targets={(r['package'],r['version']) for r in wanted};catalog={};indexes=[]
 for rel in sorted(A.glob('*.InRelease')):
  x=subprocess.run(['gpgv','--keyring','/usr/share/keyrings/ubuntu-archive-keyring.gpg',str(rel)],capture_output=True,text=True);assert x.returncode==0
  suite=rel.name.removesuffix('.InRelease');indexrows=[]
  for idx in [A/(suite+'-'+component+'-Packages.xz') for component in ('main','universe') if (A/(suite+'-'+component+'-Packages.xz')).exists()]:
   component=idx.name[len(suite)+1:-len('-Packages.xz')];name=component+'/binary-amd64/Packages.xz';m=re.findall(r'^ ([0-9a-f]{64})\s+(\d+) '+re.escape(name)+r'$',rel.read_text(),re.M);assert len(m)==1
   digest,size=m[0];b=idx.read_bytes();assert sha(b)==digest and len(b)==int(size)
   for block in lzma.decompress(b).decode().split('\n\n'):
    fields={}
    for line in block.splitlines():
     if line and not line[0].isspace() and ': ' in line:k,v=line.split(': ',1);fields[k]=v
    key=(fields.get('Package'),fields.get('Version'))
    if key in targets:catalog[key]=fields
   indexrows.append(dict(path=str(idx),sha256=digest,size=int(size)))
  indexes.append(dict(release=str(rel),sha256=sha(rel.read_bytes()),gpgv_stdout=x.stdout,gpgv_stderr=x.stderr,indexes=indexrows))
 assert targets<=catalog.keys()
 rows=[];overlap=[];selected=[]
 for row in wanted:
  meta=catalog[(row['package'],row['version'])];deb=Path(row['deb_path']);b=deb.read_bytes();assert sha(b)==row['deb_sha256']==meta['SHA256'] and len(b)==int(meta['Size'])
  control=subprocess.run(['dpkg-deb','-f',str(deb),'Package','Version','Architecture'],capture_output=True,text=True,check=True).stdout;assert 'Package: '+row['package'] in control and 'Version: '+row['version'] in control
  x=subprocess.run(['dpkg-deb','--fsys-tarfile',str(deb)],capture_output=True,check=True)
  with tarfile.open(fileobj=io.BytesIO(x.stdout)) as t:
   for member in t:
    logical=PurePosixPath(member.name);assert not logical.is_absolute() and '..' not in logical.parts
    rel=Path(*logical.parts);dest=R/rel
    if member.isfile() and dest.is_file():
     digest=sha(t.extractfile(member).read());assert sha(dest.read_bytes())==digest,(row['package'],str(dest),'existing bytes differ');overlap.append(dict(path=str(rel),sha256=digest,package=row['package']))
    wantedboost=rel.as_posix()=='usr/lib/x86_64-linux-gnu/cmake/BoostDetectToolset-1.74.0.cmake'
    # Exact basename is discovered below if packaging nests it in Boost-1.74.0.
    wantedboost=rel.name=='BoostDetectToolset-1.74.0.cmake'
    lib=(str(rel).startswith(('usr/lib/','lib/')) and '.so' in rel.name and row['package']!='libboost1.74-dev')
    if not (wantedboost or lib) or not (member.isfile() or member.issym()):continue
    staged=stage/rel;staged.parent.mkdir(parents=True,exist_ok=True)
    if member.isfile():data=t.extractfile(member).read();staged.write_bytes(data);os.chmod(staged,stat.S_IMODE(member.mode));entry=dict(kind='file',sha256=sha(data),bytes=len(data))
    else:
     target=member.linkname;assert '..' not in PurePosixPath(target).parts or not target.startswith('/')
     logicaltarget=Path(os.path.normpath(str(Path('/')/rel.parent/target))) if not target.startswith('/') else Path(target)
     mapped=R/str(logicaltarget).lstrip('/');new=os.path.relpath(mapped,(R/rel).parent)
     staged.symlink_to(new);entry=dict(kind='link',target=new,original_target=target)
    selected.append(dict(path=str(rel),package=row['package'],deb_sha256=row['deb_sha256'],**entry))
  rows.append(dict(package=row['package'],version=row['version'],deb_sha256=row['deb_sha256'],control=control))
 # Preflight selected full set before mutation, including any existing links.
 for row in selected:
  dest=R/row['path']
  if row['kind']=='file' and (dest.exists() or dest.is_symlink()):assert dest.is_file() and sha(dest.read_bytes())==row['sha256'],row
  if row['kind']=='link' and (dest.exists() or dest.is_symlink()):assert dest.is_symlink() and dest.resolve()==(dest.parent/row['target']).resolve(),row
 added=[]
 for row in selected:
  dest=R/row['path'];src=stage/row['path']
  if dest.exists() or dest.is_symlink():continue
  dest.parent.mkdir(parents=True,exist_ok=True)
  if row['kind']=='file':dest.write_bytes(src.read_bytes());os.chmod(dest,stat.S_IMODE(src.stat().st_mode));assert sha(dest.read_bytes())==row['sha256']
  else:dest.symlink_to(row['target'])
  added.append(row)
 for row in [json.loads(s) for s in (P/'FILES.jsonl').read_text().splitlines()]:assert sha((P/row['path']).read_bytes())==row['sha256']
 result=dict(passed=True,unavailable_packages=unavailable,packages=rows,authenticated_indexes=indexes,staged=len(selected),added=added,overlap_equal=overlap,old4186_unchanged=True,system_installed=False)
 (out/'MANIFEST.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(passed=True,staged=len(selected),added=len(added),overlap=len(overlap))))
if __name__=='__main__':main()
