"""Launch the frozen evaluator with only relocated lease paths injected."""
import os, runpy, sys
from pathlib import Path
import leases
sys.modules['leases'] = leases
leases.verify_pair()
project = Path(os.environ['HEROES3_PROJECT_ROOT'])
target = project/'experiments/battle-observed-MC-DEV-20261024/evaluate_policy_steps.py'
sys.path.insert(0, str(target.parent))
sys.argv[0] = str(target)
runpy.run_path(str(target), run_name='__main__')
