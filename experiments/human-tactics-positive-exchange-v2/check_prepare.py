"""Verify syntax and default launcher without creating an environment."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--output',required=True)
    args=ap.parse_args()
    here=Path(__file__).resolve().parent
    output=Path(args.output)
    assert not output.exists() and not (here/'runs/train').exists()
    files=sorted(here.glob('*.py'))
    for path in files:compile(path.read_text(),str(path),'exec')
    subprocess.run(['bash','-n',str(here/'run-events-lab.sh')],check=True)
    result=subprocess.run([sys.executable,str(here/'launch.py')],capture_output=True,text=True,check=True)
    plan=json.loads(result.stdout)
    assert plan['mode']=='plan-only' and plan['games']==16 and plan['optimizer_steps']==0
    assert not (here/'runs/train').exists()
    report=dict(passed=True,python_sources_compiled=len(files),shell_syntax=True,
        default_launcher_plan=plan,no_native_run_directory=True,
        manifest_sha256=hashlib.sha256((here/'FROZEN_SOURCES.json').read_bytes()).hexdigest())
    output.write_text(json.dumps(report,indent=2))
    print(json.dumps(dict(passed=True,python_sources_compiled=len(files),mode=plan['mode'],
                         frozen_artifacts=len(plan['frozen_artifacts']),new_native_games=0)))


if __name__=='__main__':main()
