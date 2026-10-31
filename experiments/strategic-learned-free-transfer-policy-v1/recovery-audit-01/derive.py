"""Reuse the actual CUDA boundary auditor with only its sibling run path changed."""
from pathlib import Path

here = Path(__file__).resolve().parent
source = here.parent.parent / 'strategic-learned-build-exploration-policy-v1/recovery-audit-01/audit_checkpoint_cuda.py'
old = "RUN=POLICY.parent/'strategic-learned-build-exploration-run-v1'"
new = "RUN=POLICY.parent/'strategic-learned-free-transfer-run-v1'"
text = source.read_text()
assert text.count(old) == 1
target = here / 'audit_checkpoint_cuda.py'
assert not target.exists()
target.write_text(text.replace(old, new))
