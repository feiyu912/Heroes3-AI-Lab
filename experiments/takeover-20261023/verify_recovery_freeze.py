"""Read-only verification of a recovery FREEZE manifest."""
import hashlib
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
d = json.loads(path.read_text())
assert d['schema'] == 'terminal-drain-prefix-credit-v1'
missing = []
mismatch = []
for p, expected in d['input_sha256'].items():
    q = Path(p)
    if not q.exists():
        missing.append(p)
        continue
    h = hashlib.sha256()
    with q.open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    if h.hexdigest() != expected:
        mismatch.append([p, expected, h.hexdigest()])
print(json.dumps({
    'freeze': str(path),
    'entries': len(d['input_sha256']),
    'missing': missing,
    'mismatch': mismatch,
    'has_recover_py': any(p.endswith('/recover.py') for p in d['input_sha256']),
    'has_recovery_audit_py': any(p.endswith('/recovery_audit.py') for p in d['input_sha256']),
    'has_control64': any(p.endswith('control-phase-1/update-64.pt') for p in d['input_sha256']),
    'has_candidate62': any(p.endswith('candidate-micro/update-62.pt') for p in d['input_sha256']),
}, indent=2))
assert not missing and not mismatch
