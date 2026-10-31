"""TRAIN-only difficulty calibration over immutable actual-native runtime."""
import hashlib,importlib.util,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;EXP=HERE.parent
PARENT=EXP/'strategic-learned-recruitment-run-v2'
spec=importlib.util.spec_from_file_location('_frozen_prior_zero_calibration_support',PARENT/'pipeline_common.py')
parent=importlib.util.module_from_spec(spec);spec.loader.exec_module(parent)
BASE=parent.BASE;LAB=parent.LAB;NATIVE=parent.NATIVE;MARKER=parent.MARKER;AUDITOR=HERE
DEFAULT_CAPSULE=parent.DEFAULT_CAPSULE;DEFAULT_INITIAL=parent.DEFAULT_INITIAL;INITIAL_SHA=parent.INITIAL_SHA
EPOCH='strategic-active-opponent-TRAIN-difficulty-calibration-v1'
MAP_MANIFEST_SHA='88eae3414ec9d7d7dae9bd8390eb4bf3a6ae5dd59fcb87e807d7d45a51702327'
sha=parent.sha;validate_capsule=parent.validate_capsule;capsule_inputs=parent.capsule_inputs;clean_environment=parent.clean_environment;require_qualification=parent.require_qualification
def audit_metadata():
    return dict(parent.audit_metadata(),pipeline_epoch=EPOCH,TRAIN_only=True,curriculum_calibration_only=True)
def map_manifest():
    if sha(HERE/'MAP_MANIFEST.json')!=MAP_MANIFEST_SHA:raise ValueError('Registered local TRAIN variant manifest changed')
    manifest=json.loads((HERE/'MAP_MANIFEST.json').read_text())
    if manifest['schema']!='active-opponent-hero-count-TRAIN-mapset-v1' or manifest.get('passed') is not True:raise ValueError('Strict map derivation required')
    if len(manifest['variants'])!=12:raise ValueError('Exactly 12 registered TRAIN map/role/multiplier variants required')
    for source in manifest['sources'].values():
        if sha(source['path'])!=source['sha256']:raise ValueError('Original TRAIN map changed')
    for entry in manifest['variants']:
        if sha(entry['path'])!=entry['sha256']:raise ValueError('Derived local TRAIN map changed')
    return manifest
def variant(map_name,player):
    found=[entry for entry in map_manifest()['variants'] if entry['map']==map_name]
    if len(found)!=1 or found[0]['owned_player']!=player:raise ValueError('Map variant must boost exactly the selected actual owned role')
    return found[0]
def source_inputs():
    freeze=PARENT/'SOURCE_FREEZE.json'
    if sha(freeze)!='6c882b314cd69b526644e4730691f4b3e7979780ff3b6f6efce96abb68cbe827':raise ValueError('Frozen prior-zero source identity changed')
    protected=json.loads(freeze.read_text())['files']
    if not all(sha(EXP/path.replace('\\','/'))==h for path,h in protected.items()):raise ValueError('Protected prior-zero policy/run source changed')
    manifest=map_manifest();paths=set(parent.source_inputs());paths.add(freeze)
    paths.update(HERE.glob('*.py'));paths.update([HERE/'PLAN.md',HERE/'MAP_MANIFEST.json',HERE/'COLLECTOR_DERIVATION.json'])
    paths.update(Path(entry['path']) for entry in manifest['variants']);paths.update(Path(entry['path']) for entry in manifest['sources'].values())
    return sorted(paths,key=str)
def validate_native_epoch(native,plan,execution):
    for obj in (native,plan,execution):
        if not all(obj.get(k)==v for k,v in audit_metadata().items()):raise ValueError('Calibration-only native epoch differs')
    if not all(native.get(k) is True for k in ('whole_game_valid','native_game_completed','transport_drained','full_state_recruitment_verified','free_transfer_verified')):raise ValueError('Complete actual-native game proof required')
def validate_cells(*_):raise ValueError('Difficulty calibration is not PPO admission or a training curriculum')
