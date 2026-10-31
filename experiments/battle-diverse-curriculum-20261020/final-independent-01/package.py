"""Plan/copy a SHA-verified completed evidence package; never edits original artifacts."""
import argparse,hashlib,json,shutil
from pathlib import Path
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--audit',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--execute',action='store_true');a=p.parse_args()
    report=json.loads(a.audit.read_text());assert report.get('passed') and report.get('final_experiment_certified'),'Only the completed independent audit can be archived as certified'
    records=report['artifact_index']+[dict(path=str(a.audit.resolve()),sha256=sha(a.audit),bytes=a.audit.stat().st_size),dict(path=str(Path(__file__).resolve()),sha256=sha(Path(__file__)),bytes=Path(__file__).stat().st_size)]
    mapping=[];unique={}
    for record in records:
        source=Path(record['path']);assert source.is_file() and source.stat().st_size==record['bytes'] and sha(source)==record['sha256']
        destination='artifacts/'+record['sha256']+'/'+source.name;mapping.append(dict(record,destination=destination));unique.setdefault(destination,source)
    a.out.mkdir(parents=True,exist_ok=False);plan=dict(schema='battle-diverse60-verified-evidence-package-v1',execute=a.execute,copy_completed=False,source_files_never_modified=True,
        original_audit_sha256=sha(a.audit),unique_files=len(unique),estimated_bytes=sum(p.stat().st_size for p in unique.values()),files=mapping)
    (a.out/'ARCHIVE_PLAN.json').write_text(json.dumps(plan,indent=2)+'\n')
    if not a.execute:print(json.dumps(dict(plan_only=True,unique_files=len(unique),estimated_bytes=plan['estimated_bytes'])));return
    assert shutil.disk_usage(a.out).free>plan['estimated_bytes']+2*1024**3,'Insufficient archive disk reserve'
    for destination,source in unique.items():
        target=a.out/destination;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
        assert sha(target)==target.parent.name
    plan['copy_completed']=True;(a.out/'ARCHIVE_VERIFIED.json').write_text(json.dumps(plan,indent=2)+'\n');print(json.dumps(dict(copy_completed=True,files=len(unique))))
if __name__=='__main__':main()
