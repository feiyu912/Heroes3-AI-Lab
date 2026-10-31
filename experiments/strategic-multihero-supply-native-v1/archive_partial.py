"""Preserve a stopped partial research run; never manufacture completion or score."""
import argparse,hashlib,json,os,shutil
from pathlib import Path
ROOT=Path('/root/heroes3-ai-lab/evaluations')
def manifest(root):
    out={}
    for folder,dirs,files in os.walk(root,followlinks=False):
        for name in dirs+files:
            p=Path(folder)/name;key=str(p.relative_to(root))
            if p.is_symlink():out[key]=dict(symlink=os.readlink(p))
            elif p.is_file():out[key]=dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size)
    return out
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--name',required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    assert Path(a.name).name==a.name
    source=ROOT/a.name;assert source.resolve().parent==ROOT.resolve()
    execution=json.loads((source/'EXECUTION.json').read_text());assert execution['game_completed'] is False and execution['winner'] is None
    assert execution['optimizer_steps']==execution['training_samples']==0
    for p in Path('/proc').iterdir():
        if not p.name.isdigit() or int(p.name)==os.getpid():continue
        try:command=(p/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
        except OSError:continue
        assert str(source) not in command,dict(pid=p.name,command=command)
    before=manifest(source);shutil.copytree(source,a.out,symlinks=True)
    assert before==manifest(source)==manifest(a.out)
    (a.out/'ARCHIVE_MANIFEST.json').write_text(json.dumps(before,indent=2))
    report=dict(archive_passed=True,whole_game_completed=False,whole_game_score_eligible=False,mechanics_qualified_by_archive=False,
        source_execution_preserved=True,records=len(before),regular_files=sum('sha256' in v for v in before.values()),symlinks=sum('symlink' in v for v in before.values()),
        no_asset_link_dereference=True,optimizer_steps=0,training_samples=0,expert_labels=0,
        limitation='Archive integrity only. Partial suboperation qualification and any cargo-delivery failure require the independent raw audit. This record has no win/loss.')
    (a.out/'ARCHIVE.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
if __name__=='__main__':main()
