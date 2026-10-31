"""Fixed four TRAIN cells; root must review/freeze before --execute. Zero PPO."""
import argparse
import json
import os
import signal
from pathlib import Path
import leases
from pipeline_common import (HERE, LAB, DEFAULT_INITIAL, DEFAULT_CAPSULE, INITIAL_SHA,
                             REGISTERED_JOBS, sha, source_inputs)

STUDY = LAB / 'evaluations/strategic-active-learning-native-01'


def write(path, value): path.write_text(json.dumps(value, indent=2) + '\n')


def resources(log, phase):
    mem = {k: int(v.split()[0]) for k, v in
           (line.split(':', 1) for line in Path('/proc/meminfo').read_text().splitlines())}
    record = dict(phase=phase, available_mib=mem['MemAvailable'] / 1024,
                  swap_mib=(mem['SwapTotal'] - mem['SwapFree']) / 1024)
    with log.open('a') as stream: stream.write(json.dumps(record) + '\n')
    assert record['available_mib'] > 2048 and record['swap_mib'] < 256


def command(argv, log):
    resources(log.with_suffix('.memory.jsonl'), 'before')
    with log.open('w') as stream: code = leases.run_owned(argv, env=dict(os.environ), stream=stream)
    assert code == 0, 'Engineering stop: preserve evidence, no retry: ' + str(log)
    resources(log.with_suffix('.memory.jsonl'), 'after')


def main():
    p = argparse.ArgumentParser(); p.add_argument('--out', type=Path, required=True)
    p.add_argument('--execute', action='store_true'); a = p.parse_args()
    # The preparer deliberately never creates this file. Root owns sealing.
    freeze = HERE / 'SOURCE_FREEZE.json'
    assert freeze.exists(), 'Root review and SOURCE_FREEZE required before planning/running'
    frozen = json.loads(freeze.read_text())['files']
    assert all(sha(path) == h for path, h in frozen.items())
    expected = {str(p): sha(p) for p in source_inputs()}
    assert all(frozen.get(path) == h for path, h in expected.items()), 'Incomplete source freeze'
    assert sha(DEFAULT_INITIAL) == INITIAL_SHA
    assert json.loads((STUDY / 'RESULT.json').read_text())['passed']
    jobs = []
    for seed, (mapname, player) in sorted(REGISTERED_JOBS.items()):
        index = seed - 2026104400
        raw = STUDY / 'curriculum' / f'cell-{index:02d}' / 'native'
        plan = json.loads((raw / 'PLAN.json').read_text())
        episode = json.loads((raw.parent / 'admitted/episode.json').read_text())
        assert episode['reward'] == -1. and episode['sampling_replay_exact']
        assert plan['checkpoint'] == str(DEFAULT_INITIAL) and plan['multiplier'] == 4
        assert (plan['map'], plan['owned_player'], plan['seed'], plan['opponent']) == (mapname, player, seed, 'Nullkiller2')
        assert episode['checkpoint_sha256'] == INITIAL_SHA and plan['logical_update'] == 0
        jobs.append(dict(index=index, map=mapname, player=player, seed=seed,
                         stochastic_native=str(raw), stochastic_plan_sha256=sha(raw / 'PLAN.json'),
                         stochastic_proposals_sha256=sha(raw / 'agent/typed-broker.jsonl')))
    assert len(jobs) == 4
    a.out.mkdir(parents=True, exist_ok=False)
    write(a.out / 'PLAN.json', dict(jobs=jobs, files=frozen, execute=a.execute, temperature=.25,
        initial_sha256=INITIAL_SHA, optimizer_steps=0, new_PPO_admissions=0, final_test_touched=False))
    if not a.execute: return 0
    report = dict(passed=False, entries=[], optimizer_steps=0, new_PPO_admissions=0,
                  manual_exploration_setting=True, manual_setting_is_learning=False, final_test_touched=False)
    try:
        for job in jobs:
            assert all(sha(path) == h for path, h in frozen.items())
            root = a.out / f"cell-{job['index']:02d}"; root.mkdir()
            command([str(LAB / 'venv/bin/python'), str(HERE / 'collect_episode.py'),
                '--capsule', str(DEFAULT_CAPSULE), '--checkpoint', str(DEFAULT_INITIAL),
                '--out', str(root / 'native'), '--map', job['map'], '--player', str(job['player']),
                '--opponent', 'Nullkiller2', '--arm', 'curriculum', '--logical-update', '0',
                '--seed', str(job['seed']), '--seconds', '120'], root / 'collect.log')
            command([str(LAB / 'venv/bin/python'), str(HERE / 'audit_game_v6.py'),
                     str(root / 'native'), str(root / 'raw-audit')], root / 'audit.log')
            command([str(LAB / 'gpu-venv/bin/python'), str(HERE / 'replay_sampling.py'),
                '--run', str(root / 'native'), '--native-audit', str(root / 'raw-audit/AUDIT.json'),
                '--out', str(root / 'sampler-replay')], root / 'replay.log')
            replay = json.loads((root / 'sampler-replay/AUDIT.json').read_text())
            assert replay['passed'] and replay['samples_admitted'] == 0 and replay['new_PPO_admissions'] == 0
            assert replay['replay_actions_logprobs_values_rng_exact']
            own = 'red' if job['player'] == 0 else 'blue'
            audit = json.loads((root / 'raw-audit/AUDIT.json').read_text())
            assert replay['decisions_replayed'] == audit['actual_decisions_checked']
            archived = Path(job['stochastic_native'])
            assert sha(archived / 'PLAN.json') == job['stochastic_plan_sha256']
            assert sha(archived / 'agent/typed-broker.jsonl') == job['stochastic_proposals_sha256']
            old = [json.loads(s) for s in (archived / 'agent/typed-broker.jsonl').read_text().splitlines()]
            new = [json.loads(s) for s in (root / 'native/agent/typed-broker.jsonl').read_text().splitlines()]
            assert old and new and old[0]['request'] == new[0]['request'], 'Initial public request differs from archived T1'
            prefix = 0; first_difference = None
            for number, (before, after) in enumerate(zip(old, new), 1):
                if before['request'] != after['request'] or before['action'] != after['action']:
                    first_difference = dict(step=number, request_equal=before['request'] == after['request'],
                                            T1_action=before['action'], T025_action=after['action'])
                    break
                prefix += 1
            entry = dict(job=job, valid_complete=True, victory=audit['winner'] == own,
                         decisions=replay['decisions_replayed'], T1_archived_victory=False,
                         initial_public_request_equal=True, equal_public_request_action_prefix=prefix,
                         first_difference=first_difference,
                         audit_sha256=sha(root / 'raw-audit/AUDIT.json'),
                         replay_sha256=sha(root / 'sampler-replay/AUDIT.json'))
            report['entries'].append(entry); write(a.out / 'PROGRESS.json', report)
        assert len(report['entries']) == 4 and all(sha(path) == h for path, h in frozen.items())
        wins = sum(entry['victory'] for entry in report['entries'])
        report.update(passed=True, actual_new_native_games=4, wins=wins, all_four_valid=True,
                      fixed_four_cells_temporarily_sample_success=wins >= 2,
                      ability_improvement_claim=False, automatic_PPO_authorized=False)
    except BaseException as error: report['error'] = repr(error)
    finally: leases.finish_owned_groups()
    write(a.out / 'RESULT.json', report)
    return 0 if report['passed'] else 1


def interrupt(signum, frame): raise KeyboardInterrupt('Calibration interrupted ' + str(signum))


signal.signal(signal.SIGTERM, interrupt)
if __name__ == '__main__': raise SystemExit(main())
