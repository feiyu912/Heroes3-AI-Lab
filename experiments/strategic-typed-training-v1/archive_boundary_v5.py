"""Preserve all real boundary arms/checkpoints, including physical serialization differences."""
import hashlib,json,os,shutil
from pathlib import Path
HERE=Path(__file__).resolve().parent
SOURCE=Path('/root/heroes3-ai-lab/evaluations/typed-native-cuda-boundary-v5-01')
OUT=HERE/'native-evidence-boundary-v5-01'
def manifest(root):
    result={}
    for folder,dirs,files in os.walk(root,followlinks=False):
        for name in sorted(dirs+files):
            p=Path(folder)/name;k=str(p.relative_to(root))
            if p.is_symlink():result[k]={'symlink':os.readlink(p)}
            elif p.is_file():result[k]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
    return result
assert json.loads((SOURCE/'COMPARISON.json').read_text())['passed']
assert json.loads((HERE/'native-boundary-v5-audit-01/AUDIT.json').read_text())['passed']
before=manifest(SOURCE);shutil.copytree(SOURCE,OUT,symlinks=True)
assert before==manifest(SOURCE)==manifest(OUT)
(OUT/'ARCHIVE_MANIFEST.json').write_text(json.dumps(before,indent=2))
report=dict(passed=True,records=len(before),regular_files=sum('sha256' in e for e in before.values()),
    symlinks=sum('symlink' in e for e in before.values()),no_asset_link_dereference=True,
    scope='All4 games, original logs, failed-free raw audits, CUDA admissions and all continuous/split/resumed checkpoint files retained')
(OUT/'ARCHIVE.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
