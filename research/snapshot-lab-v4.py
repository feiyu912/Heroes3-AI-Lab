import datetime
import hashlib
import json
from pathlib import Path
import subprocess

root=Path('/mnt/g/Heroes3-AI-Lab');r=root/'research'
previous=json.loads((r/'runtime-manifest-v3.json').read_text())
selected_state=json.loads((r/'training-state.json').read_text(encoding='utf-8-sig'))
training_config=selected_state.get('training_config',{})
selected_model=json.loads((root/'models/challenge-v4/manifest.json').read_text())
native_export=root/'models/goal-v5-native-selected/manifest.json'
paths=list(r.glob('*'))+list(root.glob('*.md'))+list(root.glob('*.ps1'))
files=[dict(path=str(p.relative_to(root)),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(paths)
       if p.is_file() and p.suffix in ['.py','.sh','.ps1','.patch','.json','.md','.png','.svg'] and p.name!='runtime-manifest-v4.json']
manifest=dict(date=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(timespec='minutes'),
    engine_commit=previous['engine_commit'],gym_commit=previous['gym_commit'],selected_workers=24,
    native_patch='research/lab-v3-native.patch',files=files,
    cpu_dependencies=subprocess.check_output(['/root/heroes3-ai-lab/venv/bin/python','-m','pip','freeze'],text=True).splitlines(),
    gpu_dependencies=subprocess.check_output(['/root/heroes3-ai-lab/gpu-venv/bin/python','-m','pip','freeze'],text=True).splitlines(),
    model=selected_model,native_export=json.loads(native_export.read_text()) if native_export.exists() else None,
    notes=['Prior v3 manifest preserved as historical hashes; v4 tracks changed code and new results',
           'CPU game rules; CUDA learner inference/update; training opponent inference: '+training_config.get('fixed_opponent_inference','native CPU'),
           'Official ONNX weights imported and equivalence checked before adaptation',
           'Selected model mode: '+selected_model['selection'].get('finetuning_mode','unknown')+'; continuation mode: '+selected_state.get('finetuning_mode','unknown')+'; effective config in training-state.json',
           'One GPU trainer at a time; staged worker startup with memory reserve',
           'Fresh32-case512-battle suite excluded from model selection; non-normal endings/truncation count as non-wins'])
(r/'runtime-manifest-v4.json').write_text(json.dumps(manifest,indent=2))
print('Saved runtime-v4 manifest and artifact hashes')
