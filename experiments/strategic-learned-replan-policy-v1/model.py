"""SHA-bound frozen scalar-offset architecture; no mutation of earlier sources."""
import hashlib,importlib.util
from pathlib import Path
_path=Path(__file__).resolve().parent.parent/'strategic-learned-build-exploration-v1/model.py'
_expected='893c045f9787a1afbe1fe32de6205f947da4e045220969dcd68b0d664e3e6700'
if hashlib.sha256(_path.read_bytes()).hexdigest()!=_expected:raise RuntimeError('Frozen exploration architecture changed')
_spec=importlib.util.spec_from_file_location('_exploration_train_architecture',_path)
_module=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(_module)
for _name in ('encoder','STATE_DIM','CANDIDATE_DIM','ENCODER_VERSION','ARCHITECTURE_VERSION','EPOCH','PriorCandidateActorCritic'):
    globals()[_name]=getattr(_module,_name)


