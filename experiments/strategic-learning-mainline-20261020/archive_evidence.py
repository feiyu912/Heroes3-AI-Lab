"""Copy terminal failed/successful batches and DEV evidence; SHA integrity is not strength."""
import argparse,hashlib,json,os,shutil
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=Path('/root/heroes3-ai-lab/evaluations')
NAMES=('strategic-mainline-temperature2-train-01','strategic-mainline-temperature2-train-02','strategic-mainline-temperature2-dev-01')
def manifest(root):
    found={}
    for folder,dirs,files in os.walk(root,followlinks=False):
        for name in dirs+files:
            p=Path(folder)/name;relative=str(p.relative_to(root))
            if p.is_symlink():found[relative]={'symlink':os.readlink(p)}
            elif p.is_file():found[relative]={'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
    return found
def main():
    a=argparse.ArgumentParser();a.add_argument('--out',type=Path,required=True);args=a.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    reports={}
    for name in NAMES:
        source=ROOT/name;result=json.loads((source/'RESULT.json').read_text());assert type(result['passed']) is bool
        before=manifest(source);destination=args.out/name;shutil.copytree(source,destination,symlinks=True)
        assert before==manifest(source)==manifest(destination)
        (args.out/(name+'-manifest.json')).write_text(json.dumps(before,indent=2))
        reports[name]={'experiment_passed':result['passed'],'regular_files':sum('sha256' in v for v in before.values()),'symlinks':sum('symlink' in v for v in before.values())}
        print(json.dumps({'verified':name,**reports[name]}),flush=True)
    (args.out/'ARCHIVE.json').write_text(json.dumps({'archive_integrity_passed':True,'copies':reports,'no_asset_link_dereference':True,'ability_improvement_claim':False,'scope':'All attempts preserved, including invalid first batch. Original Linux evidence retained.'},indent=2))
if __name__=='__main__':main()
