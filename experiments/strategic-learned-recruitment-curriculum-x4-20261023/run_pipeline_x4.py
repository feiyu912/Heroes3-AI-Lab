"""Plan by default; explicitly executed by root only.

Exactly eight registered x4 TRAIN cells, then one unchanged PPO update.
The only controlled factor is the owned hero's starting army x4 on private
TRAIN map copies.  Original maps, opponents, seeds, initialization, native
capsule and optimizer remain fixed.
"""
import argparse, json, subprocess
from pathlib import Path
from pipeline_common import (HERE, LAB, BASE, EPOCH, INITIAL_SHA, DEFAULT_CAPSULE,
    DEFAULT_INITIAL, jobs, source_inputs, capsule_inputs, selection, sha,
    validate_cells)

def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--capsule', type=Path, default=DEFAULT_CAPSULE)
    parser.add_argument('--checkpoint', type=Path, default=DEFAULT_INITIAL)
    parser.add_argument('--seed-base', type=int, default=2026103900)
    parser.add_argument('--seconds', type=float, default=120)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--collect-only', action='store_true')
    args = parser.parse_args()
    assert args.seconds > 0
    chosen = selection()
    registered_jobs = jobs(args.seed_base)
    assert [job['seed'] for job in registered_jobs] == list(range(2026103900, 2026103908))
    checkpoint = args.checkpoint.resolve()
    capsule = args.capsule.resolve()
    initialization = json.loads((checkpoint.parent / 'AUDIT.json').read_text())
    initial_sha = initialization['initialization_sha256']
    assert initial_sha == INITIAL_SHA, 'Only the registered zero-prior schema6 initialization is admitted'
    assert sha(checkpoint) == initial_sha
    assert initialization['parent_sha256'] == '83319be8bde5d94eea839b1a889821449a7c1492c65da7ca6cde2deb63aab25a'
    assert initialization['new_Adam_state_empty'] and initialization['readback_exact']
    inputs = source_inputs() + capsule_inputs(capsule) + [
        Path(__file__).resolve(), HERE / 'train_update_x4.py',
        checkpoint, checkpoint.parent / 'AUDIT.json']
    frozen = {str(path): sha(path) for path in inputs}
    args.out.mkdir(parents=True, exist_ok=False)
    commands = []
    admissions = []
    for index, job in enumerate(registered_jobs):
        cell = args.out / f'cell-{index:02d}'
        run = cell / 'native'
        audit = cell / 'raw-audit'
        admission = cell / 'admitted'
        admissions.append(admission)
        collect = ['/usr/bin/python3', str(HERE / 'collect_episode_x4.py'),
                   '--capsule', str(capsule), '--checkpoint', str(checkpoint),
                   '--map', job['map'], '--player', str(job['player']),
                   '--opponent', job['opponent'], '--seed', str(job['seed']),
                   '--logical-update', '0', '--seconds', str(args.seconds),
                   '--out', str(run)]
        raw = [str(LAB / 'venv/bin/python'), str(HERE / 'audit_game_v6.py'),
               str(run), str(audit)]
        admit = [str(LAB / 'gpu-venv/bin/python'), str(HERE / 'admit_episode_v5.py'),
                 '--run', str(run), '--native-audit', str(audit / 'AUDIT.json'),
                 '--out', str(admission)]
        commands.append(dict(cell=index, job=job, commands=[collect, raw, admit]))
    train = [str(LAB / 'gpu-venv/bin/python'), str(HERE / 'train_update_x4.py'),
             '--initialize', str(checkpoint), '--capsule', str(capsule),
             '--purpose', 'curriculum_training', '--seed', str(args.seed_base),
             '--out', str(args.out / 'update-01')]
    for directory in admissions:
        train += ['--admission', str(directory)]
    plan = dict(epoch=EPOCH, execute=args.execute, collect_only=args.collect_only,
                checkpoint=str(checkpoint), checkpoint_sha256=initial_sha,
                capsule=str(capsule), jobs=commands, training_command=train,
                input_sha256=frozen, optimizer_reset=True, logical_update=0,
                parallelism=1,
                source_scope='Same schema6 native runtime and zero-prior initialization; only the actual owned starting army is x4 on private TRAIN map copies; exactly one fresh update',
                planned_updates=1,
                calibration_selection=chosen,
                DEV_seeds=list(range(2026104200, 2026104208)),
                controlled_factor=dict(
                    changed='actual owned hero starting army only',
                    original_owned_army='20 pikemen + 10 archers',
                    boosted_owned_army='80 pikemen + 40 archers (x4)',
                    opponent_armies_unchanged=True,
                    original_maps_unchanged=True,
                    initialization_unchanged=True,
                    seeds_unchanged=True,
                    ppo_and_lr_unchanged=True),
                TRAIN_pairing=dict(same_native_seeds=True,
                    same_sampler_seed_derivation=True,
                    same_initial_learner_RNG_seed=2026103900,
                    old_samples_reused=False),
                DEV_design=dict(arms=['minus4_initial', 'minus4_updated',
                                      'zero_initial', 'zero_updated'],
                    unique_cells=8, unique_native_games=32,
                    shared_native_seed_within_cell=True,
                    finaltest_touched=False))
    write(args.out / 'PLAN.json', plan)
    if not args.execute:
        print(json.dumps({'plan_only': True, 'cells': 8, 'optimizer_steps': 0}))
        return 0
    completed = []
    try:
        for item, directory in zip(commands, admissions):
            assert all(sha(Path(path)) == digest for path, digest in frozen.items())
            directory.parent.mkdir()
            for stage, argv in zip(('collect', 'audit', 'admit'), item['commands']):
                result = subprocess.run(argv, capture_output=True, text=True)
                (directory.parent / (stage + '.log')).write_text(
                    result.stdout + '\nSTDERR:\n' + result.stderr)
                assert result.returncode == 0, f'cell{item["cell"]}/{stage} failed; no update'
            episode = json.loads((directory / 'episode.json').read_text())
            report = json.loads((directory / 'AUDIT.json').read_text())
            assert report['passed'] and episode['checkpoint_sha256'] == initial_sha
            assert episode['job']['logical_update'] == 0
            assert episode['job']['map'] == item['job']['map']
            completed.append(episode)
            write(args.out / 'PROGRESS.json', dict(completed=completed, optimizer_steps=0))
        validate_cells(completed)
        assert all(sha(Path(path)) == digest for path, digest in frozen.items())
        if args.collect_only:
            write(args.out / 'RESULT.json', dict(passed=True, collected=True,
                episodes=completed, optimizer_steps=0))
            return 0
        result = subprocess.run(train, capture_output=True, text=True)
        (args.out / 'train.log').write_text(result.stdout + '\nSTDERR:\n' + result.stderr)
        assert result.returncode == 0, 'Training failed; preserve the original partial checkpoint/report'
        write(args.out / 'RESULT.json', dict(passed=True, episodes=completed,
            training_result=str(args.out / 'update-01/RESULT.json'),
            ability_improvement_claim=False))
        return 0
    except BaseException as error:
        write(args.out / 'RESULT.json', dict(passed=False, error=repr(error),
            completed=completed, complete_curriculum=False,
            ability_improvement_claim=False))
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
