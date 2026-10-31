"""Path/source binding for the qualified native epoch; no policy, audit or PPO changes."""
import hashlib,importlib.util,json,os
from pathlib import Path
HERE=Path(__file__).resolve().parent
EXPERIMENTS=HERE.parent.parent
BASE=EXPERIMENTS/'strategic-typed-training-v1'
POLICY=EXPERIMENTS/'strategic-policy-v3'
NATIVE=EXPERIMENTS/'strategic-typed-native-v1'
AUDITOR=EXPERIMENTS/'strategic-director-terminal-drain-v4'
SUPPORT=EXPERIMENTS/'multihero-mechanism-probe-v1/build-driver-frozen-03'
LAB=Path('/root/heroes3-ai-lab')
DEFAULT_CAPSULE=LAB/'evaluations/typed-director-terminal-drain-capsule-03'
DEFAULT_INITIAL=HERE.parent/'temperature-initialization-01/temperature-2-initialization.pt'
INITIAL_SHA='d5908330038444107ed9ba00585fb068e453a5d1636856ba994d9aa3eb68df72'
EPOCH='strategic-learning-mainline-capsule03-temperature2-20261020-v1'
spec=importlib.util.spec_from_file_location('_mainline_terminal_registry',AUDITOR/'director_registry_v1.py')
registry=importlib.util.module_from_spec(spec);spec.loader.exec_module(registry)
AUDIT_EPOCH=registry.AUDIT_EPOCH
MARKER=registry.MARKER
TERMINATION='atomic-termination-closed-registry-v3'
MAPS=('takeover-v2-train-01-mines','takeover-v2-train-02-development')
EXPECTED_CELLS={(m,p,o) for m in MAPS for o in ('EmptyAI','Nullkiller2') for p in (0,1)}
AUDITOR_SOURCES={'audit_game_v6.py':AUDITOR/'audit_game_v6.py','raw_events_v4.py':NATIVE/'raw_events_v4.py','director_registry_v1.py':AUDITOR/'director_registry_v1.py'}
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def source_inputs():
    # Freeze the complete Python helpers in the relevant packages, including
    # unchanged sampler/model/encoder/PPO/auditor dependencies; no new auditor.
    paths={p.resolve() for folder in (BASE,POLICY,NATIVE,AUDITOR,SUPPORT) for p in folder.glob('*.py')}
    paths.update((HERE/name).resolve() for name in ['pipeline_common.py','collect_episode_v5.py','admit_episode_v5.py'])
    paths.add(AUDITOR/'CANDIDATE_MANIFEST.json')
    manifest=json.loads((AUDITOR/'CANDIDATE_MANIFEST.json').read_text())
    assert len(manifest['files'])==9
    paths.update((AUDITOR.parent/'strategic-director-terminal-drain-v3/candidate'/r).resolve() for r in manifest['files'])
    return sorted(paths,key=str)
def validate_capsule(capsule):
    capsule=Path(capsule).resolve();att=json.loads((capsule/'EXECUTION.json').read_text())
    source=json.loads((capsule/'build-source-manifest.json').read_text())
    manifest=json.loads((AUDITOR/'CANDIDATE_MANIFEST.json').read_text())
    assert manifest['schema']=='director-native-terminal-drain-closed-v3' and len(manifest['files'])==9
    assert att['passed'] and att['accepted_binaries_restored'] and not att['rebuild_required']
    assert all(sha(capsule/r)==h for r,h in att['candidate_artifacts'].items())
    for relative,entry in manifest['files'].items():
        expected=entry['candidate_sha256']
        assert sha(capsule/'source-snapshot'/relative)==source[relative]['sha256']==att['candidate_artifacts']['source-snapshot/'+relative]==expected
    return att
def capsule_inputs(capsule):
    capsule=Path(capsule).resolve();att=validate_capsule(capsule)
    return [capsule/'EXECUTION.json',capsule/'build-source-manifest.json']+[capsule/r for r in sorted(att['candidate_artifacts'])]
def audit_metadata():return dict(terminal_ack_scope='director',termination_registry_semantics=TERMINATION,audit_epoch=AUDIT_EPOCH,pipeline_epoch=EPOCH)
def validate_native_epoch(native,plan,execution):
    for obj in (native,plan,execution):
        assert obj['terminal_ack_scope']=='director' and obj['termination_registry_semantics']==TERMINATION and obj['audit_epoch']==AUDIT_EPOCH
    assert native.get('input_audit_epoch')==AUDIT_EPOCH and not native.get('read_only_legacy_reaudit',True)
    assert native.get('compiled_native_epoch_proven') is True and native.get('event_contract_valid') is True
    assert native.get('whole_game_valid') is True and native.get('native_game_completed') is True and native.get('transport_drained') is True
    assert native['candidate_manifest_sha256']==sha(AUDITOR/'CANDIDATE_MANIFEST.json')
    assert set(native['auditor_sha256'])==set(AUDITOR_SOURCES)
    assert all(sha(AUDITOR_SOURCES[name])==digest for name,digest in native['auditor_sha256'].items())
def validate_cells(episodes):
    assert len(episodes)==8 and len({e['episode_id'] for e in episodes})==8,'Exactly eight distinct complete episodes required'
    cells={(e['job']['map'],e['job']['owned_player'],e['job']['opponent']) for e in episodes}
    assert cells==EXPECTED_CELLS,'Exactly both Training maps x both roles x both opponents required'
    assert len({e['checkpoint_sha256'] for e in episodes})==1,'Mixed parent policies forbidden'
    assert len({e['job']['logical_update'] for e in episodes})==1,'Mixed logical updates forbidden'
def clean_environment():
    assert os.environ.get('LAB_ADV_THREAT_REPLAN') in (None,'','off'),'Training epoch has no optional threat replan'
    assert not os.environ.get('LAB_ADV_MODE'),'Transport/recovery mode must not enter policy training'
