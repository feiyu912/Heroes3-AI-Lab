"""Register final snapshot expectations only; never acquire locks or query GPU."""
import hashlib,json
from pathlib import Path

HERE=Path(__file__).resolve().parent;BASE=HERE.parent;PROJECT=BASE.parent.parent
PROFILE=Path('/home/kaicheng/Documents/Codex/2026-10-24/hello/outputs/Heroes3-Native-20261025')
MIGRATION=Path('/home/kaicheng/Documents/Codex/2026-10-24/hello/outputs/WSL迁出-20261025')
BACKUP=Path('/run/media/kaicheng/game/SharedAI/WSL-Backup-20261025/Ubuntu-2204-ext4.vhdx.zst')
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
    out=HERE/'PLAN.json';assert not out.exists()
    baseline=PROJECT/'experiments/takeover-20261023/first-pilot-protection.json';expected=json.loads(baseline.read_text())['protected_current_files'];assert len(expected)==17
    active={str(PROFILE/p.removeprefix('/root/')):s for p,s in expected.items()}
    engines={}
    for name in ('libvcmi.so','libmlclient.so','libmlserverplugin.so','vcmiclient','vcmiserver'):
        engines[str(PROFILE/'runtime/engine-battle'/name)]=expected['/root/heroes3-ai-lab/src/gym/vcmi/rel/bin/'+name]
    for name in ('libvcmi.so','vcmiclient','vcmiserver'):
        engines[str(PROFILE/'runtime/engine-strategic'/name)]=expected['/root/heroes3-ai-lab/src/vcmi-adv-build/bin/'+name]
    freezes={};certs={}
    for folder in ('refill-candidate-draft','learner-recovery','learner-recovery-v2'):
        manifest=BASE/folder/'SOURCE_FREEZE.json';d=json.loads(manifest.read_text());certs[str(manifest)]=sha(manifest)
        for p,s in d['files'].items():freezes[str(manifest.parent/p)]=s
        for p,s in d.get('candidate_payloads',{}).items():freezes[str(manifest.parent/'candidate'/p)]=s
    history=BASE/'evidence-review/history-review-01';h=json.loads((history/'AUDIT.json').read_text());assert h['passed']
    profile_cert=PROFILE/'AUDIT.json';build=json.loads(profile_cert.read_text());assert build['passed']
    cert_paths=[baseline,profile_cert,PROFILE/'PLAN.json',BASE/'python-integrity/PROFILE_CERTIFICATE.json',BASE/'python-integrity/actual-02/AUDIT.json',BASE/'migration-repair-source/RESTORE.json',BASE/'migration-repair-source/CLEANUP.json',history/'AUDIT.json',BASE/'evidence-review/DIRECT_FILE_HASH_AUDIT.json',BASE/'toolchain-inputs/AUDIT.json',BACKUP.with_name('backup-manifest.json'),HERE/'audit.py',HERE/'prepare.py']
    for p in cert_paths:certs[str(p)]=sha(p)
    resource=MIGRATION/'files/root/heroes3-ai-lab/evaluations'
    plan=dict(active_profile=str(PROFILE),active_protected_sha256=active,active_engine_sha256=engines,certificate_sha256=certs,frozen_payload_sha256=freezes,history_artifact_sha256={str(history/'CORRECTED_MANIFEST.jsonl'):h['manifest_sha256'],str(history/'corrected-history-delta.tar.zst'):h['delta_sha256']},resource_lock_paths=[str(resource/'.gpu-learner-lock'),str(resource/'.pool-lock')],profile_build_certificate=str(profile_cert),venv_certificate=str(BASE/'python-integrity/PROFILE_CERTIFICATE.json'),cleanup_certificate=str(BASE/'migration-repair-source/CLEANUP.json'),temporary_source=str(BASE/'migration-repair-source/source.vhdx'),backup_file=str(BACKUP),backup_manifest=str(BACKUP.with_name('backup-manifest.json')),backup_bytes=83712133374,backup_compressed_sha256='4780f93b768a7f2f279ab7bd3d9b6123648ced65094bda9756bd09d98327ca82',original_disk_sha256='f90ad98ddbdc54aeb3d5856f6e5d6764fcfa76750e113624e40af1ede95886bc',old_migration_audit=str(BASE/'evidence-review/DIRECT_FILE_HASH_AUDIT.json'),execution_authorization='Root must explicitly notify native/GPU have exited before --execute. Preparation does not authorize execution.',no_locks_acquired=True,no_GPU_query=True)
    out.write_text(json.dumps(plan,ensure_ascii=False,indent=2));print(json.dumps(dict(prepared=True,active17=len(active),engines8=len(engines),frozen_payloads=len(freezes),certificate_pins=len(certs),locks_acquired=False,GPU_queried=False),indent=2))

if __name__=='__main__':main()
