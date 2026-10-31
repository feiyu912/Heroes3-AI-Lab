"""Compact read-only status for the bounded battle continuation."""
from pathlib import Path
import json,argparse
parser=argparse.ArgumentParser();parser.add_argument('--run',type=Path,default=Path('/root/heroes3-ai-lab/evaluations/battle-terminal-credit-01'));args=parser.parse_args();root=args.run
rows=[]
for stage in sorted(root.iterdir()):
    if not stage.is_dir():continue
    result=stage/'RESULT.json';audit=stage/'AUDIT.json'
    item={'stage':stage.name}
    if result.exists():
        d=json.loads(result.read_text());item.update({k:d.get(k) for k in ('passed','qualified','actual_Adam_steps','admitted_stage_rows','suffix_stage_rows','error')})
    item['audit_passed']=json.loads(audit.read_text()).get('passed') if audit.exists() else None
    item['native_step_returns']=sum(1 for _ in stage.glob('phase-*/*-return.pt'))
    rows.append(item)
print(json.dumps(rows))
for name in ('RESULT.json','DEV-RESULT.json'):
    if (root/name).exists():print(name,(root/name).read_text()[:2500])
if (root/'MEMORY.jsonl').exists():
    readings=[]
    for line in (root/'MEMORY.jsonl').read_text().splitlines():
        try:readings.append(json.loads(line))
        except json.JSONDecodeError:pass
    if readings:print(json.dumps(dict(latest_memory=readings[-1],minimum_available_mib=min(r['available_mib'] for r in readings),maximum_swap_mib=max(r['swap_used_mib'] for r in readings))))
