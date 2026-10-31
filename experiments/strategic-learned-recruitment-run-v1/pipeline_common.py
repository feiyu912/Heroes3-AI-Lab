"""Qualified schema6 recruitment run. Source and runtime closure are explicit."""
import hashlib,importlib.util,json,os,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;EXP=HERE.parent
BASE=EXP/'strategic-learned-recruitment-policy-v2';sys.path.insert(0,str(BASE))
from qualification import require_qualification,CONTRACT_SHA
LAB=Path('/root/heroes3-ai-lab');AUDITOR=HERE
NATIVE=EXP/'strategic-learned-recruitment-native-v3'
EPOCH='strategic-learned-recruitment-training-v1';AUDIT_EPOCH='director-learned-recruitment-v1'
DEFAULT_CAPSULE=LAB/'evaluations/strategic-learned-recruitment-capsule-02'
DEFAULT_INITIAL=BASE/'initialization-01/recruitment-initialization.pt';INITIAL_SHA='b9ede0d158d113eff42d58cb8a844277b42e8a0820122d985299dfcf9cdb7b79'
MAPS=('takeover-v2-train-01-mines','takeover-v2-train-02-development')
EXPECTED_CELLS={(m,p,o) for m in MAPS for p in (0,1) for o in ('EmptyAI','Nullkiller2')}
spec=importlib.util.spec_from_file_location('_recruit_registry',EXP/'strategic-director-terminal-drain-v4/director_registry_v1.py')
registry=importlib.util.module_from_spec(spec);spec.loader.exec_module(registry);MARKER=registry.MARKER
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def audit_metadata():
    return dict(terminal_ack_scope='director',termination_registry_semantics='atomic-termination-closed-registry-v3',
        audit_epoch=AUDIT_EPOCH,pipeline_epoch=EPOCH,action_schema='strategy-candidates-v6',
        economy_epoch='learned-economy-build-recruit-v1',contract_sha256=CONTRACT_SHA,
        native_flow_epoch='learned-economy-build-recruit-v1',flow_contract_sha256=CONTRACT_SHA,threat_replan='off')
def validate_capsule(capsule):
    b=require_qualification()
    if Path(capsule).resolve()!=Path(b['capsule_directory']).resolve():raise ValueError('Unqualified capsule path')
    return json.loads((Path(capsule)/'EXECUTION.json').read_text())
def capsule_inputs(capsule):
    att=validate_capsule(capsule);c=Path(capsule)
    return [c/'EXECUTION.json',c/'build-source-manifest.json']+[c/p for p in sorted(att['candidate_artifacts'])]
def source_inputs():
    b=require_qualification();native=Path(b['native_directory'])
    folders=[HERE,BASE,EXP/'strategic-policy-v3',EXP/'strategic-typed-training-v1',EXP/'strategic-learned-economy-policy-v1',EXP/'strategic-learned-build-exploration-v1',EXP/'strategic-director-terminal-drain-v4',EXP/'multihero-mechanism-probe-v1/build-driver-frozen-03']
    paths={p.resolve() for folder in folders for p in folder.glob('*.py')}
    paths.update([HERE/'QUALIFICATION.json',HERE/'PLAN.md',native/'CONTRACT.md',native/'CANDIDATE_MANIFEST.json',Path(b['catalog_path']),Path(b['mechanism_report']),Path(b['per_game_auditor']),BASE/'creature_vocabulary.json',EXP/'strategic-learned-recruitment-native-v2/CONTRACT.md'])
    paths.update(Path(p) for p in b['evidence_sha256']);paths.update(Path(p) for p in b['auditor_dependencies'])
    paths.update(native/'candidate'/p for p in json.loads((native/'CANDIDATE_MANIFEST.json').read_text())['files'])
    return sorted(paths,key=str)
def validate_native_epoch(native,plan,execution):
    b=require_qualification()
    for obj in (native,plan,execution):
        if not all(obj.get(k)==v for k,v in audit_metadata().items()):raise ValueError('Schema6 epoch metadata differs')
    for key in ('whole_game_valid','native_game_completed','transport_drained','full_state_recruitment_verified','free_transfer_verified','compiled_native_epoch_proven'):
        if native.get(key) is not True:raise ValueError('Native audit missing '+key)
    if native.get('candidate_manifest_sha256')!=b['native_manifest_sha256']:raise ValueError('Per-game native manifest differs')
    if native.get('catalog_sha256')!=b['catalog_sha256']:raise ValueError('Per-game runtime catalog differs')
    if native.get('contract_errors'):raise ValueError('Native contract errors')
def validate_cells(episodes):
    if len(episodes)!=8 or len({e['episode_id'] for e in episodes})!=8:raise ValueError('Complete eight-cell TRAIN batch required')
    if {(e['job']['map'],e['job']['owned_player'],e['job']['opponent']) for e in episodes}!=EXPECTED_CELLS:raise ValueError('Wrong TRAIN map/role/opponent cells')
    if len({e['checkpoint_sha256'] for e in episodes})!=1 or len({e['job']['logical_update'] for e in episodes})!=1:raise ValueError('Mixed parent/update')
def clean_environment():
    if os.environ.get('LAB_ADV_THREAT_REPLAN') not in (None,'','off') or os.environ.get('LAB_ADV_MODE') or os.environ.get('LAB_ADV_LEARNED_ECONOMY') not in (None,'','build_recruit_v1'):raise ValueError('Foreign native environment overrides')
