"""Explicit, audited cleanup of regenerable caches; never remove research inputs."""
import argparse
import fcntl
import hashlib
import json
import os
import stat
import subprocess
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
LAB = Path('/root/heroes3-ai-lab')
BUILDS = [LAB/'src/vcmi-adv-build', LAB/'src/gym/vcmi/rel',
          Path('/root/heroes3-ai-lab-events-v2/src/gym/vcmi/rel')]
CACHES = [Path('/root/.npm/_cacache'), Path('/root/.nv/ComputeCache'), Path('/root/.triton/cache')]
FROZEN = LAB/'src/gym/vcmi/rel/bin'
PROTECTED = [FROZEN/n for n in ('libvcmi.so','libmlclient.so','libmlserverplugin.so','vcmiclient','vcmiserver')]
PROTECTED += [BUILDS[2]/'bin'/n for n in ('libvcmi.so','libmlclient.so','libmlserverplugin.so','vcmiclient','vcmiserver')]
PROTECTED += [LAB/'src/vcmi-adv-build/bin'/n for n in ('libvcmi.so','vcmiclient','vcmiserver')]
PROTECTED += [LAB/'models/graph-finetune/1792068859379237126/update-64.pt',
    LAB/'evaluations/battle-continuation-lr-paired-01/control/models/1792508024116623978/update-60.pt',
    LAB/'evaluations/battle-continuation-lr-paired-01/candidate/models/1792509605969861627/update-57.pt',
    LAB/'evaluations/strategic-learned-free-transfer-train-01/update-01/update-1.pt']

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
    return h.hexdigest()

def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n')

def processes():
    busy=[]
    for p in Path('/proc').iterdir():
        if not p.name.isdigit() or int(p.name)==os.getpid():continue
        try:
            comm=(p/'comm').read_text().strip()
            args=(p/'cmdline').read_bytes().decode(errors='replace').split('\0')
            if comm in {'ninja','cmake','cc1plus','clang','clang++','g++','gcc','npm','apt','apt-get','dpkg'} or any(
                x.endswith(('/train_last_graph.py','/onpolicy_broker_v2.py')) or Path(x).name in {'vcmiclient','vcmiserver'} for x in args):
                busy.append({'pid':p.name,'comm':comm})
        except (OSError,ProcessLookupError):continue
    return busy

def scan(root,kind):
    if not root.exists():return []
    assert root.is_absolute() and root.resolve()==root and not root.is_symlink(),root
    entries=[]
    for parent,dirs,files in os.walk(root,followlinks=False):
        dirs[:]=[d for d in dirs if not (Path(parent)/d).is_symlink() and (kind!='pch' or d not in {'bin','.git','config','scripts'})]
        for name in files:
            p=Path(parent)/name
            if kind=='pch' and (name!='cmake_pch.hxx.gch' or 'CMakeFiles' not in p.parts):continue
            s=p.lstat()
            if not stat.S_ISREG(s.st_mode):continue
            if kind!='pch' and time.time()-s.st_mtime<48*3600:continue
            assert p.resolve().is_relative_to(root) and not p.is_symlink()
            entries.append(dict(path=str(p),root=str(root),kind=kind,size=s.st_size,
                allocated=s.st_blocks*512,inode=s.st_ino,mtime_ns=s.st_mtime_ns))
    return entries

def main():
    p=argparse.ArgumentParser();p.add_argument('--execute',action='store_true');a=p.parse_args()
    assert not processes(),processes()
    assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip(),'GPU busy'
    entries=sum((scan(r,'pch') for r in BUILDS),[])+sum((scan(r,'cache') for r in CACHES),[])
    summary={}
    for e in entries:
        item=summary.setdefault(e['root'],dict(files=0,allocated=0))
        item['files']+=1;item['allocated']+=e['allocated']
    plan=dict(execute=a.execute,summary=summary,files=len(entries),allocated=sum(e['allocated'] for e in entries),entries=entries)
    write(HERE/('EXECUTE_PLAN.json' if a.execute else 'PLAN.json'),plan)
    print(json.dumps({k:v for k,v in plan.items() if k!='entries'},indent=2),flush=True)
    if not a.execute:return
    assert not (HERE/'RESULT.json').exists(),'Do not rerun a completed deletion batch'
    before={str(p):sha(p) for p in PROTECTED}
    write(HERE/'PROTECTED_BEFORE.json',before)
    handles=[];free_before=__import__('shutil').disk_usage('/').free
    try:
        for name in ('.gpu-learner-lock','.pool-lock'):
            h=(LAB/'evaluations'/name).open('a');handles.append(h);fcntl.flock(h,fcntl.LOCK_EX|fcntl.LOCK_NB)
        assert not processes(),processes()
        with (HERE/'DELETED.jsonl').open('x') as log:
            for e in entries:
                path=Path(e['path']);root=Path(e['root']);s=path.lstat()
                assert path.resolve().is_relative_to(root) and not path.is_symlink()
                assert (s.st_ino,s.st_size,s.st_mtime_ns)==(e['inode'],e['size'],e['mtime_ns'])
                path.unlink()
                log.write(json.dumps(e)+'\n')
        after={str(p):sha(p) for p in PROTECTED}
        assert after==before,'Protected artifacts changed'
        write(HERE/'PROTECTED_AFTER.json',after)
        write(HERE/'RESULT.json',dict(passed=True,deleted_files=len(entries),allocated_bytes_removed=sum(e['allocated'] for e in entries),
            free_before=free_before,free_after=__import__('shutil').disk_usage('/').free,
            protected_artifacts_unchanged=True,summary=summary,training_started=False))
    finally:
        for h in reversed(handles):h.close()
    print((HERE/'RESULT.json').read_text())

if __name__=='__main__':main()
