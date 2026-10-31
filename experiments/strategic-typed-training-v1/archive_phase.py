"""Preserve full phase evidence including failed attempts, without traversing game assets."""
import hashlib,json,os,shutil
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=Path('/root/heroes3-ai-lab/evaluations');OUT=HERE/'native-evidence-phase-02'
names=['typed-onpolicy-cuda-episode-02','typed-onpolicy-balanced-01','typed-schema4-ack-drain-capsule-01','typed-terminal-ack-repro-01',
       'typed-onpolicy-balanced-ack-01','typed-onpolicy-balanced-ack-reconcile-01','typed-curriculum-paired-dev-01','typed-curriculum-paired-dev-02']
def manifest(root):
    result={}
    for folder,dirs,files in os.walk(root,followlinks=False):
        for name in sorted(dirs+files):
            p=Path(folder)/name;k=str(p.relative_to(root))
            if p.is_symlink():result[k]={'symlink':os.readlink(p)}
            elif p.is_file():result[k]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
    return result
OUT.mkdir(exist_ok=False);summary={}
for name in names:
    before=manifest(ROOT/name);shutil.copytree(ROOT/name,OUT/name,symlinks=True)
    assert before==manifest(ROOT/name)==manifest(OUT/name)
    (OUT/(name+'-manifest.json')).write_text(json.dumps(before,indent=2));summary[name]=len(before)
    print(json.dumps({'verified_copy':name,'records':len(before)}),flush=True)
(OUT/'ARCHIVE.json').write_text(json.dumps({'passed':True,'copies':summary,'no_asset_link_dereference':True},indent=2))
