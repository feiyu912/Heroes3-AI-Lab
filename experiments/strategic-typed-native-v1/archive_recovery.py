"""Supplement evidence archive, no overwrite or asset dereference."""
import hashlib,json,os,shutil
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=Path('/root/heroes3-ai-lab/evaluations');OUT=HERE/'native-evidence-02'
def manifest(root):
    result={}
    for folder,dirs,files in os.walk(root,followlinks=False):
        for n in dirs+files:
            p=Path(folder)/n;k=str(p.relative_to(root))
            if p.is_symlink():result[k]={'symlink':os.readlink(p)}
            elif p.is_file():result[k]={'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
    return result
OUT.mkdir(exist_ok=False);summary={}
for name in ['typed-schema4-turnstart-restore-01','typed-schema4-blue-nk-01']:
    before=manifest(ROOT/name);shutil.copytree(ROOT/name,OUT/name,symlinks=True)
    assert before==manifest(ROOT/name)==manifest(OUT/name)
    (OUT/(name+'-manifest.json')).write_text(json.dumps(before,indent=2));summary[name]=len(before)
(OUT/'ARCHIVE.json').write_text(json.dumps({'passed':True,'copies':summary,'asset_links_not_dereferenced':True},indent=2));print(json.dumps(summary))
