"""External actual-native eligibility. Missing pins always stop execution."""
import functools,hashlib,importlib.util,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
RUN=HERE.parent/'strategic-learned-recruitment-run-v1'
BINDING=RUN/'QUALIFICATION.json'
CONTRACT_SHA='1f3a9d3c0777e31787df5e8cd2a2af1614d326a04f9b0f85ac0e83c3e42d15a3'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def need(ok,message):
    if not ok:raise ValueError(message)
def require_qualification():
    need(BINDING.is_file(),'Actual recruitment capsule/catalog qualification is absent; execution closed')
    b=json.loads(BINDING.read_text())
    required={'schema','catalog_path','catalog_sha256','native_directory','native_manifest_sha256','capsule_directory',
        'capsule_manifest_sha256','native_artifacts','mechanism_report','mechanism_report_sha256','per_game_auditor','per_game_auditor_sha256','evidence_sha256','auditor_dependencies'}
    need(set(b)==required and b['schema']=='recruitment-native-qualification-binding-v1','Exact qualification binding required')
    native=Path(b['native_directory']);capsule=Path(b['capsule_directory'])
    need(sha(native/'CONTRACT.md')==CONTRACT_SHA,'Reviewed schema6 contract changed')
    need(sha(native/'CANDIDATE_MANIFEST.json')==b['native_manifest_sha256'],'Native candidate manifest changed')
    need(sha(capsule/'build-source-manifest.json')==b['capsule_manifest_sha256'],'Capsule manifest changed')
    need(set(b['native_artifacts'])=={'vcmiclient','vcmiserver','libvcmi.so'},'Three actual native binaries required')
    need(all(sha(capsule/'bin'/name)==digest for name,digest in b['native_artifacts'].items()),'Actual binary SHA differs')
    att=json.loads((capsule/'EXECUTION.json').read_text())
    need(att['passed'] and att['accepted_sources_restored'] and att['accepted_binaries_restored'] and not att['rebuild_required'],'Build/restoration attestation failed')
    need(att['candidate_manifest_sha256']==b['native_manifest_sha256'],'Build candidate differs')
    need(all(sha(capsule/p)==h for p,h in att['candidate_artifacts'].items()),'Capsule artifacts changed')
    manifest=json.loads((native/'CANDIDATE_MANIFEST.json').read_text());source=json.loads((capsule/'build-source-manifest.json').read_text())
    for relative,entry in manifest['files'].items():
        need(sha(native/'candidate'/relative)==sha(capsule/'source-snapshot'/relative)==source[relative]['sha256']==entry['candidate_sha256'],'Candidate source closure differs')
    need(sha(b['mechanism_report'])==b['mechanism_report_sha256'],'Mechanism report changed')
    report=json.loads(Path(b['mechanism_report']).read_text())
    for field in ('passed','mechanism_only','full_state_recruitment_verified','free_transfer_verified','same_turn_build_recruit_move_recruit_return_end_verified','catalog_runtime_bound'):
        need(report.get(field) is True,'Actual mechanism report missing '+field)
    need(report.get('training_samples')==0 and report.get('optimizer_steps')==0,'Mechanism evidence cannot be training')
    for key in ('catalog_sha256','native_manifest_sha256','capsule_manifest_sha256','native_artifacts'):
        need(report.get(key)==b[key],'Mechanism binding mismatch: '+key)
    need(isinstance(b['evidence_sha256'],dict) and b['evidence_sha256'],'Raw actual mechanism evidence required')
    need(report.get('evidence_sha256')==b['evidence_sha256'],'Raw evidence closure mismatch')
    need(all(sha(p)==h for p,h in b['evidence_sha256'].items()),'Mechanism raw evidence changed')
    need(sha(b['catalog_path'])==b['catalog_sha256'],'Actual runtime catalog changed')
    need(sha(b['per_game_auditor'])==b['per_game_auditor_sha256'],'Per-game auditor changed')
    need(b['auditor_dependencies'] and all(sha(p)==h for p,h in b['auditor_dependencies'].items()),'Auditor dependencies changed')
    return b
@functools.lru_cache(maxsize=1)
def qualified_catalog():
    b=require_qualification()
    spec=importlib.util.spec_from_file_location('_qualified_recruit_catalog_encoder',HERE/'encoder.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    catalog=module.load_catalog(b['catalog_path'],b['catalog_sha256'])
    need(len(catalog['ids'])>0,'Registered nonempty creature vocabulary required')
    return catalog
