"""Verified ordinary-file archive; external resource symlinks recorded, not traversed."""
from pathlib import Path
import hashlib,json,os,shutil,time
HERE=Path(__file__).resolve().parent
SOURCE=Path('/root/heroes3-ai-lab/evaluations/strategic-active-calibration-v2-native-01')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    out=HERE/'calibration-delivery-01';out.mkdir(exist_ok=False)
    archive=out/'archive';archive.mkdir();entries={};count=total=0;links={};start=time.monotonic()
    result=json.loads((SOURCE/'RESULT.json').read_text());assert result['passed'] and len(result['results'])==12
    for root,dirs,files in os.walk(SOURCE,followlinks=False):
        for name in dirs+files:
            p=Path(root)/name;rel=str(p.relative_to(SOURCE));target=archive/rel
            if p.is_symlink():links[rel]=os.readlink(p);continue
            if p.is_dir():target.mkdir(exist_ok=True,parents=True);continue
            assert p.is_file();target.parent.mkdir(exist_ok=True,parents=True);shutil.copy2(p,target)
            digest=sha(p);assert digest==sha(target)
            entries[rel]={'sha256':digest,'bytes':p.stat().st_size};count+=1;total+=p.stat().st_size
            if count%1000==0:(out/'PROGRESS.json').write_text(json.dumps(dict(verified_files=count,bytes=total,final_certificate=False)))
    report={'passed':True,'source':str(SOURCE),'all_ordinary_files_copied_and_hashed_equal':True,'files':entries,'symlink_targets_not_traversed':links,'ordinary_files':count,'bytes':total,'seconds':time.monotonic()-start,'training_samples':0,'optimizer_steps':0,'scope':'Complete calibration run ordinary files. Shared Data/Mods/client symlinks remain external dependencies, preserved as target metadata only. Existing fixed model/capsule are separately pinned in run plans.'}
    (out/'ARCHIVE.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k not in ('files','symlink_targets_not_traversed')},indent=2))
if __name__=='__main__':main()
