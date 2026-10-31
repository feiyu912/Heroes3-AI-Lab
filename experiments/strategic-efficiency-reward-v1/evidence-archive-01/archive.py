"""Compressed local evidence copy; verify every regular byte/link without extraction."""
import hashlib,json,os,tarfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=Path('/root/heroes3-ai-lab/evaluations')
NAMES=('strategic-efficiency-shared-train-01','strategic-efficiency-targets-01','strategic-efficiency-control-update-01','strategic-efficiency-treatment-update-01','strategic-efficiency-paired-dev-01')
def manifest():
    result={}
    for name in NAMES:
        base=ROOT/name
        if 'targets' in name:assert (base/'TARGETS.json').is_file()
        else:assert json.loads((base/'RESULT.json').read_text())['passed' if ('shared' in name or 'paired' in name) else 'completed_update']
        for folder,dirs,files in os.walk(base,followlinks=False):
            for item in dirs+files:
                p=Path(folder)/item;key=str(p.relative_to(ROOT))
                if p.is_symlink():result[key]={'symlink':os.readlink(p)}
                elif p.is_file():result[key]={'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
    return result
def main():
    before=manifest();archive=HERE/'raw-evidence.tar.gz';assert not archive.exists()
    with tarfile.open(archive,'x:gz',dereference=False,compresslevel=3) as out:
        for key in sorted(before):out.add(ROOT/key,arcname=key,recursive=False)
    assert manifest()==before,'Source changed while archiving'
    actual={}
    with tarfile.open(archive,'r:gz') as inp:
        for member in inp:
            assert member.name not in actual
            if member.issym():actual[member.name]={'symlink':member.linkname}
            else:
                assert member.isfile();data=inp.extractfile(member).read();actual[member.name]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
    assert actual==before,'Compressed evidence differs from source'
    (HERE/'MANIFEST.json').write_text(json.dumps(before,indent=2))
    report={'archive_integrity_passed':True,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'archive_bytes':archive.stat().st_size,
        'regular_files':sum('sha256' in v for v in before.values()),'symlinks':sum('symlink' in v for v in before.values()),
        'source_after_and_archive_regular_bytes_exact':True,'no_asset_symlink_dereference':True,'archive_extracted':False,
        'original_Linux_evidence_retained':True,'ability_improvement_claim':False,'names':NAMES}
    (HERE/'ARCHIVE.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if __name__=='__main__':main()
