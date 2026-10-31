"""SHA-bound per-game verifier qualified by the separate actual mechanism fixture."""
import hashlib,importlib.util
from pathlib import Path
HELPER=Path(__file__).resolve().parent.parent/'strategic-learned-economy-native-v2/qualification/flow_evidence.py'
HELPER_SHA256='0d263839dadd6d117d98acb305993e6b2dc167c4e66b0c088350375d97256e60'
QUALIFIED=True
def verify(raw,proposals,folder=None):
    assert hashlib.sha256(HELPER.read_bytes()).hexdigest()==HELPER_SHA256,'Qualified flow helper changed'
    spec=importlib.util.spec_from_file_location('_qualified_free_stock_evidence',HELPER)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    # A real game may present no eligible prewindow stock. Global fixture coverage
    # is required separately; every observed transfer here is still strictly checked.
    return module.verify(raw,proposals,folder=folder)
