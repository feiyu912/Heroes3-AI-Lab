"""Temporary exact disk-byte recovery for forensic re-extraction, never mounts WSL."""
import hashlib,json,os,shutil,subprocess,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
BACKUP=Path('/run/media/kaicheng/game/SharedAI/WSL-Backup-20261025/Ubuntu-2204-ext4.vhdx.zst')
OUT=HERE/'migration-repair-source/source.vhdx'
def write(v):
    v['seconds']=time.monotonic()-START
    (OUT.parent/'PROGRESS.json').write_text(json.dumps(v,indent=2))
START=time.monotonic()
manifest=json.loads(BACKUP.with_name('backup-manifest.json').read_text(encoding='utf-8-sig'))
assert manifest['verified'] and not OUT.exists()
assert shutil.disk_usage(OUT.parent).free>manifest['source_bytes']+10*2**30
before=BACKUP.stat();h=hashlib.sha256();n=0
with BACKUP.open('rb') as f:
    for b in iter(lambda:f.read(16*1024*1024),b''):
        h.update(b);n+=len(b)
        if n%(1024**3)<len(b):write(dict(phase='compressed_SHA256',bytes=n,total=before.st_size))
assert h.hexdigest()==manifest['compressed_sha256']
compressed_hash=h.hexdigest();h=hashlib.sha256();n=0
temp=OUT.with_suffix('.vhdx.partial');assert not temp.exists()
p=subprocess.Popen(['zstd','-dc','--',str(BACKUP)],stdout=subprocess.PIPE)
try:
    with temp.open('xb') as f:
        for b in iter(lambda:p.stdout.read(16*1024*1024),b''):
            f.write(b);h.update(b);n+=len(b)
            if n%(1024**3)<len(b):write(dict(phase='recover_exact_disk_bytes',bytes=n,total=manifest['source_bytes']))
        f.flush();os.fsync(f.fileno())
    assert p.wait()==0 and n==manifest['source_bytes'] and h.hexdigest()==manifest['source_sha256']
    os.link(temp,OUT);temp.unlink()
finally:
    if p.stdout:p.stdout.close()
    if p.poll() is None:p.terminate();p.wait()
after=BACKUP.stat();assert (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns)
result=dict(passed=True,temporary_source=str(OUT),bytes=n,sha256=h.hexdigest(),compressed_sha256=compressed_hash,backup_read_only_and_unchanged=True,registered_WSL=False,mounted_filesystem=False,original_frozen_files_modified=False,seconds=time.monotonic()-START)
(OUT.parent/'RESTORE.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
