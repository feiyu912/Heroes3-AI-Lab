"""Only newline-committed records are visible while an append-only writer is live."""
import json
from pathlib import Path
def parse(raw,*,final=False):
    if final and raw and not raw.endswith(b'\n'):raise ValueError('Final JSONL has an uncommitted tail')
    records=raw.split(b'\n')[:-1]
    return [json.loads(line) for line in records if line.strip()]
def read(path,*,final=False):
    path=Path(path)
    return parse(path.read_bytes(),final=final) if path.exists() else []
