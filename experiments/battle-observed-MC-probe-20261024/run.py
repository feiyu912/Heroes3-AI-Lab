"""Lease-owning plan/execute wrapper; no Torch in controller."""
import argparse,contextlib,fcntl,json,os,signal,sys
from pathlib import Path
import leases
HERE=Path(__file__).resolve().parent
def sha(p):return __import__('hashlib').sha256(Path(p).read_bytes()).hexdigest()
@contextlib.contextmanager
def owned():
    handles=[]
    try:
        for path in leases.PATHS:
            f=path.open('a+');handles.append(f);fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        yield handles
    finally:
        for f in reversed(handles):f.close()
def stop(signum,frame):raise KeyboardInterrupt('Probe controller interrupted')
signal.signal(signal.SIGTERM,stop)
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--execute',action='store_true');a=p.parse_args()
    freeze=json.loads((HERE/'SOURCE_FREEZE.json').read_text());assert all(sha(p)==h for p,h in freeze['input_sha256'].items())
    a.out.mkdir(parents=True,exist_ok=False);(a.out/'PLAN.json').write_text(json.dumps(dict(execute=a.execute,freeze_sha256=sha(HERE/'SOURCE_FREEZE.json'),new_native_games=0,reference_reproduction_planned_Adam=128,MC_maximum_Adam=128),indent=2))
    if not a.execute:return 0
    code=1
    try:
        with owned() as handles,(a.out/'learner.log').open('w') as stream:
            env=dict(os.environ,TERMINAL_CREDIT_LEASES=json.dumps([leases.metadata(f,p) for f,p in zip(handles,leases.PATHS)]),CUBLAS_WORKSPACE_CONFIG=':4096:8')
            code=leases.run_owned(['/root/heroes3-ai-lab/gpu-venv/bin/python',str(HERE/'learner.py'),'--out',str(a.out)],env=env,stream=stream,pass_fds=tuple(f.fileno() for f in handles))
    finally:leases.finish_owned_groups()
    return code
if __name__=='__main__':raise SystemExit(main())
