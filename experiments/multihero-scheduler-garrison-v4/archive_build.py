"""Copy verified capsule payloads and build proof without touching native inputs."""
from pathlib import Path
import hashlib,json,shutil
HERE=Path(__file__).resolve().parent
ROOT=Path('/root/heroes3-ai-lab/evaluations/multihero-scheduler-garrison-capsule-04')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    out=HERE/'build-evidence-04';out.mkdir(exist_ok=False)
    files={}
    paths=['EXECUTION.json','PLAN.json','restore-accepted-build.log','vcmiclient-accepted-ldd.log','vcmiserver-accepted-ldd.log']
    for arm in ('baseline','filtered'):
        paths.extend(arm+'/'+n for n in ('BUILD_ATTESTATION.json','build.log','base-source-manifest.json','build-source-manifest.json','bin/vcmiclient','bin/vcmiserver','bin/libvcmi.so','source-snapshot/AI/DirectorAI/CDirectorAI.cpp','source-snapshot/AI/DirectorAI/CDirectorAI.h'))
    for rel in paths:
        source=ROOT/rel;target=out/rel;target.parent.mkdir(exist_ok=True,parents=True)
        shutil.copy2(source,target);assert sha(source)==sha(target)
        files[rel]={'sha256':sha(target),'bytes':target.stat().st_size}
    record={'passed':True,'source':str(ROOT),'files':files,'all_files_rehashed_equal':True,
        'full_engine_checkout_copied':False,'scope':'Exact compiled candidate code, executable/library payloads and complete source manifests/build proof; base full checkout remains at attested WSL path.'}
    (out/'ARCHIVE.json').write_text(json.dumps(record,indent=2));print(json.dumps({'passed':True,'files':len(files),'bytes':sum(x['bytes'] for x in files.values())}))
if __name__=='__main__':main()
