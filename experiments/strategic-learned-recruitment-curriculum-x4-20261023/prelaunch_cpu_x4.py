"""CPU-only prelaunch audit for the eight x4 TRAIN cells.

Starts no native client, loads no CUDA model and acquires no resource lock.
Each cell is prepared through the real collector in --prepare-only mode, then
the private map copy, frozen inputs and sampling-seed pairing are checked.
"""
import argparse, hashlib, json, subprocess
from pathlib import Path
import pipeline_common as pc

def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--capsule', type=Path, default=pc.DEFAULT_CAPSULE)
    parser.add_argument('--checkpoint', type=Path, default=pc.DEFAULT_INITIAL)
    args = parser.parse_args()
    chosen = pc.selection()
    checkpoint = args.checkpoint.resolve()
    capsule = args.capsule.resolve()
    initialization = json.loads((checkpoint.parent / 'AUDIT.json').read_text())
    assert pc.sha(checkpoint) == pc.INITIAL_SHA == initialization['initialization_sha256']
    assert initialization['new_Adam_state_empty'] and initialization['readback_exact']
    pc.validate_capsule(capsule)
    registered = pc.jobs()
    assert [job['seed'] for job in registered] == list(range(2026103900, 2026103908))
    manifest = pc.map_manifest()
    before = {str(Path(source['path'])): source['sha256'] for source in manifest['sources'].values()}
    before.update({str(Path(entry['path'])): entry['sha256'] for entry in manifest['variants']
                   if entry['multiplier'] == pc.MULTIPLIER})
    assert all(pc.sha(path) == digest for path, digest in before.items())
    args.out.mkdir(parents=True, exist_ok=False)
    cells = []
    for index, job in enumerate(registered):
        native = args.out / f'cell-{index:02d}' / 'native'
        command = ['/usr/bin/python3', str(pc.HERE / 'collect_episode_x4.py'),
                   '--capsule', str(capsule), '--checkpoint', str(checkpoint),
                   '--map', job['map'], '--player', str(job['player']),
                   '--opponent', job['opponent'], '--seed', str(job['seed']),
                   '--logical-update', '0', '--seconds', '120',
                   '--out', str(native), '--prepare-only']
        result = subprocess.run(command, capture_output=True, text=True)
        (native.parent / 'prepare.log').write_text(
            result.stdout + '\nSTDERR:\n' + result.stderr)
        assert result.returncode == 0, f'prepare failed for cell {index}'
        prepared = json.loads((native / 'PREPARED.json').read_text())
        plan = json.loads((native / 'PLAN.json').read_text())
        assert prepared['passed'] and prepared['native_runs'] == 0
        assert prepared['GPU_steps'] == 0 and prepared['optimizer_steps'] == 0
        assert prepared['locks_acquired'] is False and prepared['input_sha_unchanged'] is True
        assert prepared['source_inputs'] == len(plan['hashes'])
        assert plan['map'] == job['map'] and plan['source_map'] == job['source_map']
        assert plan['owned_player'] == job['player'] and plan['opponent'] == job['opponent']
        assert plan['seed'] == job['seed'] and plan['logical_update'] == 0
        assert plan['pipeline_epoch'] == pc.EPOCH
        assert plan['training_curriculum'] == 'owned-start-army-x4-vs-original-v1'
        assert plan['selected_multiplier'] == 4
        assert plan['selection_record_sha256'] == pc.sha(pc.SELECTION)
        assert plan['curriculum_variant']['multiplier'] == 4
        assert plan['curriculum_variant']['map_sha256'] == pc.variant_by_name(job['map'])['sha256']
        copied = native / 'data/vcmi/Maps/adv' / (job['map'] + '.vmap')
        assert pc.sha(copied) == plan['curriculum_variant']['map_sha256']
        material = json.dumps(dict(seed=job['seed'], map=job['source_map'],
            player=job['player'], opponent=job['opponent'], logical_update=0),
            sort_keys=True).encode()
        expected_sampling_seed = int.from_bytes(hashlib.sha256(material).digest()[:8], 'little') % (2**63 - 1)
        assert plan['sampling_seed'] == expected_sampling_seed
        assert all(pc.sha(Path(path)) == digest for path, digest in plan['hashes'].items())
        assert all(pc.sha(path) == digest for path, digest in before.items())
        cells.append(dict(cell=index, job=job, prepared=prepared,
                          plan_sha256=pc.sha(native / 'PLAN.json'),
                          sampling_seed_before_native=plan['sampling_seed'],
                          private_map_sha256=plan['curriculum_variant']['map_sha256'],
                          native_runs=0, GPU_steps=0, optimizer_steps=0,
                          locks_acquired=False))
    write(args.out / 'PRELAUNCH_CPU_AUDIT.json', dict(
        passed=True, CPU_only=True, cells=len(cells),
        all_eight_TRAIN_jobs_match_registered_plan=len({json.dumps(c['job'], sort_keys=True) for c in cells}) == 8,
        first_actual_collector_sampler_seed_identical=cells[0]['sampling_seed_before_native'],
        selection=chosen['selection'], selection_record_sha256=pc.sha(pc.SELECTION),
        checkpoint_sha256=pc.INITIAL_SHA,
        capsule=str(capsule), source_inputs=cells[0]['prepared']['source_inputs'],
        cells_evidence=cells, native_runs=0, GPU_steps=0, optimizer_steps=0,
        locks_acquired=False, shared_runtime_maps_written=False))
    print(json.dumps(dict(passed=True, cells=len(cells), native_runs=0,
        GPU_steps=0, optimizer_steps=0, locks_acquired=False), indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
