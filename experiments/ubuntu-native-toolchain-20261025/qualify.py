"""Isolated, leased compile/link qualification; no accepted tree mutation."""
import os,sys,json,hashlib,fcntl,subprocess,importlib.util,re,time,traceback
from pathlib import Path
HERE=Path(__file__).resolve().parent
PROJECT=HERE.parent.parent
PREFIX=Path('/home/kaicheng/Documents/Codex/2026-10-24/hello/outputs/Heroes3-Toolchain-GCC11-01')
ROOT=PREFIX/'sysroot'; BIN=ROOT/'usr/bin'; GCCLIB=ROOT/'usr/lib/gcc/x86_64-linux-gnu/11'
PROFILE=Path('/home/kaicheng/Documents/Codex/2026-10-24/hello/outputs/Heroes3-Native-20261025')
CMAKE=PROFILE/'heroes3-ai-lab/python-packages/cmake/data/bin/cmake'
RESOURCE=Path('/home/kaicheng/Documents/Codex/2026-10-24/hello/outputs/WSL迁出-20261025/files/root/heroes3-ai-lab/evaluations')
os.environ['HEROES3_LAB_ROOT']=str(PROFILE/'heroes3-ai-lab');os.environ['HEROES3_RESOURCE_ROOT']=str(RESOURCE)
spec=importlib.util.spec_from_file_location('leases',PROJECT/'experiments/ubuntu-native-takeover-20261025/leases.py');leases=importlib.util.module_from_spec(spec);spec.loader.exec_module(leases)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def environment():
 return dict(PATH=str(BIN)+':/usr/bin:/bin',HOME=os.environ['HOME'],LANG='C',LC_ALL='C',LD_LIBRARY_PATH=str(PREFIX/'compiler-runtime'),COMPILER_PATH=str(GCCLIB)+':'+str(BIN),PKG_CONFIG_SYSROOT_DIR=str(ROOT),PKG_CONFIG_LIBDIR=str(ROOT/'usr/lib/x86_64-linux-gnu/pkgconfig')+':'+str(ROOT/'usr/share/pkgconfig'),HEROES3_LAB_ROOT=os.environ['HEROES3_LAB_ROOT'],HEROES3_RESOURCE_ROOT=str(RESOURCE),TERMINAL_CREDIT_LEASES=os.environ.get('TERMINAL_CREDIT_LEASES',''))
def worker(out):
 verification=leases.verify_pair();write(out/'INHERITED_LEASES.json',verification)
 env=environment();write(out/'ENV.json',env)
 def run(label,args,input=None):
  start=time.time();p=subprocess.run([str(x) for x in args],env=env,input=input,capture_output=True,text=True,cwd=out)
  (out/(label+'.stdout')).write_text(p.stdout);(out/(label+'.stderr')).write_text(p.stderr)
  row=dict(command=[str(x) for x in args],returncode=p.returncode,seconds=time.time()-start,stdout_sha256=sha(out/(label+'.stdout')),stderr_sha256=sha(out/(label+'.stderr')))
  write(out/(label+'.json'),row)
  assert p.returncode==0,(label,p.returncode,p.stderr[-3000:]);return p.stdout,p.stderr
 assembly=json.loads((PREFIX/'ASSEMBLY.json').read_text());assert assembly['passed']
 assert sha(PREFIX/'FILES.jsonl')==assembly['files_sha256']
 rows=[json.loads(x) for x in (PREFIX/'FILES.jsonl').read_text().splitlines()]
 assert len(rows)==4186
 for row in rows:assert sha(PREFIX/row['path'])==row['sha256'],row['path']
 for row in json.loads((PREFIX/'LINKS.json').read_text()):
  p=PREFIX/row['path'];assert p.is_symlink() and os.readlink(p)==row['new_target'] and p.resolve(strict=True).is_relative_to(ROOT)
 write(out/'INPUT_AUDIT.json',dict(passed=True,files=len(rows),bytes=sum(x['size'] for x in rows),assembly_sha256=sha(PREFIX/'ASSEMBLY.json')))
 for name,exe,version in [('gcc',BIN/'gcc-11','11.4.0'),('gxx',BIN/'g++-11','11.4.0'),('ninja',BIN/'ninja','1.10.1'),('cmake',CMAKE,'3.31.10')]:
  a,b=run(name+'-version',[exe,'--version']);assert version in a
 for exe in [BIN/'gcc-11',BIN/'g++-11',GCCLIB/'cc1',GCCLIB/'cc1plus',GCCLIB/'collect2',BIN/'as',BIN/'ld',BIN/'ninja',CMAKE]:
  tag='elf-'+exe.name;a,b=run(tag,['/usr/bin/ldd',exe]);assert 'not found' not in a+b
  run(tag+'-dynamic',['/usr/bin/readelf','-d',exe])
 flags=['--sysroot='+str(ROOT),'-B'+str(BIN)+'/', '-B'+str(GCCLIB)+'/']
 for compiler in ['gcc-11','g++-11']:
  run(compiler+'-search',[BIN/compiler,*flags,'-print-search-dirs'])
  for component in ['as','ld','cc1plus' if compiler=='g++-11' else 'cc1']:
   a,b=run(compiler+'-program-'+component,[BIN/compiler,*flags,'-print-prog-name='+component]);assert Path(a.strip()).resolve().is_relative_to(ROOT),(component,a)
  run(compiler+'-include',[BIN/compiler,*flags,'-v','-E','-x','c++' if compiler=='g++-11' else 'c','-'],input='')
 c='#include <stdio.h>\n#include <stdint.h>\nint main(void) { uint64_t x=42; printf("C:%lu\\n",(unsigned long)x); return x!=42; }\n'
 cpp='#include <iostream>\n#include <vector>\n#include <ranges>\n#include <numeric>\n#include <thread>\nint main(){std::vector<int> v{1,2,3}; auto r=v|std::views::transform([](int x){return x*2;}); int s=0; for(int x:r)s+=x;std::thread t([]{});t.join();std::cout<<"CXX20:"<<s<<"\\n";return s!=12;}\n'
 for name,exe,source,extra in [('c',BIN/'gcc-11',c,['-std=gnu11']),('cxx20',BIN/'g++-11',cpp,['-std=gnu++20','-pthread'])]:
  src=out/(name+('.c' if name=='c' else '.cpp'));src.write_text(source)
  run(name+'-build',[exe,*flags,*extra,'-O3','-DNDEBUG','-v','-Wl,-t','-Wl,-Map,'+str(out/(name+'.map')),src,'-o',out/name])
  run(name+'-target-elf',['/usr/bin/readelf','-l','-d',out/name])
  # Execute with explicitly paired old loader/libraries, not a mixed host loader.
  loader=ROOT/'usr/lib/x86_64-linux-gnu/ld-linux-x86-64.so.2'
  libs=str(ROOT/'usr/lib/x86_64-linux-gnu')+':'+str(GCCLIB)
  clean=env.copy();clean.pop('LD_LIBRARY_PATH')
  p=subprocess.run([str(loader),'--library-path',libs,str(out/name)],env=clean,capture_output=True,text=True)
  (out/(name+'-run.stdout')).write_text(p.stdout);(out/(name+'-run.stderr')).write_text(p.stderr)
  write(out/(name+'-run.json'),dict(returncode=p.returncode,command=[str(loader),'--library-path',libs,str(out/name)]));assert p.returncode==0,(name,p.stderr)
 write(out/'RESULT.json',dict(passed=True,toolchain_root=str(PREFIX),actual_executable_compilations=2,source_sha256=sha(__file__),environment_sha256=sha(out/'ENV.json'),actual_inherited_flocks=True,scope='C/C++20 executable compile/link/run and compiler ELF closure; VCMI configure/build not yet qualified'))
def main():
 if len(sys.argv)>1 and sys.argv[1]=='--worker':
  out=Path(sys.argv[2])
  try:worker(out)
  except BaseException as e:write(out/'RESULT.json',dict(passed=False,error=str(e),traceback=traceback.format_exc()));raise
  return
 out=HERE/(sys.argv[1] if len(sys.argv)>1 else 'attempt-01');out.mkdir(exist_ok=False)
 handles=[]
 try:
  for path in leases.PATHS:
   f=path.open('a');fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);handles.append(f)
  entries=[leases.metadata(f,p) for f,p in zip(handles,leases.PATHS)];write(out/'CONTROLLER_LEASES.json',entries)
  env=environment();env['TERMINAL_CREDIT_LEASES']=json.dumps(entries)
  with (out/'worker.log').open('w') as stream:code=leases.run_owned([sys.executable,str(Path(__file__).resolve()),'--worker',str(out)],env=env,stream=stream,pass_fds=[f.fileno() for f in handles])
  if code==0:
   cert=json.loads((out/'RESULT.json').read_text());cert['qualification_evidence']=str(out);cert['result_sha256']=sha(out/'RESULT.json');cert['environment']=environment();cert['environment'].pop('TERMINAL_CREDIT_LEASES');write(PREFIX/'QUALIFIED_TOOLCHAIN.json',cert)
  print(json.dumps(dict(exitcode=code,result=str(out/'RESULT.json'))))
 finally:
  leases.finish_owned_groups()
  for f in reversed(handles):fcntl.flock(f,fcntl.LOCK_UN);f.close()
if __name__=='__main__':main()
