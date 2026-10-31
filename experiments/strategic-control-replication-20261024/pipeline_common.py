"""Fixed active-opponent DEV follow-up, bound to the immutable completed learning epoch."""
import importlib.util,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;PARENT=HERE.parent/'strategic-active-opponent-learning-20261024'
spec=importlib.util.spec_from_file_location('_frozen_learning_support',PARENT/'pipeline_common.py')
parent=importlib.util.module_from_spec(spec);spec.loader.exec_module(parent)
for key in ('BASE','LAB','NATIVE','MARKER','DEFAULT_CAPSULE','DEFAULT_INITIAL','INITIAL_SHA','CONTROL_POLICY','CONTROL_SHA','require_qualification','sha','capsule_inputs','validate_capsule','clean_environment','training_variant'):
    globals()[key]=getattr(parent,key)
AUDITOR=HERE;EPOCH='strategic-control-replication-DEV-v1'
def audit_metadata():return dict(parent.audit_metadata(),pipeline_epoch=EPOCH,DEV_only=True,replication_only=True)
def source_inputs():
    freeze=PARENT/'SOURCE_FREEZE.json'
    if sha(freeze)!='c19ac372d22b3156172f02a65f8ad1ef4dc635a15737775eb8cf98c3b31467f7':raise ValueError('Frozen paired study changed')
    if not all(sha(path)==h for path,h in json.loads(freeze.read_text())['files'].items()):raise ValueError('Frozen paired source changed')
    return sorted(set(parent.source_inputs()+[freeze,HERE/'PLAN.md',HERE/'COLLECTOR_DERIVATION.json',CONTROL_CHECKPOINT]+list(HERE.glob('*.py'))),key=str)
def validate_native_epoch(native,plan,execution):
    for obj in (native,plan,execution):
        if not all(obj.get(k)==v for k,v in audit_metadata().items()):raise ValueError('Diagnostic-only epoch required')
    if not native['whole_game_valid'] or not native['native_game_completed'] or not native['transport_drained']:raise ValueError('Invalid diagnostic game')
def validate_cells(*args):raise ValueError('Diagnostic observations cannot become new PPO admissions')

CONTROL_CHECKPOINT=LAB/'evaluations/strategic-active-learning-native-01/control/update-01/update-1.pt'
CONTROL_CHECKPOINT_SHA='b52ac74ad3b0ba6860e57be0a6b2deed9d8c88f14e140b59bd2c61e8b1f739fc'
