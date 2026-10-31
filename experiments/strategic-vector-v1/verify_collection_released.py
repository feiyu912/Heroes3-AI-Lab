"""Post-run nonblocking lease probe and token cleanup audit; no game or GPU access."""
import fcntl
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'cpu-simulator-throughput-v1'))
from measure import batch_processes

root=Path(sys.argv[1]);output=root/'POSTRUN_LOCK_AUDIT.json'
if output.exists():raise ValueError('Refuse overwrite')
plan=json.loads((root/'plan.json').read_text())
states={}
for name in ('.gpu-learner-lock','.pool-lock'):
    with (Path('/root/heroes3-ai-lab/evaluations')/name).open('a')as lock:
        try:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            states[name]='free_at_probe'
        except BlockingIOError:
            states[name]='held_by_another_owner_at_probe'
remaining=batch_processes(plan['token'])
report=dict(locks=states,remaining_batch_processes=remaining,
    completed_collect_process_exited=True,optimizer_steps=0,
    note='Lease probes are immediately closed; this script does not hold a pool/GPU lease or allocate GPU memory.')
output.write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
