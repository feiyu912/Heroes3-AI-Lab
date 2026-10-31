"""Independent raw-evidence audit of x4 curriculum training batch-02.

Reads only preserved evidence.  Does not run native, CUDA, or an optimizer.
The source files are hashed as they exist at audit time; this is an integrity
check, not a second training run.
"""
import hashlib
import json
from pathlib import Path

import torch

LAB = Path('/root/heroes3-ai-lab')
EXP = Path('/mnt/g/Heroes3-AI-Lab/experiments')
OUT = EXP / 'takeover-20261023/independent-evidence-02/training-batch-02-audit-01'
RUN = LAB / 'evaluations/strategic-learned-recruitment-curriculum-x4-train-20261023-02'
RUN01 = LAB / 'evaluations/strategic-learned-recruitment-curriculum-x4-train-20261023-01'
INIT = EXP / 'strategic-learned-recruitment-policy-v3/initialization-02/recruitment-initialization.pt'
INIT_AUDIT = INIT.parent / 'AUDIT.json'
INIT_SHA = '1510149ef1c2c896e3125e6468e9e58234a8bfc9e4278ad239f9d6840e1c62a1'
CHECKPOINT = RUN / 'update-01/update-1.pt'
CHECKPOINT_SHA = '6a0bd8f7c800157258e77cdbdece7fdb4da183ae2a86c103ed050fb6af6e876e'
SAMPLE = 272
EXPECTED_CELLS = {
    (f'active-calibration-train-0{m + 1}-owned{p}-hero-x4', p, o)
    for m in range(2) for p in (0, 1) for o in ('EmptyAI', 'Nullkiller2')
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def main():
    out = {}
    errors = []

    def check(name, value, detail=None):
        out[name] = bool(value)
        if not value:
            errors.append({'check': name, 'detail': detail})

    out['scope'] = 'independent integrity/accounting audit of one x4 TRAIN curriculum update; no ability claim'
    out['run'] = str(RUN)
    out['checkpoint'] = str(CHECKPOINT)
    out['checkpoint_sha256'] = sha(CHECKPOINT)
    check('checkpoint_sha256_expected', out['checkpoint_sha256'] == CHECKPOINT_SHA,
          out['checkpoint_sha256'])

    run_result = read(RUN / 'RESULT.json')
    train_result = read(RUN / 'update-01/RESULT.json')
    out['run_result_sha256'] = sha(RUN / 'RESULT.json')
    out['train_result_sha256'] = sha(RUN / 'update-01/RESULT.json')
    check('run_passed', run_result.get('passed') is True, run_result)
    check('training_completed_update', train_result.get('completed_update') is True, train_result)
    check('exactly_one_training_update', train_result.get('training_updates') == 1, train_result.get('training_updates'))
    check('actual_cuda_adam_steps_272', train_result.get('cuda_optimizer_steps') == SAMPLE, train_result.get('cuda_optimizer_steps'))
    check('optimizer_total_272', train_result.get('optimizer_steps_total') == SAMPLE, train_result.get('optimizer_steps_total'))
    check('no_early_kl_stop', train_result['progress'].get('early_stop_kl') is False)
    check('one_completed_update_boundary', train_result['progress'].get('completed') is True)
    check('training_samples_4318', train_result.get('samples') == 4318, train_result.get('samples'))
    check('training_episodes_8', train_result.get('episodes') == 8, train_result.get('episodes'))
    check('training_trajectory_4_wins_4_losses',
          train_result.get('training_wins') == 4 and train_result.get('training_losses') == 4,
          (train_result.get('training_wins'), train_result.get('training_losses')))

    episode_rows = run_result.get('episodes', [])
    check('run_result_has_8_episodes', len(episode_rows) == 8, len(episode_rows))
    check('episode_cells_exact', {
        (e['job']['map'], e['job']['owned_player'], e['job']['opponent']) for e in episode_rows
    } == EXPECTED_CELLS)
    check('episode_seeds_exact', [e['job']['seed'] for e in episode_rows] == list(range(2026103900, 2026103908)))
    check('all_episodes_logical_update_0', all(e['job']['logical_update'] == 0 for e in episode_rows))
    check('all_episodes_parent_initialization', all(e['checkpoint_sha256'] == INIT_SHA for e in episode_rows))
    check('all_episode_audits_passed', all(read(e['raw_audit_path']).get('passed') is True for e in episode_rows))
    check('all_native_games_completed', all(e['native']['completed'] and e['native']['inputs_unchanged'] for e in episode_rows))
    check('all_transports_drained', all(e.get('transport_drained') is True for e in episode_rows))
    check('all_sampling_replays_exact', all(e.get('sampling_replay_exact') is True for e in episode_rows))

    # Keep the raw hashes in the audit and verify every one.
    raw_ok = True
    raw_count = 0
    for e in episode_rows:
        audit = read(e['raw_audit_path'])
        raw_ok &= sha(e['raw_audit_path']) == e['raw_audit_sha256']
        raw_root = Path(audit['raw'])
        for rel, digest in audit.get('raw_sha256', {}).items():
            raw_count += 1
            if not (raw_root / rel).is_file():
                raw_ok = False
            elif sha(raw_root / rel) != digest:
                raw_ok = False
    answer_ok = True
    answer_count = 0
    for e in episode_rows:
        audit = read(e['raw_audit_path'])
        for rel, digest in audit.get('source_sha256', {}).items():
            # Absolute paths include run-specific native copies.  Verify the
            # shared experiment sources directly; run-local copies were already
            # hashed by the pass above and by the collector plan.
            if rel.startswith('/mnt/g/Heroes3-AI-Lab/'):
                answer_count += 1
                if not Path(rel).is_file() or sha(rel) != digest:
                    answer_ok = False
    out['raw_files_hashed'] = raw_count
    out['shared_source_files_hashed'] = answer_count
    check('raw_audit_and_raw_files_hashes_match', raw_ok)
    check('shared_experiment_source_hashes_match', answer_ok)

    admissions_ok = True
    for i, e in enumerate(episode_rows):
        report = read(RUN / f'cell-{i:02d}/admitted/AUDIT.json')
        admissions_ok &= report.get('passed') is True and report.get('optimizer_steps') == 0
        admissions_ok &= report.get('samples_admitted') == e['decisions']
        admissions_ok &= report.get('output_sha256', {}).get('samples.jsonl') == sha(RUN / f'cell-{i:02d}/admitted/samples.jsonl')
        admissions_ok &= report.get('output_sha256', {}).get('episode.json') == sha(RUN / f'cell-{i:02d}/admitted/episode.json')
    check('admission_outputs_complete_and_unoptimized', admissions_ok)

    # Deterministic reproduction against batch-01: compare all per-decision
    # request/action bytes.  Raw audit JSON SHA includes run-local paths, so it
    # is intentionally not asserted equal.
    repro = True
    mismatch_counts = {}
    for i in range(8):
        for kind in ('request', 'action'):
            a = RUN01 / f'cell-{i:02d}/native/agent'
            b = RUN / f'cell-{i:02d}/native/agent'
            names_a = sorted(p.name for p in a.glob(f'{kind}-*.json'))
            names_b = sorted(p.name for p in b.glob(f'{kind}-*.json'))
            if names_a != names_b:
                repro = False
                mismatch_counts[f'cell-{i:02d}/{kind}/names'] = (len(names_a), len(names_b))
                continue
            bad = [n for n in names_a if (a / n).read_bytes() != (b / n).read_bytes()]
            if bad:
                repro = False
                mismatch_counts[f'cell-{i:02d}/{kind}/bytes'] = len(bad)
    out['batch01_vs_batch02_byte_mismatches'] = mismatch_counts
    check('batch01_batch02_actions_requests_byte_identical', repro)

    bundle = torch.load(CHECKPOINT, map_location='cpu', weights_only=True)
    out['checkpoint_format'] = bundle.get('format')
    out['checkpoint_parent_sha256'] = bundle.get('parent_checkpoint_sha256')
    out['checkpoint_training_updates'] = bundle.get('training_updates')
    out['checkpoint_optimizer_steps_total'] = bundle.get('optimizer_steps_total')
    out['checkpoint_complete'] = bundle.get('complete_update_boundary')
    out['protocol_schema'] = bundle.get('protocol', {}).get('schema')
    out['curriculum_epoch'] = bundle.get('protocol', {}).get('curriculum_epoch')
    out['lineage_training_epoch'] = bundle.get('lineage', {}).get('training_epoch')
    out['lineage_parent_training_updates'] = bundle.get('lineage', {}).get('parent_training_updates')
    out['collection_states'] = len(bundle.get('collection_states', {}))
    check('checkpoint_sha_is_expected', sha(CHECKPOINT) == CHECKPOINT_SHA)
    check('checkpoint_complete_and_one_update',
          bundle.get('complete_update_boundary') is True and bundle.get('training_updates') == 1)
    check('checkpoint_parent_is_registered_initialization',
          bundle.get('parent_checkpoint_sha256') == INIT_SHA)
    check('checkpoint_protocol_schema_exact',
          bundle['protocol'].get('schema') == 'strategic-learned-recruitment-prior-zero-training-v1')
    check('checkpoint_curriculum_epoch_x4',
          bundle['protocol'].get('curriculum_epoch') == 'strategic-learned-recruitment-curriculum-x4-training-v1')
    check('lineage_records_x4_epoch',
          bundle['lineage'].get('training_epoch') == 'strategic-learned-recruitment-curriculum-x4-training-v1')
    check('lineage_parent_is_zero_update_initialization',
          bundle['lineage'].get('parent_training_updates') == 0)
    check('explicit_optimizer_reset', bundle['lineage'].get('explicit_optimizer_reset') is True)
    check('optimizer_steps_match_checkpoint', bundle.get('optimizer_steps_total') == SAMPLE)
    check('collection_states_8', len(bundle.get('collection_states', {})) == 8)
    check('snapshot_device_cuda', bundle.get('snapshot_device') == 'cuda')
    check('purpose_curriculum_training', bundle.get('purpose') == 'curriculum_training')
    check('no_ability_claim', train_result.get('ability_improvement_claim') is False)

    recruit_adam = train_result.get('recruitment', {}).get('actual_new_parameter_Adam', {})
    out['recruit_bias_before'] = train_result.get('recruit_bias_before')
    out['recruit_bias_after'] = train_result.get('recruit_bias_after')
    out['recruit_bias_delta'] = train_result.get('recruit_bias_delta')
    out['recruit_adam_steps'] = {k: v.get('adam_step') for k, v in recruit_adam.items()}
    check('recruit_adam_parameters_272',
          recruit_adam and all(v.get('adam_step') == SAMPLE for v in recruit_adam.values()))
    check('recruit_bias_moved_off_zero', abs(train_result.get('recruit_bias_delta', 0)) > 0)

    # No second update or hidden optimizer run in this directory.
    update_dirs = sorted(p.name for p in RUN.glob('update-*') if p.is_dir())
    out['update_directories'] = update_dirs
    check('only_update_01_exists', update_dirs == ['update-01'], update_dirs)
    check('batch01_has_no_checkpoint',
          not (RUN01 / 'update-01/update-1.pt').exists())
    b01 = read(RUN01 / 'RESULT.json')
    check('batch01_was_engineering_failure_not_update',
          b01.get('passed') is False and b01.get('error') == "AssertionError('Training failed; preserve the original partial checkpoint/report')")

    init_audit = read(INIT_AUDIT)
    out['initialization_audit_sha256'] = sha(INIT_AUDIT)
    out['initialization_sha256'] = sha(INIT)
    check('initialization_sha_registered', sha(INIT) == INIT_SHA)
    check('initialization_new_adam_empty', init_audit.get('new_Adam_state_empty') is True)
    check('initialization_readback_exact', init_audit.get('readback_exact') is True)

    out['errors'] = errors
    out['passed'] = not errors
    out['native_runs_by_auditor'] = 0
    out['GPU_steps'] = 0
    out['optimizer_steps'] = 0
    out['DEV_read'] = False
    out['finaltest_touched'] = False
    out['limitation'] = ('Single fresh update; 4/8 training terminal outcomes are not an ability estimate. '
                         'The x4 starting-army curriculum is a TRAIN-only intervention, and this audit '
                         'does not establish that learned recruitment caused any outcome.')
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'AUDIT.json').write_text(json.dumps(out, indent=2) + '\n')
    (OUT / 'REPORT.md').write_text(
        '# x4 curriculum training batch-02 audit\n\n'
        f"- Passed checks: **{out['passed']}**\n"
        f"- Update: 1 complete update, {out.get('checkpoint_optimizer_steps_total')} actual Adam steps\n"
        f"- Checkpoint SHA-256: `{out['checkpoint_sha256']}`\n"
        f"- Parent SHA-256: `{out['checkpoint_parent_sha256']}`\n"
        f"- Train terminal outcomes: 4 wins / 4 losses\n"
        f"- Recruit bias: {out['recruit_bias_before']} -> {out['recruit_bias_after']}\n"
        f"- DEV read: {out['DEV_read']}; final test touched: {out['finaltest_touched']}\n\n"
        'Batch-01 and batch-02 request/action payload bytes were compared for all eight cells. '
        'Raw-audit SHA-256 values differ because those JSON files embed run-local paths; the audit '
        'does not misreport that as a behavioral difference.\n\n'
        'This is an integrity/accounting audit of one training update, not evidence of improved '
        'strategic ability. Training wins are not used to claim a model upgrade.\n')
    print(json.dumps({k: v for k, v in out.items() if k != 'errors'}, indent=2))
    if errors:
        print(json.dumps(errors, indent=2))
    return 0 if out['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
