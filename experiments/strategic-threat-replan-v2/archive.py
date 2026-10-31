"""Archive completed native evidence only; keep symlink metadata and source originals."""
import argparse,hashlib,json,os,shutil
from pathlib import Path
ROOT=Path('/root/heroes3-ai-lab/evaluations')
def manifest(root):
    answer={}
    for folder,dirs,files in os.walk(root,followlinks=False):
        for name in sorted(dirs+files):
            p=Path(folder)/name;k=str(p.relative_to(root))
            if p.is_symlink():answer[k]={'symlink':os.readlink(p)}
            elif p.is_file():answer[k]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
    return answer
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--name',action='append',required=True);a=p.parse_args()
a.out.mkdir(parents=True,exist_ok=False);summary={}
for name in a.name:
    assert Path(name).name==name;source=ROOT/name
    proof=json.loads((source/('RESULT.json' if (source/'RESULT.json').exists() else 'EXECUTION.json')).read_text())
    assert proof.get('passed') is True or (proof.get('game_completed') is True and proof.get('client_exit')==0 and proof.get('transport_drained') is True)
    before=manifest(source);dest=a.out/name;shutil.copytree(source,dest,symlinks=True)
    assert before==manifest(source)==manifest(dest)
    (a.out/(name+'-manifest.json')).write_text(json.dumps(before,indent=2))
    summary[name]=dict(regular_files=sum('sha256' in x for x in before.values()),symlinks=sum('symlink' in x for x in before.values()))
    print(json.dumps({'verified_copy':name,**summary[name]}),flush=True)
(a.out/'ARCHIVE.json').write_text(json.dumps(dict(passed=True,copies=summary,no_asset_link_dereference=True),indent=2))
