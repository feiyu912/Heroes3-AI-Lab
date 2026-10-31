"""Canonical flock descriptions and cleanup covering Ninja/native child groups by SID."""
import contextlib,fcntl,os,signal,time
from pathlib import Path
from common import RESOURCE,leases,write
@contextlib.contextmanager
def owned_resources(out):
 handles=[]
 try:
  paths=[RESOURCE/n for n in ('.gpu-learner-lock','.pool-lock')]
  for path in paths:
   assert path.is_file()
   h=path.open('r+');handles.append(h);fcntl.flock(h,fcntl.LOCK_EX|fcntl.LOCK_NB)
  entries=[leases.metadata(h,p) for h,p in zip(handles,paths)]
  write(Path(out)/'LEASES.json',leases.verify(entries,paths))
  yield entries
 finally:
  for h in reversed(handles):fcntl.flock(h,fcntl.LOCK_UN);h.close()
def session_processes(sid):
 rows=[]
 for p in Path('/proc').glob('[0-9]*/stat'):
  try:
   f=p.read_text().rsplit(')',1)[1].split()
   if int(f[3])==sid and f[0] not in ('Z','X'):rows.append(dict(pid=int(p.parent.name),pgrp=int(f[2]),sid=int(f[3])))
  except (FileNotFoundError,ProcessLookupError,ValueError,IndexError):continue
 return rows
def signal_session(sid,sig):
 assert sid!=os.getsid(0)
 for pgrp in {r['pgrp'] for r in session_processes(sid)}:
  try:os.killpg(pgrp,sig)
  except ProcessLookupError:pass
def finish_session(proc):
 if proc is None:return
 previous={s:signal.getsignal(s) for s in (signal.SIGTERM,signal.SIGINT)}
 for s in previous:signal.signal(s,signal.SIG_IGN)
 try:
  if session_processes(proc.pid):signal_session(proc.pid,signal.SIGTERM)
  deadline=time.monotonic()+5
  while session_processes(proc.pid) and time.monotonic()<deadline:time.sleep(.05)
  while session_processes(proc.pid):signal_session(proc.pid,signal.SIGKILL);time.sleep(.05)
  proc.wait()
 finally:
  for s,h in previous.items():signal.signal(s,h)
