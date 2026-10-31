"""Atomic experiment metadata and per-run source provenance."""
import hashlib
import json
import os
from pathlib import Path
import shutil


def atomic_json(path,value):
    path=Path(path);temporary=path.with_name(path.name+'.tmp-'+str(os.getpid()))
    try:
        with temporary.open('w') as stream:
            json.dump(value,stream,indent=2);stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,path)
    finally:
        if temporary.exists():temporary.unlink()


def capture_source(folder,trainer):
    source=Path(__file__).parent;target=Path(folder)/'source'
    target.mkdir(parents=True,exist_ok=True)
    names=[trainer,'recovered-graph.py','full_graph_policy.py','masked_ppo.py','vector_env.py',
        'decision_model.py','battle_features.py','lab-env.py','run-lab.sh','prepare-worker.py','native_cuda_env.py','gpu_opponent.py','lab_io.py']
    files=[]
    for name in names:
        destination=target/name;shutil.copyfile(source/name,destination)
        files.append(dict(name=name,sha256=hashlib.sha256(destination.read_bytes()).hexdigest()))
    atomic_json(target/'manifest.json',dict(files=files,note='Copied at run startup before optimizer updates. Native engine/gym commits are recorded separately.'))
    return str(target)
