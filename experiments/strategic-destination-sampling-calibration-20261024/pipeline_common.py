"""Only TRAIN diagnostic, bound to the immutable completed learning epoch."""
import importlib.util,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;PARENT=HERE.parent/'strategic-active-opponent-learning-20261024'
spec=importlib.util.spec_from_file_location('_frozen_learning_support',PARENT/'pipeline_common.py')
parent=importlib.util.module_from_spec(spec);spec.loader.exec_module(parent)
for key in ('BASE','LAB','NATIVE','MARKER','DEFAULT_CAPSULE','DEFAULT_INITIAL','INITIAL_SHA','CONTROL_POLICY','CONTROL_SHA','require_qualification','sha','capsule_inputs','validate_capsule','clean_environment','training_variant'):
    globals()[key]=getattr(parent,key)
AUDITOR=HERE;EPOCH='strategic-destination-sampling-TRAIN-calibration-v1'
def audit_metadata():return dict(parent.audit_metadata(),pipeline_epoch=EPOCH,TRAIN_only=True,sampler_diagnostic_only=True,manual_exploration_setting=True,manual_setting_is_learning=False,move_temperature=0.25,new_PPO_admissions=0)
def source_inputs():
    diagnostic_freeze=HERE.parent/'strategic-sampler-calibration-diagnostic-20261024/SOURCE_FREEZE.json'
    if sha(diagnostic_freeze)!='e411f2112db82c4a1f2fa9bc734e6fbdc54c51deb26d4c0691c3bd2b0c36f73e':raise ValueError('Frozen sampling diagnostic changed')
    if not all(sha(p)==h for p,h in json.loads(diagnostic_freeze.read_text())['files'].items()):raise ValueError('Frozen diagnostic sources changed')
    freeze=PARENT/'SOURCE_FREEZE.json'
    if sha(freeze)!='c19ac372d22b3156172f02a65f8ad1ef4dc635a15737775eb8cf98c3b31467f7':raise ValueError('Frozen paired study changed')
    if not all(sha(path)==h for path,h in json.loads(freeze.read_text())['files'].items()):raise ValueError('Frozen paired source changed')
    return sorted(set(parent.source_inputs()+[freeze,diagnostic_freeze,HERE/'PLAN.md',HERE/'DERIVATION.json']+list(HERE.glob('*.py'))),key=str)
def validate_native_epoch(native,plan,execution):
    for obj in (native,plan,execution):
        if not all(obj.get(k)==v for k,v in audit_metadata().items()):raise ValueError('Diagnostic-only epoch required')
    b=require_qualification()
    for key in ('whole_game_valid','native_game_completed','transport_drained','full_state_recruitment_verified','free_transfer_verified','compiled_native_epoch_proven'):
        if native.get(key) is not True:raise ValueError('Native audit missing '+key)
    if native.get('candidate_manifest_sha256')!=b['native_manifest_sha256'] or native.get('catalog_sha256')!=b['catalog_sha256'] or native.get('contract_errors'):
        raise ValueError('Native manifest/catalog/contract binding differs')
def validate_cells(*args):raise ValueError('Diagnostic observations cannot become new PPO admissions')

REGISTERED_JOBS = {
    2026104402: ('takeover-v2-train-01-mines', 0),
    2026104403: ('takeover-v2-train-01-mines', 1),
    2026104406: ('takeover-v2-train-02-development', 0),
    2026104407: ('takeover-v2-train-02-development', 1),
}

def validate_job(args):
    if args.arm != 'curriculum' or args.opponent != 'Nullkiller2' or args.logical_update != 0:
        raise ValueError('Only the four registered initial-model NK x4 calibration cells')
    if REGISTERED_JOBS.get(args.seed) != (args.map, args.player):
        raise ValueError('Unregistered calibration map/role/seed')
    if sha(args.checkpoint.resolve()) != INITIAL_SHA:
        raise ValueError('Fixed initial1510149e required, never an updated model')
