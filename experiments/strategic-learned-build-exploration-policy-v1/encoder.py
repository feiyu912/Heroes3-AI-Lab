"""Frozen strict schema5 encoder; features unchanged by output-offset intervention."""
import hashlib,importlib.util
from pathlib import Path
_path=Path(__file__).resolve().parent.parent/'strategic-learned-economy-policy-v1/encoder.py'
if hashlib.sha256(_path.read_bytes()).hexdigest()!='77210fd938d0e114e64f6d302f7749dc2a28e76c99e30d1a2488bd7afd02a259':raise RuntimeError('Frozen schema5 encoder changed')
_spec=importlib.util.spec_from_file_location('_exploration_train_encoder',_path)
_module=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(_module)
for _name in dir(_module):
    if not _name.startswith('__'):globals()[_name]=getattr(_module,_name)
