"""Run the preregistered 16 games serially. Root agent schedules this script.

Each episode obtains the common simulation lock in run_episode.py. This script
does not instantiate a learner, read B64, or consume locked dev/test fixtures.
"""
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    here = Path(__file__).resolve().parent
    out = here/'runs'/'train'
    assert not out.exists(), 'Refuse to overwrite or mix an existing pilot'
    out.mkdir(parents=True)
    files = list(here.glob('*.py')) + list(here.glob('*.sh')) + [here/'scenarios.json',here/'PREREGISTRATION.md']
    frozen = {str(p):digest(p) for p in files}
    (out/'PROTOCOL.json').write_text(json.dumps(dict(schema='visible-exchange-pilot-v1',
        frozen=frozen,seeds=[2026101841,2026101842],scenarios=[0,1],
        roles=['attacker','defender'],policies=['teacher','visible-exchange'],
        independent_evaluation=False,bc_eligible=False),indent=2))
    rows = []
    started = time.monotonic()
    for scenario in (0,1):
        for role in ('attacker','defender'):
            for seed in (2026101841,2026101842):
                for policy in ('teacher','visible-exchange'):
                    assert all(digest(Path(p)) == h for p,h in frozen.items())
                    target = out/f'{scenario}-{role}-{seed}-{policy}.json'
                    command = ['bash',str(here/'run-events-lab.sh'),str(here/'run_episode.py'),
                        '--scenario',str(scenario),'--role',role,'--seed',str(seed),
                        '--policy',policy,'--output',str(target)]
                    with target.with_suffix('.log').open('w') as log:
                        proc = subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                        try:
                            code = proc.wait(timeout=180)
                        except BaseException:
                            os.killpg(proc.pid,signal.SIGTERM)
                            try:
                                proc.wait(timeout=10)
                            except subprocess.TimeoutExpired:
                                os.killpg(proc.pid,signal.SIGKILL)
                                proc.wait()
                            raise
                    assert code == 0, f'Game failed, preserve evidence and stop: {target}'
                    result = json.loads(target.read_text())
                    assert result['completed'] and result['terminated'] and not result['truncated']
                    assert result['invalid_actions'] == 0 and result['terminal_outcome']['result_type'] == 0
                    assert result['matched_action_windows'] == result['steps'] and result['terminal_event_count'] == 1
                    assert digest(Path(result['archive'])) == result['archive_sha256']
                    assert all(digest(Path(p)) == h for p,h in frozen.items())
                    side = str(int(role=='defender'))
                    loss = result['terminal_outcome']['casualties'][side]
                    rows.append(dict(scenario=scenario,role=role,seed=seed,policy=policy,
                        won=int(result['success']),main_loss=loss.get('6',0),
                        total_loss=sum(loss.values()),summary=str(target),archive_sha256=result['archive_sha256']))
                    print(json.dumps(rows[-1]),flush=True)
    pairs = []
    for scenario in (0,1):
        for role in ('attacker','defender'):
            for seed in (2026101841,2026101842):
                p = {r['policy']:r for r in rows if (r['scenario'],r['role'],r['seed']) == (scenario,role,seed)}
                base, candidate = p['teacher'],p['visible-exchange']
                pairs.append(dict(scenario=scenario,role=role,seed=seed,
                    delta_wins=candidate['won']-base['won'],
                    delta_main_loss=candidate['main_loss']-base['main_loss'],
                    delta_total_loss=candidate['total_loss']-base['total_loss']))
    report = dict(schema='visible-exchange-pilot-result-v1',episodes=len(rows),pairs=pairs,
        net_wins=sum(p['delta_wins'] for p in pairs),
        mean_delta_main_loss=sum(p['delta_main_loss'] for p in pairs)/len(pairs),
        mean_delta_total_loss=sum(p['delta_total_loss'] for p in pairs)/len(pairs),
        wall_seconds=time.monotonic()-started,bc_eligible=False,certified=False,
        independent_improvement_proven=False,rows=rows)
    (here/'PILOT_RESULTS.json').write_text(json.dumps(report,indent=2))


if __name__ == '__main__':
    main()
