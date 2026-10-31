"""Preserve the stopped invalid proxy attempt explicitly as failed, never as a score."""
import hashlib,json,os,shutil
from pathlib import Path
HERE=Path(__file__).resolve().parent;SOURCE=Path('/root/heroes3-ai-lab/evaluations/typed-clearance-proxy-paired-01');OUT=HERE/'failed-proxy-evidence-01'
proof=json.loads((SOURCE/'RESULT.json').read_text());assert proof['passed'] is False
writers=[]
for p in Path('/proc').iterdir():
    if not p.name.isdigit() or int(p.name)==os.getpid():continue
    try:
        command=(p/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
        if str(SOURCE) in command:writers.append(dict(pid=p.name,command=command))
    except OSError:continue
assert not writers,writers
def manifest(root):
    result={}
    for folder,dirs,files in os.walk(root,followlinks=False):
        for name in dirs+files:
            p=Path(folder)/name;k=str(p.relative_to(root))
            if p.is_symlink():result[k]={'symlink':os.readlink(p)}
            elif p.is_file():result[k]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
    return result
before=manifest(SOURCE);shutil.copytree(SOURCE,OUT,symlinks=True);assert before==manifest(SOURCE)==manifest(OUT)
(OUT/'ARCHIVE_MANIFEST.json').write_text(json.dumps(before,indent=2))
report=dict(archive_passed=True,experiment_passed=False,records=len(before),no_matching_live_processes=True,no_asset_link_dereference=True,
    native_outcome_scored=False,training_samples=0,optimizer_steps=0,source_result_preserved=True)
(OUT/'ARCHIVE.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
