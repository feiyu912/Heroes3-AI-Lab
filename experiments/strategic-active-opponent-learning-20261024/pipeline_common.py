"""Qualified schema6 recruitment run. Source and runtime closure are explicit."""
import hashlib,importlib.util,json,os,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;EXP=HERE.parent
BASE=EXP/'strategic-active-opponent-policy-v4';sys.path.insert(0,str(BASE))
from qualification import require_qualification,CONTRACT_SHA
LAB=Path('/root/heroes3-ai-lab');AUDITOR=HERE
NATIVE=EXP/'strategic-learned-recruitment-native-v3'
EPOCH='strategic-active-opponent-paired-learning-v1';AUDIT_EPOCH='director-learned-recruitment-v1'
DEFAULT_CAPSULE=LAB/'evaluations/strategic-learned-recruitment-capsule-02'
DEFAULT_INITIAL=EXP/'strategic-learned-recruitment-policy-v3/initialization-02/recruitment-initialization.pt';INITIAL_SHA='1510149ef1c2c896e3125e6468e9e58234a8bfc9e4278ad239f9d6840e1c62a1'
CONTROL_POLICY=EXP/'strategic-learned-recruitment-policy-v2'
CONTROL_INITIAL=CONTROL_POLICY/'initialization-01/recruitment-initialization.pt'
CONTROL_UPDATED=LAB/'evaluations/strategic-learned-recruitment-train-20261023-01/update-01/update-1.pt'
CONTROL_SHA={'minus4_initial':'b9ede0d158d113eff42d58cb8a844277b42e8a0820122d985299dfcf9cdb7b79','minus4_updated':'85c5fdda76e1d98fcc157f86f08203e7f9db0e1774f5b0f254ad5b20f9b55a9a'}
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
    verify_parent_freeze()
    b=require_qualification();native=Path(b['native_directory'])
    folders=[HERE,BASE,EXP/'strategic-policy-v3',EXP/'strategic-typed-training-v1',EXP/'strategic-learned-economy-policy-v1',EXP/'strategic-learned-build-exploration-v1',EXP/'strategic-director-terminal-drain-v4',EXP/'multihero-mechanism-probe-v1/build-driver-frozen-03']
    paths={p.resolve() for folder in folders for p in folder.glob('*.py')}
    paths.update([HERE/'QUALIFICATION.json',HERE/'PLAN.md',HERE/'DERIVATION.json',native/'CONTRACT.md',native/'CANDIDATE_MANIFEST.json',Path(b['catalog_path']),Path(b['mechanism_report']),Path(b['per_game_auditor']),BASE/'creature_vocabulary.json',EXP/'strategic-learned-recruitment-native-v2/CONTRACT.md'])
    paths.update(Path(p) for p in b['evidence_sha256']);paths.update(Path(p) for p in b['auditor_dependencies'])
    paths.update(native/'candidate'/p for p in json.loads((native/'CANDIDATE_MANIFEST.json').read_text())['files'])
    paths.update(control_policy_inputs())
    paths.update([HERE/'MAP_MANIFEST.json',OLD_RUN/'SOURCE_FREEZE.json'])
    paths.update(Path(e['path']) for e in map_manifest()['variants'])
    paths.update(Path(e['path']) for e in map_manifest()['sources'].values())
    paths.add(DEFAULT_INITIAL.parent/'AUDIT.json')
    paths.update(LAB/('data/vcmi/Maps/adv/'+name+'.vmap') for name in ('takeover-v2-dev-01-river','takeover-v2-dev-02-reserves'))
    return sorted(paths,key=str)
def control_policy_inputs():
    old_run=EXP/'strategic-learned-recruitment-run-v1';freeze=old_run/'SOURCE_FREEZE.json'
    if sha(freeze)!='9919de90735e946dbb543059923287f0c0e712ee0a91a2d09cc5e47195890a22':raise ValueError('Protected old SOURCE_FREEZE identity changed')
    frozen=json.loads(freeze.read_text())['files']
    if not all(sha(EXP/relative.replace('\\','/'))==h for relative,h in frozen.items()):raise ValueError('Protected old policy/run source freeze changed')
    return [freeze]+[EXP/relative.replace('\\','/') for relative in frozen]+[CONTROL_POLICY/'initialization-01/AUDIT.json']
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
    if len({e['job']['arm'] for e in episodes})!=1:raise ValueError('Mixed treatments')
    for e in episodes:
        j=e['job'];entry=training_variant(j['map'],j['owned_player'],j['opponent'],j['arm'])
        index=list((m,o,p) for m in MAPS for o in ('EmptyAI','Nullkiller2') for p in (0,1)).index((j['map'],j['opponent'],j['owned_player']))
        if j['seed']!=2026104400+index or j['logical_update']!=0 or j['multiplier']!=entry['multiplier']:raise ValueError('Unregistered TRAIN job')
    if len(episodes)!=8 or len({e['episode_id'] for e in episodes})!=8:raise ValueError('Complete eight-cell TRAIN batch required')
    if {(e['job']['map'],e['job']['owned_player'],e['job']['opponent']) for e in episodes}!=EXPECTED_CELLS:raise ValueError('Wrong TRAIN map/role/opponent cells')
    if len({e['checkpoint_sha256'] for e in episodes})!=1 or len({e['job']['logical_update'] for e in episodes})!=1:raise ValueError('Mixed parent/update')
def clean_environment():
    if os.environ.get('LAB_ADV_THREAT_REPLAN') not in (None,'','off') or os.environ.get('LAB_ADV_MODE') or os.environ.get('LAB_ADV_LEARNED_ECONOMY') not in (None,'','build_recruit_v1'):raise ValueError('Foreign native environment overrides')

OLD_RUN=EXP/'strategic-learned-recruitment-run-v2'
MAP_MANIFEST_SHA='88eae3414ec9d7d7dae9bd8390eb4bf3a6ae5dd59fcb87e807d7d45a51702327'
def verify_parent_freeze():
    freeze=OLD_RUN/'SOURCE_FREEZE.json'
    if sha(freeze)!='6c882b314cd69b526644e4730691f4b3e7979780ff3b6f6efce96abb68cbe827':raise ValueError('Frozen parent changed')
    if not all(sha(EXP/p.replace('\\','/'))==h for p,h in json.loads(freeze.read_text())['files'].items()):raise ValueError('Protected parent source changed')
def map_manifest():
    if sha(HERE/'MAP_MANIFEST.json')!=MAP_MANIFEST_SHA:raise ValueError('TRAIN map manifest changed')
    result=json.loads((HERE/'MAP_MANIFEST.json').read_text())
    if not result['passed'] or len(result['variants'])!=12:raise ValueError('Unqualified TRAIN variants')
    for e in list(result['sources'].values())+result['variants']:
        if sha(e['path'])!=e['sha256']:raise ValueError('TRAIN map bytes changed')
    return result
def training_variant(map_name,player,opponent,arm):
    if arm not in ('control','curriculum') or opponent not in ('EmptyAI','Nullkiller2'):raise ValueError('Unregistered treatment')
    multiplier=4 if arm=='curriculum' and opponent=='Nullkiller2' else 1
    found=[e for e in map_manifest()['variants'] if (e['source_map'],e['owned_player'],e['multiplier'])==(map_name,player,multiplier)]
    if len(found)!=1:raise ValueError('Wrong TRAIN map/role/treatment')
    return found[0]
