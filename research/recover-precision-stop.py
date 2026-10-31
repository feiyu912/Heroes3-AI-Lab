"""Archive failed numerical check and resume the latest verified optimizer state."""
import hashlib
import json
from pathlib import Path
import shutil
import torch

r=Path('/mnt/g/Heroes3-AI-Lab/research')
data=json.loads((r/'recovered-adapted-v4.json').read_text())
folder=Path(data['checkpoint']).parent
saved={str(int(p.stem.split('-')[-1])):str(p) for p in folder.glob('update-*.pt')}
original=json.loads((r/'challenge-paused-state.json').read_text())
saved[str(original['completed_updates'])]=original['checkpoint']
checkpoint=Path(saved[str(max(map(int,saved)))])
state=torch.load(checkpoint,map_location='cpu',weights_only=True)
assert state['completed_updates']==96 and 'optimizer_state_dict' in state
for name in ['challenge24-pipeline-progress.json','recovered-adapted-v4.json','recovered-adapted-v4.log',
             'run-recovered-head-adaptation-resume.log','goal-v5-control.json','challenge-paused-state.json']:
    path=r/name;target=r/(path.stem+'-precision-stop'+path.suffix)
    assert not target.exists(),target
    shutil.copyfile(path,target)
progress=json.loads((r/'challenge24-pipeline-progress.json').read_text())
assert len(progress)==3 and progress[-1]['returncode']==1
(r/'challenge24-pipeline-progress.json').write_text(json.dumps(progress[:2],indent=2))
manifest=dict(original,status='checkpoint_recovery',checkpoint=str(checkpoint),
    completed_updates=96,remaining_updates=32,environment_steps=state['environment_steps'],
    saved_checkpoints=saved,sha256=hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
    note='Numerical recomputation assertion at update111; last complete optimizer state96 restored. Failed14 updates discarded, not claimed as retained progress. Fresh battles resume phase6; global update labels remain correct.')
backup=r.parent/'models/challenge-paused/recovered-latest.pt'
shutil.copyfile(checkpoint,backup)
assert hashlib.sha256(backup.read_bytes()).hexdigest()==manifest['sha256']
(r/'challenge-paused-state.json').write_text(json.dumps(manifest,indent=2))
print(str(checkpoint),flush=True)
