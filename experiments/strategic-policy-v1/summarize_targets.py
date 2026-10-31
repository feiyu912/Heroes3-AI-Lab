"""Summarize diagnostic target filters, preserving source hashes."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

run = Path(sys.argv[1])
path = run / 'strategy-trace.jsonl.targets.jsonl'
rows = [json.loads(s) for s in path.read_text().splitlines() if s.strip()]
result = dict(source=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
              counts={str(k): v for k, v in Counter((r['kind'], r['status']) for r in rows).items()},
              first_by_status={}, last_rows=rows[-10:])
for r in rows:
    result['first_by_status'].setdefault(str((r['kind'], r['status'])), r)
print(json.dumps(result, indent=2))
if len(sys.argv) > 2:
    Path(sys.argv[2]).write_text(json.dumps(result, indent=2))
