"""Explicit learned-build epoch. Historical schema4 gates remain unchanged."""
import hashlib, importlib.util, json, os
from pathlib import Path
HERE=Path(__file__).resolve().parent
EXPERIMENTS=HERE.parent
BASE=EXPERIMENTS/'strategic-learned-free-transfer-policy-v1'
AUDITOR=HERE
NATIVE=EXPERIMENTS/'strategic-learned-economy-native-v2'
CONTRACT=EXPERIMENTS/'strategic-learned-economy-native-v1/CONTRACT.md'
FLOW_CONTRACT=NATIVE/'FLOW_CONTRACT.json'
BINDINGS_PATH=HERE/'DRAFT_BINDINGS.json'
BINDINGS=json.loads(BINDINGS_PATH.read_text())
OLD=EXPERIMENTS/'strategic-learning-mainline-20261020/native-pipeline'
SUPPORT=EXPERIMENTS/'multihero-mechanism-probe-v1/build-driver-frozen-03'
LAB=Path('/root/heroes3-ai-lab')
EPOCH='strategic-learned-free-transfer-training-v1'
AUDIT_EPOCH='director-learned-economy-free-stock-prewindow-v2'
TERMINATION='atomic-termination-closed-registry-v3'
DEFAULT_CAPSULE=Path(BINDINGS.get('qualified_capsule_directory') or LAB/'evaluations/UNQUALIFIED-free-stock-capsule')
DEFAULT_INITIAL=BASE/'initialization-01/free-transfer-initialization.pt'
INITIAL_SHA=BINDINGS.get('initialization_sha256')
MAPS=('takeover-v2-train-01-mines','takeover-v2-train-02-development')
EXPECTED_CELLS={(m,p,o) for m in MAPS for p in (0,1) for o in ('EmptyAI','Nullkiller2')}
spec=importlib.util.spec_from_file_location('_learned_build_registry',EXPERIMENTS/'strategic-director-terminal-drain-v4/director_registry_v1.py')
registry=importlib.util.module_from_spec(spec);spec.loader.exec_module(registry)
MARKER=registry.MARKER
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def require_qualification():
    b=json.loads(BINDINGS_PATH.read_text())
    if b.get('native_run_allowed') is not True:raise ValueError('Native free-stock capsule/flow audit is not qualified; draft execution is disabled')
    required=('native_candidate_directory','native_contract_sha256','flow_contract_sha256','native_manifest_sha256','qualified_capsule_directory',
        'qualified_capsule_manifest_sha256','qualified_native_binary_sha256','native_exact_payload_paths_and_sha256',
        'prewindow_qualification_report','prewindow_qualification_report_sha256','flow_auditor_sha256')
    if any(not b.get(k) for k in required):raise ValueError('Missing exact free-stock qualification pins')
    if Path(b['native_candidate_directory']).resolve()!=NATIVE.resolve():raise ValueError('Wrong native candidate directory')
    if b.get('native_manifest_schema')!='director-learned-economy-free-stock-prewindow-v2':raise ValueError('Wrong native schema')
    if b.get('native_flow_epoch')!='learned-economy-free-existing-stock-prewindow-v2' or b.get('native_audit_epoch')!=AUDIT_EPOCH:raise ValueError('Wrong free-stock flow/audit epoch')
    if sha(CONTRACT)!=b['native_contract_sha256'] or sha(NATIVE/'CANDIDATE_MANIFEST.json')!=b['native_manifest_sha256']:raise ValueError('Native contract/manifest changed')
    if sha(FLOW_CONTRACT)!=b['flow_contract_sha256']:raise ValueError('Native flow contract changed')
    proof=Path(b['prewindow_qualification_report'])
    if sha(proof)!=b['prewindow_qualification_report_sha256']:raise ValueError('Qualification proof changed')
    result=json.loads(proof.read_text())
    if result.get('passed') is not True or result.get('candidate_manifest_sha256')!=b['native_manifest_sha256']:raise ValueError('Qualification lacks exact compiled candidate binding')
    if result.get('flow_contract_sha256')!=b['flow_contract_sha256']:raise ValueError('Qualification flow contract differs')
    if result.get('capsule_manifest_sha256')!=b['qualified_capsule_manifest_sha256'] or result.get('native_artifacts')!=b['qualified_native_binary_sha256']:raise ValueError('Qualification compiled capsule differs')
    if result.get('multistack_before_first_policy_proven') is not True or result.get('rescue_hire_then_free_transfer_before_first_policy_proven') is not True:raise ValueError('Qualification lacks actual multistack/rescue coverage')
    if result.get('mechanism_only') is not True or result.get('training_samples')!=0 or result.get('optimizer_steps')!=0:raise ValueError('Qualification must remain mechanism only')
    if b.get('flow_auditor_dependencies')!=result.get('flow_auditor_dependencies'):raise ValueError('Qualification helper source closure differs')
    if result.get('capsule_manifest_sha256')!=b['qualified_capsule_manifest_sha256'] or result.get('native_artifacts')!=b['qualified_native_binary_sha256']:raise ValueError('Qualification actual runtime differs')
    if sha(HERE/'free_transfer_evidence.py')!=b['flow_auditor_sha256']:raise ValueError('Flow auditor changed')
    spec=importlib.util.spec_from_file_location('_free_stock_flow_qualification',HERE/'free_transfer_evidence.py')
    flow=importlib.util.module_from_spec(spec);spec.loader.exec_module(flow)
    if getattr(flow,'QUALIFIED',False) is not True:raise ValueError('Per-game free-stock evidence verifier remains unqualified')
    for path,digest in b.get('flow_auditor_dependencies',{}).items():
        if sha(path)!=digest:raise ValueError('Flow auditor dependency changed: '+path)
    return b
def audit_metadata():
    return dict(terminal_ack_scope='director',termination_registry_semantics=TERMINATION,
        audit_epoch=AUDIT_EPOCH,pipeline_epoch=EPOCH,action_schema='strategy-candidates-v5',
        economy_epoch='learned-economy-build-v1',contract_sha256=sha(CONTRACT),
        native_flow_epoch='learned-economy-free-existing-stock-prewindow-v2',flow_contract_sha256=sha(FLOW_CONTRACT),threat_replan='off')
def source_inputs():
    require_qualification()
    folders=(HERE,BASE,SUPPORT,EXPERIMENTS/'strategic-learned-build-exploration-policy-v1',EXPERIMENTS/'strategic-learned-economy-policy-v1',EXPERIMENTS/'strategic-learned-build-exploration-v1',EXPERIMENTS/'strategic-typed-training-v1',
        EXPERIMENTS/'strategic-policy-v3',EXPERIMENTS/'strategic-typed-native-v1',
        EXPERIMENTS/'strategic-director-terminal-drain-v4')
    paths={p.resolve() for folder in folders for p in folder.glob('*.py')}
    paths.update((CONTRACT,FLOW_CONTRACT,NATIVE/'CANDIDATE_MANIFEST.json',BINDINGS_PATH,HERE/'PLAN.md'))
    manifest=json.loads((NATIVE/'CANDIDATE_MANIFEST.json').read_text())
    b=require_qualification()
    paths.add(Path(b['prewindow_qualification_report']).resolve())
    paths.update(Path(path).resolve() for path in b.get('flow_auditor_dependencies',{}))
    assert manifest['schema']==b['native_manifest_schema']
    assert {k:v['candidate_sha256'] for k,v in manifest['files'].items()}==b['native_exact_payload_paths_and_sha256']
    paths.update(NATIVE/'candidate'/r for r in manifest['files'])
    return sorted(paths,key=str)
def validate_capsule(capsule):
    b=require_qualification()
    capsule=Path(capsule).resolve();att=json.loads((capsule/'EXECUTION.json').read_text())
    assert capsule==Path(b['qualified_capsule_directory']).resolve()
    source=json.loads((capsule/'build-source-manifest.json').read_text())
    manifest=json.loads((NATIVE/'CANDIDATE_MANIFEST.json').read_text())
    assert manifest['schema']==b['native_manifest_schema']
    assert {k:v['candidate_sha256'] for k,v in manifest['files'].items()}==b['native_exact_payload_paths_and_sha256']
    assert manifest['contract_sha256']==sha(CONTRACT)==b['native_contract_sha256']
    assert manifest['flow_contract_sha256']==sha(FLOW_CONTRACT)==b['flow_contract_sha256']
    assert sha(capsule/'build-source-manifest.json')==b['qualified_capsule_manifest_sha256']
    assert {n:sha(capsule/'bin'/n) for n in ('vcmiclient','vcmiserver','libvcmi.so')}==b['qualified_native_binary_sha256']
    assert att['passed'] and att['accepted_binaries_restored'] and not att['rebuild_required']
    assert all(sha(capsule/r)==h for r,h in att['candidate_artifacts'].items())
    for relative,entry in manifest['files'].items():
        expected=entry['candidate_sha256']
        assert sha(capsule/'source-snapshot'/relative)==source[relative]['sha256']==att['candidate_artifacts']['source-snapshot/'+relative]==expected
    return att
def capsule_inputs(capsule):
    capsule=Path(capsule).resolve();att=validate_capsule(capsule)
    return [capsule/'EXECUTION.json',capsule/'build-source-manifest.json']+[capsule/r for r in sorted(att['candidate_artifacts'])]
def validate_native_epoch(native,plan,execution):
    expected=audit_metadata()
    for obj in (native,plan,execution):
        assert all(obj.get(k)==v for k,v in expected.items()),'New economic epoch metadata mismatch'
    assert native['compiled_native_epoch_proven'] and native['event_contract_valid']
    assert native['whole_game_valid'] and native['native_game_completed'] and native['transport_drained']
    assert native['candidate_manifest_sha256']==sha(NATIVE/'CANDIDATE_MANIFEST.json')
    assert set(native['auditor_sha256'])==set(AUDITOR_SOURCES)
    assert all(sha(AUDITOR_SOURCES[k])==v for k,v in native['auditor_sha256'].items())
    assert native['build_evidence_verified'] is True
    assert native.get('prewindow_evidence_verified') is True
def validate_cells(episodes):
    assert len(episodes)==8 and len({e['episode_id'] for e in episodes})==8
    assert {(e['job']['map'],e['job']['owned_player'],e['job']['opponent']) for e in episodes}==EXPECTED_CELLS
    assert len({e['checkpoint_sha256'] for e in episodes})==1
    assert len({e['job']['logical_update'] for e in episodes})==1
def clean_environment():
    assert os.environ.get('LAB_ADV_THREAT_REPLAN') in (None,'','off')
    assert not os.environ.get('LAB_ADV_MODE')
    assert os.environ.get('LAB_ADV_LEARNED_ECONOMY') in (None,'','build_v1')
AUDITOR_SOURCES={n:HERE/n for n in ('audit_game_v6.py','audit_contract.py','raw_events_v5.py','build_evidence.py')}
AUDITOR_SOURCES['director_registry_v1.py']=EXPERIMENTS/'strategic-director-terminal-drain-v4/director_registry_v1.py'
AUDITOR_SOURCES['free_transfer_evidence.py']=HERE/'free_transfer_evidence.py'
AUDITOR_SOURCES.update({'flow_dependency:'+p:Path(p) for p in BINDINGS.get('flow_auditor_dependencies',{})})


