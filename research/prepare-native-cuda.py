"""Unpack a separate GPU runtime; do not replace either installed Python ORT."""
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

root=Path('/root/heroes3-ai-lab');r=Path('/mnt/g/Heroes3-AI-Lab/research')
wheel=next((root/'downloads').glob('onnxruntime_gpu-1.22.0-*.whl'))
destination=root/'onnxruntime-gpu-1.22/lib';destination.mkdir(parents=True,exist_ok=True)
extracted=[]
with zipfile.ZipFile(wheel) as archive:
    for name in archive.namelist():
        filename=Path(name).name
        if name.startswith('onnxruntime/capi/') and filename.startswith('libonnxruntime') and '.so' in filename:
            path=destination/filename;path.write_bytes(archive.read(name));extracted.append(str(path))
library=destination/'libonnxruntime.so.1.22.0'
assert library.exists()
for name in ['libonnxruntime.so','libonnxruntime.so.1']:
    link=destination/name
    if not link.exists():link.symlink_to(library.name)
(root/'profiles').mkdir(exist_ok=True)
subprocess.run(['g++','-std=c++17','-shared','-fPIC','-O2',str(r/'native-ort-cuda.cpp'),
    '-I'+str(root/'onnxruntime/include'),'-ldl','-o',str(destination/'lab-cuda-options.so')],check=True)
nvidia=root/'gpu-venv/lib/python3.10/site-packages/nvidia'
directories=[destination,*sorted(p for p in nvidia.glob('*/lib') if p.is_dir())]
manifest=dict(runtime='1.22.0',library_directory=str(destination),wheel=str(wheel),wheel_sha256=hashlib.sha256(wheel.read_bytes()).hexdigest(),
    extracted=extracted,library_paths=list(map(str,directories)),shim=str(destination/'lab-cuda-options.so'),
    source='https://onnxruntime.ai/docs/execution-providers/CUDA-ExecutionProvider.html',formal_use_approved_by_contract=False)
(r/'native-cuda-runtime.json').write_text(json.dumps(manifest,indent=2))
print(manifest,flush=True)
