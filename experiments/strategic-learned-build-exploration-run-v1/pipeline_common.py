"""Explicit learned-build epoch. Historical schema4 gates remain unchanged."""
import hashlib, importlib.util, json, os
from pathlib import Path
HERE=Path(__file__).resolve().parent
EXPERIMENTS=HERE.parent
BASE=EXPERIMENTS/'strategic-learned-build-exploration-policy-v1'
AUDITOR=HERE
NATIVE=EXPERIMENTS/'strategic-learned-economy-native-v1'
OLD=EXPERIMENTS/'strategic-learning-mainline-20261020/native-pipeline'
SUPPORT=EXPERIMENTS/'multihero-mechanism-probe-v1/build-driver-frozen-03'
LAB=Path('/root/heroes3-ai-lab')
EPOCH='strategic-learned-build-exploration-training-v1'
AUDIT_EPOCH='director-learned-economy-build-v1'
TERMINATION='atomic-termination-closed-registry-v3'
DEFAULT_CAPSULE=LAB/'evaluations/strategic-learned-economy-build-capsule-01'
DEFAULT_INITIAL=EXPERIMENTS/'strategic-learned-build-exploration-v1/calibration-01/build-offset-initialization.pt'
INITIAL_SHA='40eccc511fbc61b84b86e75b5aec102781835f2574db809f9a698f9a81db6d97'
MAPS=('takeover-v2-train-01-mines','takeover-v2-train-02-development')
EXPECTED_CELLS={(m,p,o) for m in MAPS for p in (0,1) for o in ('EmptyAI','Nullkiller2')}
spec=importlib.util.spec_from_file_location('_learned_build_registry',EXPERIMENTS/'strategic-director-terminal-drain-v4/director_registry_v1.py')
registry=importlib.util.module_from_spec(spec);spec.loader.exec_module(registry)
MARKER=registry.MARKER
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def audit_metadata():
    return dict(terminal_ack_scope='director',termination_registry_semantics=TERMINATION,
        audit_epoch=AUDIT_EPOCH,pipeline_epoch=EPOCH,action_schema='strategy-candidates-v5',
        economy_epoch='learned-economy-build-v1',contract_sha256=sha(NATIVE/'CONTRACT.md'))
def source_inputs():
    folders=(HERE,BASE,SUPPORT,EXPERIMENTS/'strategic-learned-economy-policy-v1',EXPERIMENTS/'strategic-learned-build-exploration-v1',EXPERIMENTS/'strategic-typed-training-v1',
        EXPERIMENTS/'strategic-policy-v3',EXPERIMENTS/'strategic-typed-native-v1',
        EXPERIMENTS/'strategic-director-terminal-drain-v4')
    paths={p.resolve() for folder in folders for p in folder.glob('*.py')}
    paths.update((NATIVE/'CONTRACT.md',NATIVE/'CANDIDATE_MANIFEST.json'))
    manifest=json.loads((NATIVE/'CANDIDATE_MANIFEST.json').read_text())
    assert manifest['schema']=='director-learned-economy-build-v1' and len(manifest['files'])==9
    paths.update(NATIVE/'candidate'/r for r in manifest['files'])
    return sorted(paths,key=str)
def validate_capsule(capsule):
    capsule=Path(capsule).resolve();att=json.loads((capsule/'EXECUTION.json').read_text())
    source=json.loads((capsule/'build-source-manifest.json').read_text())
    manifest=json.loads((NATIVE/'CANDIDATE_MANIFEST.json').read_text())
    assert manifest['schema']=='director-learned-economy-build-v1' and len(manifest['files'])==9
    assert manifest['contract_sha256']==sha(NATIVE/'CONTRACT.md')
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
