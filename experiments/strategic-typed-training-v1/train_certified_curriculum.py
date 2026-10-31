"""Run one complete eight-cell curriculum update from a sealed ledger."""
import json,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
ledger=json.loads((HERE/'balanced-ack-certified-01/RESULT.json').read_text());assert ledger['passed'] and len(ledger['episodes'])==8
command=['/root/heroes3-ai-lab/gpu-venv/bin/python',str(HERE/'train_update_v2.py'),
    '--initialize',str(HERE/'cuda-update-engineering-01/update-1.pt'),
    '--capsule','/root/heroes3-ai-lab/evaluations/typed-schema4-ack-drain-capsule-01',
    '--purpose','curriculum_training','--out',str(HERE/'cuda-curriculum-ack-01')]
for e in ledger['episodes']:command+=['--admission',e['admission']]
raise SystemExit(subprocess.run(command).returncode)
