"""Copy a complete resumable checkpoint to the Windows workspace, with checksums."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import zipfile
import torch
from lab_io import atomic_json

torch.set_num_threads(1)
r=Path('/mnt/g/Heroes3-AI-Lab/research')
report_path=Path(sys.argv[1]) if len(sys.argv)>1 else r/'v5-diverse-heads.json'
data=json.loads(report_path.read_text())
folder=Path(data['checkpoint']).parent
assert folder.is_relative_to('/root/heroes3-ai-lab/models')
checkpoint=None
for candidate in sorted(folder.glob('update-*.pt'),key=lambda p:int(p.stem.split('-')[-1]),reverse=True):
    try:
        with zipfile.ZipFile(candidate) as archive:assert archive.testzip() is None
        state=torch.load(candidate,map_location='cpu',weights_only=True)
    except (OSError,zipfile.BadZipFile,RuntimeError,EOFError,AssertionError):continue
    assert state['completed_updates']==int(candidate.stem.split('-')[-1])
    assert 'optimizer_state_dict' in state and 'cuda_rng_states' in state
    assert all(torch.isfinite(value).all() for model in state['models'].values() for value in model['weights'].values())
    checkpoint=candidate;break
assert checkpoint is not None,'No complete resumable model found'
target=r.parent/'models/goal-v5-recovery'
target.mkdir(parents=True,exist_ok=True)
destination=target/f'{report_path.stem}-{folder.name}-{checkpoint.name}'
temporary=destination.with_name(destination.name+'.tmp-'+str(os.getpid()))
try:
    shutil.copyfile(checkpoint,temporary)
    checksum=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    digest=checksum(checkpoint);assert digest==checksum(temporary)
    os.replace(temporary,destination)
finally:
    if temporary.exists():temporary.unlink()
manifest=dict(source_checkpoint=str(checkpoint),backup_checkpoint=str(destination),sha256=digest,
    completed_updates=state['completed_updates'],environment_steps=state['environment_steps'],
    config=state['config'],resume_available=True,weights_finite=True,zip_crc_verified=True,
    source_report=str(report_path),validation_status='Not yet evaluated; backup is not evidence of playing strength')
atomic_json(destination.with_suffix('.json'),manifest)
atomic_json(target/'latest.json',manifest)
print(json.dumps(manifest,indent=2),flush=True)
