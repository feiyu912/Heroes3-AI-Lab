"""Verified evidence copy, preserving links without expanding game assets."""
import hashlib,json,os,shutil
from pathlib import Path
HERE=Path(__file__).resolve().parent;LAB=Path('/root/heroes3-ai-lab');EVAL=LAB/'evaluations'
OUT=HERE/'native-evidence-01'
sources={name:EVAL/name for name in ['typed-schema4-capsule-01','typed-schema4-diagnostic-01','typed-schema4-diagnostic-02','typed-schema4-policy-fullgame-01','typed-schema4-policy-fullgame-02','multihero-complete-assets-01']}
sources['v8-control-native']=LAB/'workers/adv-runs/typed-battle-loop-v8-control-01-2026102601-gjymqstd'
sources['v8-control-broker']=LAB/'workers/strategy-agent-runs/typed-battle-loop-v8-control-01-el42rmm0'
def manifest(root):
    records={}
    for folder,dirs,files in os.walk(root,followlinks=False):
        for name in sorted(dirs+files):
            p=Path(folder)/name;relative=str(p.relative_to(root))
            if p.is_symlink():records[relative]={'symlink':os.readlink(p)}
            elif p.is_file():records[relative]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
    return records
OUT.mkdir(exist_ok=False);summary={}
for name,source in sources.items():
    before=manifest(source);shutil.copytree(source,OUT/name,symlinks=True)
    assert before==manifest(source)==manifest(OUT/name)
    summary[name]={'source':str(source),'records':len(before),'verified':True}
    (OUT/(name+'-manifest.json')).write_text(json.dumps(before,indent=2))
(OUT/'ARCHIVE.json').write_text(json.dumps({'passed':True,'copies':summary,'no_asset_link_dereference':True},indent=2))
print(json.dumps(summary,indent=2))
