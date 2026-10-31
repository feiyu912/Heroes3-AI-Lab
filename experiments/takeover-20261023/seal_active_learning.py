"""Seal the prepared epoch once, after read-only CPU checks and protected hashes."""
import hashlib,json,shutil,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
RUN=HERE.parent/'strategic-active-opponent-learning-20261024'
sys.path.insert(0,str(RUN))
from pipeline_common import BASE,source_inputs,capsule_inputs,DEFAULT_CAPSULE,DEFAULT_INITIAL,sha
from collect_episode_v5 import owned_resources
def main():
    target=RUN/'SOURCE_FREEZE.json';assert not target.exists()
    preflight=Path('/root/heroes3-ai-lab/evaluations/strategic-active-learning-preflight-02')
    assert json.loads((preflight/'AUDIT.json').read_text())['passed']
    protected=json.loads((HERE/'first-pilot-protection.json').read_text())['protected_current_files']
    with owned_resources():
        actual={path:sha(path) for path in protected};assert actual==protected
        gpu=subprocess.run(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],capture_output=True,text=True,check=True).stdout.strip()
        assert not gpu,'A GPU compute process is active; preserve lock ownership'
        live=[]
        for path in Path('/proc').glob('[0-9]*/comm'):
            try:
                if path.read_text().strip() in ('vcmiclient','vcmiserver'):live.append(str(path.parent))
            except FileNotFoundError:pass
        assert not live,'Native process still active'
        protection=dict(passed=True,all17_exact=True,protected_current_files=actual,resource_locks_acquired_GPU_then_pool_and_released=True,GPU_compute=gpu,native_processes=live)
    (RUN/'preflight-evidence').mkdir()
    for name in ('AUDIT.json','codec/AUDIT.json','cached-raw/AUDIT.json'):
        output=RUN/'preflight-evidence'/name;output.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(preflight/name,output);assert sha(output)==sha(preflight/name)
    (RUN/'preflight-evidence/PROTECTION.json').write_text(json.dumps(protection,indent=2))
    deriv=json.loads((RUN/'DERIVATION.json').read_text())
    deriv['post_derivation_changes']=['load_admitted and model epoch explicitly updated; old initialization lineage retained','new trained codec requires registered treatment','runtime initial owned army proof required before admission','DEV map bytes frozen before training','new cached immutable log parser independently compared on long cell','controller resource guard before/after every stage; serial heavy analysis','actual CUDA restoration auditor with twelve mutation negatives reused and rebound']
    deriv['actual_derived_python_sha256']={str(path):sha(path) for folder in (RUN,BASE) for path in folder.glob('*.py')}
    (RUN/'DERIVATION.json').write_text(json.dumps(deriv,indent=2))
    files=source_inputs()+capsule_inputs(DEFAULT_CAPSULE)+[DEFAULT_INITIAL]
    frozen={str(path):sha(path) for path in files}
    target.write_text(json.dumps(dict(schema='strategic-active-opponent-paired-source-freeze-v1',files=frozen,prepared_check=str(preflight/'AUDIT.json'),prepared_check_sha256=sha(preflight/'AUDIT.json'),native_runs=0,optimizer_steps=0),indent=2))
    assert all(sha(path)==h for path,h in frozen.items())
    print(json.dumps(dict(sealed=True,files=len(frozen),source_freeze_sha256=sha(target),all17_protected_exact=True,native_runs=0,optimizer_steps=0)))
if __name__=='__main__':main()
