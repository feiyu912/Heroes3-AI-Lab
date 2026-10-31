"""Archive evidence with regular-file hashes and link metadata, never asset traversal."""
import hashlib,json,os,shutil
from pathlib import Path

BASE=Path('/root/heroes3-ai-lab/evaluations')
OUT=Path('/mnt/g/Heroes3-AI-Lab/experiments/multihero-mechanism-probe-v1/native-evidence-01')
NAMES=['multihero-capsules-01','multihero-capsules-02','multihero-capsules-03',
       'multihero-probe-close-01','multihero-probe-close-02','multihero-probe-close-03',
       'multihero-probe-close-04','multihero-probe-transfer-01','multihero-probe-unhandled-01']
def manifest(root):
    records={}
    for folder,dirs,files in os.walk(root,followlinks=False):
        for name in sorted(dirs+files):
            p=Path(folder)/name;relative=str(p.relative_to(root))
            if p.is_symlink(): records[relative]={'symlink':os.readlink(p)}
            elif p.is_file(): records[relative]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
    return records
OUT.mkdir(exist_ok=False)
summary={}
for name in NAMES:
    source=BASE/name;before=manifest(source)
    shutil.copytree(source,OUT/name,symlinks=True)
    assert before==manifest(source)==manifest(OUT/name)
    summary[name]={'verified':True,'records':len(before)}
    (OUT/(name+'-manifest.json')).write_text(json.dumps(before,indent=2))
(OUT/'ARCHIVE.json').write_text(json.dumps({'passed':True,'source_root':str(BASE),'copies':summary,'asset_links_preserved_without_dereference':True},indent=2))
print(json.dumps(summary,indent=2))
