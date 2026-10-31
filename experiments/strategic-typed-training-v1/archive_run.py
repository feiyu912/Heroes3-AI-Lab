"""Archive one completed immutable run; preserve asset links without traversal."""
import argparse,hashlib,json,os,shutil
from pathlib import Path
def manifest(root):
    result={}
    for folder,dirs,files in os.walk(root,followlinks=False):
        for name in sorted(dirs+files):
            p=Path(folder)/name;k=str(p.relative_to(root))
            if p.is_symlink():result[k]={'symlink':os.readlink(p)}
            elif p.is_file():result[k]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
    return result
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
before=manifest(a.source);a.out.mkdir(parents=True,exist_ok=False);shutil.copytree(a.source,a.out/'run',symlinks=True)
assert before==manifest(a.source)==manifest(a.out/'run')
(a.out/'MANIFEST.json').write_text(json.dumps(before,indent=2));(a.out/'ARCHIVE.json').write_text(json.dumps({'passed':True,'source':str(a.source),'records':len(before),'no_link_dereference':True},indent=2));print(json.dumps({'passed':True,'records':len(before)}))
