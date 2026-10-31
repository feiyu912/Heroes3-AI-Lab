"""Run the fixed multi-stack pilot only if all fixed v2 train pairs lack benefit."""
import json
from pathlib import Path
import subprocess
import time

HERE=Path(__file__).resolve().parent
v2=HERE.parent/'wait-variant-v2'
while True:
    cmdline=Path('/proc/85637/cmdline')
    if not cmdline.exists() or 'wait-variant-v2/run_variants.py' not in cmdline.read_text().replace('\0',' '):
        break
    time.sleep(5)
report=json.loads((v2/'wait-train-comparison.json').read_text())
rows=report['results']
assert len(rows)==8, 'v2 incomplete; refuse to skip fixed experiment'
if any(row['benefit_verified'] for row in rows):
    print('v2 produced benefit candidates; leave v3 frozen and unrun for now',flush=True)
else:
    print('All eight v2 pairs have no verified benefit; execute predeclared four v3 pairs',flush=True)
    subprocess.run(['bash','/mnt/g/Heroes3-AI-Lab/research/run-lab.sh',str(HERE/'run_multistack.py'),'--run'],check=True)
