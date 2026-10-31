#!/usr/bin/env python3
"""Synthetic CPU checks of evaluation gates and boundary comparison; NO games."""
import argparse
import copy
import json
from pathlib import Path
import shutil
import sys
from types import SimpleNamespace
from unittest.mock import patch

import torch
import evaluate_pairs as evaluation
import verify_training_boundary as boundary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    (args.out / 'SYNTHETIC_ONLY.txt').write_text('All games and results below are mocked fixtures. No real game or GPU was started.\n')
    checks, calls = {}, []
    initial = evaluation.HERE / 'checkpoints/prior-initial-v2.pt'
    model_sha = evaluation.sha(initial)
    fixtures = args.out / 'mocked-game-fixtures'
    fixtures.mkdir()
    fail_consumption = False
    def fake_game(command, **kwargs):
        index = len(calls)
        calls.append(command)
        agent = fixtures / str(index)
        agent.mkdir()
        native_dir = agent / 'synthetic-native'
        native_dir.mkdir()
        option = lambda name: command[command.index(name) + 1]
        red, blue = option('--red'), option('--blue')
        request = dict(request_id=1, player=0 if red == 'DirectorAI' else 1, day=1, hero=1,
                       **{'from': [1, 1, 0]}, candidates=[dict(position=[2, 1, 0], next=[2, 1, 0])])
        (agent / 'request-00000001.json').write_text(json.dumps(request))
        (agent / 'broker-ready.json').write_text(json.dumps(dict(model_version='sha256:' + model_sha)))
        (agent / 'broker-trace.jsonl').write_text(json.dumps(dict(event='decision_committed', request_id=1,
            action=0, request_file='request-00000001.json')) + '\n')
        decision = dict(selected_candidate=1 if fail_consumption else 0, player=request['player'], day=1,
                        hero=1, **{'from': [1, 1, 0]}, destination=[2, 1, 0], step=[2, 1, 0])
        (native_dir / 'strategy-decisions.jsonl').write_text(json.dumps(decision) + '\n')
        native = dict(completed=True, inputs_unchanged=True, actual_ai=dict(red=red, blue=blue),
                      winner='red', run_dir=str(native_dir), SYNTHETIC_ONLY=True)
        (agent / 'smoke-result.json').write_text(json.dumps(dict(passed=True, native_result=native)))
        return SimpleNamespace(returncode=0, stdout='AGENT_DIR=' + str(agent) + '\n')

    output = args.out / 'SYNTHETIC-evaluation-success'
    argv = ['evaluate_pairs.py', '--out', str(output), '--candidate', str(initial)]
    with patch.object(sys, 'argv', argv), patch.object(evaluation.subprocess, 'run', fake_game):
        evaluation.main()
    result = json.loads((output / 'results.json').read_text())
    assert result['status'] == 'completed' and len(result['pairs']) == 8
    assert result['net_win_delta'] == 0 and all(row['native_consumption_verified'] for row in result['rows'])
    assert [row['model'] for row in result['rows'][:4]] == ['baseline', 'candidate', 'candidate', 'baseline']
    checks['paired_order_and_aggregation'] = dict(passed=True, synthetic_pairs=8)
    fail_consumption = True
    output = args.out / 'SYNTHETIC-evaluation-consumption-failure'
    argv = ['evaluate_pairs.py', '--out', str(output), '--candidate', str(initial)]
    with patch.object(sys, 'argv', argv), patch.object(evaluation.subprocess, 'run', fake_game):
        try:
            evaluation.main()
        except RuntimeError as error:
            assert 'Invalid evaluation game' in str(error)
        else:
            raise AssertionError('Mismatched native action was accepted')
    result = json.loads((output / 'results.json').read_text())
    assert result['status'] == 'failed' and not result['rows'][0]['valid'] and result['rows'][0]['win'] is None
    assert not result['rows'][0]['native_consumption_verified']
    checks['consumption_mismatch_fails_without_loss_imputation'] = True

    # Exercise checkpoint+native trace comparison with explicit synthetic files.
    root = args.out / 'SYNTHETIC-boundary-fixture'
    root.mkdir()
    fixture = dict(state_dict={'actor.weight': torch.tensor([1., 2.])}, optimizer={'state': {}},
                   torch_rng=torch.get_rng_state(), cuda_rng=[], python_rng=('synthetic',),
                   training_updates=1, optimizer_steps_total=8, complete_update_boundary=True,
                   protocol_sha256='synthetic', protocol={'SYNTHETIC_ONLY': True},
                   lineage={'mode': 'weights-only-migration', 'reset_optimizer': True, 'reset_rng': True})
    for branch in ('continuous-2', 'split-1', 'resume-2'):
        directory = root / branch
        directory.mkdir()
        (directory / 'training.json').write_text(json.dumps(dict(status='completed', SYNTHETIC_ONLY=True)))
    torch.save(fixture, root / 'split-1/update-1.pt')
    torch.save(fixture, root / 'continuous-2/update-1.pt')
    second = dict(fixture, training_updates=2, optimizer_steps_total=16)
    torch.save(second, root / 'continuous-2/update-2.pt')
    resumed = dict(second, lineage=dict(mode='resume', parent_sha256=boundary.sha(root / 'split-1/update-1.pt'),
                                       reset_optimizer=False, reset_rng=False))
    torch.save(resumed, root / 'resume-2/update-2.pt')
    for update in (1, 2):
        for branch in ('continuous-2', 'split-1' if update == 1 else 'resume-2'):
            for episode in range(4):
                episode_dir = root / branch / f'update-{update}-episode-{episode}'
                episode_dir.mkdir()
                (episode_dir / 'rollout.jsonl').write_text('{"SYNTHETIC_ONLY": true, "action": 0}\n')
                (episode_dir / 'strategy-decisions.jsonl').write_text('{"SYNTHETIC_ONLY": true, "selected_candidate": 0}\n')
                record = dict(config={'seed': episode}, valid=True, reward=1.0, decisions=1,
                              native_consumption_verified=True, rollout_dir=str(episode_dir),
                              native=dict(run_dir=str(episode_dir), completed=True, winner='red'))
                (episode_dir / 'episode.json').write_text(json.dumps(record))
    comparison = boundary.compare(root)
    assert comparison['passed']
    checks['synthetic_boundary_equal'] = True
    changed = copy.deepcopy(resumed)
    changed['state_dict']['actor.weight'][0] += .01
    torch.save(changed, root / 'resume-2/update-2.pt')
    assert not boundary.compare(root)['passed']
    torch.save(resumed, root / 'resume-2/update-2.pt')
    (root / 'resume-2/update-2-episode-0/strategy-decisions.jsonl').write_text('{"SYNTHETIC_ONLY": true, "selected_candidate": 1}\n')
    unequal = boundary.compare(root)
    assert not unequal['passed'] and not unequal['checks']['update_2_episode_0']['equal']
    checks['changed_weights_and_native_decisions_detected'] = True
    protected = args.out / 'synthetic-frozen-input.txt'
    protected.write_text('before')
    digest = boundary.sha(protected)
    protected.write_text('after')
    try:
        boundary.assert_frozen({str(protected): digest})
    except RuntimeError:
        checks['changed_input_rejected'] = True
    else:
        raise AssertionError('Changed frozen input accepted')
    # Real CPU subprocesses only: ensure separately sessioned owned children
    # are detected and cleaned before another learning stage could start.
    dummy = args.out / 'synthetic-owned-process.py'
    dummy.write_text("import subprocess, sys, time\n"
                     "subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(20)'], start_new_session=True)\n"
                     "time.sleep(2.2)\n")
    stage = dict(name='SYNTHETIC-process-cleanup', directory=str(args.out / 'no-training'),
                 command=[sys.executable, str(dummy)])
    with patch.object(boundary, 'gpu_sample', lambda: dict(available=False, SYNTHETIC_ONLY=True)):
        try:
            boundary.run_stage(stage, args.out, {}, 10)
        except RuntimeError as error:
            assert 'left owned processes' in str(error)
        else:
            raise AssertionError('Leftover separately sessioned child was accepted')
    cleanup = json.loads((args.out / 'SYNTHETIC-process-cleanup-stage.json').read_text())
    assert cleanup['leftover_owned_processes_after_exit'] and not cleanup['survivors_after_cleanup']
    checks['separate_session_owned_child_cleanup'] = cleanup
    assert not torch.cuda.is_initialized()
    snapshot = args.out / 'sources'
    snapshot.mkdir()
    for path in (Path(__file__), Path(evaluation.__file__), Path(boundary.__file__)):
        shutil.copy2(path, snapshot / path.name)
    report = dict(passed=True, game_started=False, GPU_initialized=False, synthetic_only=True, checks=checks,
                  hashes={str(path): boundary.sha(path) for path in
                          (Path(__file__), Path(evaluation.__file__), Path(boundary.__file__))})
    boundary.atomic_json(args.out / 'AUDIT.json', report)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
