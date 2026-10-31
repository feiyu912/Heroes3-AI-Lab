"""Preserve failed version and derive the one-path launcher correction."""
from pathlib import Path
import json,hashlib,shutil
ROOT=Path(__file__).resolve().parent.parent
old=ROOT/'battle-training-resume-20261020';new=ROOT/'battle-training-resume-20261020-v2'
new.mkdir(exist_ok=False)
for p in list(old.glob('*.py'))+[old/'PLAN.md']:
    shutil.copyfile(p,new/p.name)
path=new/'run.py';text=path.read_text()
a="LAB_WORKER_ROOT=str(a.out/'bootstrap')";b="LAB_WORKER_ROOT=str(LAB/'workers'/(a.out.name+'-bootstrap'))"
assert text.count(a)==1;path.write_text(text.replace(a,b))
(new/'BOOTSTRAP_FIX.json').write_text(json.dumps(dict(parent=str(old),parent_run_sha256=hashlib.sha256((old/'run.py').read_bytes()).hexdigest(),
    failure='prepare-worker containment refused evaluations/bootstrap before CUDA/native/optimizer',
    change='bootstrap worker under canonical workers directory',native_games=0,optimizer_steps=0),indent=2))
