#!/usr/bin/env python3
"""Independent raw-evidence audit of the completed 12-game x1/x2/x4 calibration.

Reads only the recorded calibration output and immutable manifest/initialization
files. Does not import the calibration runner and does not run native/GPU work.
"""
import hashlib, json, pathlib, re

CAL = pathlib.Path('/root/heroes3-ai-lab/evaluations/strategic-active-opponent-calibration-20261023-01')
CURR = pathlib.Path('/mnt/g/Heroes3-AI-Lab/experiments/strategic-active-opponent-curriculum-20261023')
MANIFEST_PATH = CURR / 'MAP_MANIFEST.json'
MANIFEST_SHA = '88eae3414ec9d7d7dae9bd8390eb4bf3a6ae5dd59fcb87e807d7d45a51702327'
INIT_SHA = '1510149ef1c2c896e3125e6468e9e58234a8bfc9e4278ad239f9d6840e1c62a1'
INIT_PATH = pathlib.Path('/mnt/g/Heroes3-AI-Lab/experiments/strategic-learned-recruitment-policy-v3/initialization-02/recruitment-initialization.pt')
EPOCH = 'strategic-active-opponent-TRAIN-difficulty-calibration-v1'
CONTRACT = '1f3a9d3c0777e31787df5e8cd2a2af1614d326a04f9b0f85ac0e83c3e42d15a3'
OUT = pathlib.Path('/mnt/g/Heroes3-AI-Lab/experiments/takeover-20261023/independent-evidence-02/calibration-x4-audit-01')
OUT.mkdir(parents=True, exist_ok=False)

def sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()

def load(path):
    return json.loads(pathlib.Path(path).read_text())

def main():
    assert sha(MANIFEST_PATH) == MANIFEST_SHA, 'manifest changed'
    assert sha(INIT_PATH) == INIT_SHA, 'initialization changed'
    init_audit = load(INIT_PATH.parent / 'AUDIT.json')
    assert init_audit['initialization_sha256'] == INIT_SHA
    assert init_audit['new_Adam_state_empty'] and init_audit['readback_exact']
    manifest = load(MANIFEST_PATH)
    assert manifest['passed'] is True and manifest['native_runs'] == 0 and manifest['GPU_steps'] == 0
    assert manifest['shared_runtime_maps_written'] is False
    variants = {entry['map']: entry for entry in manifest['variants']}
    assert len(variants) == 12
    result_path = CAL / 'RESULT.json'
    result = load(result_path)
    assert result['passed'] is True
    assert result['TRAIN_only'] is True and result['DEV_read'] is False
    assert result['finaltest_touched'] is False
    assert result['training_samples'] == 0 and result['optimizer_steps'] == 0
    assert len(result['results']) == 12
    cells_on_disk = sorted(path.name for path in CAL.glob('cell-*'))
    assert cells_on_disk == [f'cell-{i:02d}' for i in range(12)], 'unexpected cell set'
    rows = []
    for index, registered in enumerate(result['results']):
        cell = CAL / f'cell-{index:02d}'
        job = registered['job']
        variant = variants[job['map']]
        assert variant['source_map'] == job['source_map']
        assert variant['owned_player'] == job['player']
        assert variant['multiplier'] == job['multiplier']
        assert sha(variant['path']) == variant['sha256']
        expected_seed = 2026104300 + 2 * (0 if job['source_map'] == 'takeover-v2-train-01-mines' else 1) + job['player']
        assert job['seed'] == expected_seed, 'paired seed differs'
        assert job['opponent'] == 'Nullkiller2'
        audit = load(cell / 'raw-audit/AUDIT.json')
        plan = load(cell / 'native/PLAN.json')
        execution = load(cell / 'native/EXECUTION.json')
        for obj in (audit, plan, execution):
            assert obj['pipeline_epoch'] == EPOCH
            assert obj['TRAIN_only'] is True and obj['curriculum_calibration_only'] is True
            assert obj['contract_sha256'] == CONTRACT
            assert obj['threat_replan'] == 'off'
        assert sha(cell / 'raw-audit/AUDIT.json') == registered['audit_sha256']
        assert audit['passed'] is True
        for key in ('whole_game_valid', 'native_game_completed', 'transport_drained',
                    'full_state_recruitment_verified', 'free_transfer_verified',
                    'compiled_native_epoch_proven', 'event_contract_valid'):
            assert audit[key] is True, (index, key)
        assert audit['contract_errors'] == []
        assert audit['owned_player'] == job['player']
        assert audit['winner'] in ('red', 'blue')
        assert audit['native_runs_by_auditor'] == 0 and audit['gpu_runs'] == 0
        assert audit['optimizer_steps'] == 0
        assert audit['counts']['policy_recruits'] > 0
        assert audit['actual_decisions_checked'] == audit['counts']['new_policy_decisions']
        assert audit['actual_recruits_checked'] == audit['counts']['policy_recruits']
        assert plan['map'] == job['map']
        assert plan['calibration_variant']['source_map'] == job['source_map']
        assert plan['owned_player'] == job['player'] and plan['opponent'] == job['opponent']
        assert plan['seed'] == job['seed'] and plan['logical_update'] == 0
        assert plan['checkpoint'] == str(INIT_PATH)
        assert plan['sampling'] == 'CPU argmax'
        assert plan['calibration_variant']['sha256'] == variant['sha256']
        assert plan['calibration_variant']['modified_army'] == variant['modified_army']
        assert execution['game_completed'] is True
        assert execution['transport_drained'] is True
        assert execution['input_sha_unchanged'] is True
        assert execution['client_exit'] == 0
        assert execution['thread_server_verification']['passed'] is True
        ready = load(cell / 'native/agent/broker-ready.json')
        assert ready['mode'] == 'new-policy' and ready['device'] == 'cpu'
        assert ready['model_sha256'] == INIT_SHA
        assert ready['optimizer_steps'] == 0
        for name, digest in audit['raw_sha256'].items():
            assert sha(cell / 'native' / name) == digest, (index, name)
        assert sha(cell / 'native/agent/request-00000001.json') == registered['initial_request_sha256']
        # Exactly one completed game_over event in the actual raw typed mirror.
        game_over = 0
        for line in (cell / 'native/typed.jsonl').read_text().splitlines():
            event = json.loads(line)
            if event.get('event') == 'game_over':
                game_over += 1
                assert event.get('completed') is True
        assert game_over == 1
        win = audit['winner'] == ('red' if job['player'] == 0 else 'blue')
        assert win is registered['win']
        assert all('dev-' not in str(value) for value in job.values())
        rows.append(dict(cell=index, map=job['map'], source_map=job['source_map'],
                         multiplier=job['multiplier'], player=job['player'],
                         seed=job['seed'], winner=audit['winner'], win=win,
                         decisions=audit['counts']['new_policy_decisions'],
                         recruits=audit['counts']['policy_recruits'],
                         builds=audit['counts']['policy_builds'],
                         audit_sha256=registered['audit_sha256'],
                         plan_sha256=sha(cell / 'native/PLAN.json')))
    wins = {str(m): sum(row['win'] for row in rows if row['multiplier'] == m) for m in (1, 2, 4)}
    selected = next((m for m in (2, 4) if wins[str(m)] >= 2), None)
    assert selected == 4
    assert result['selection']['selected_multiplier'] == selected
    assert result['selection']['wins_by_multiplier'] == wins
    assert wins == {'1': 0, '2': 1, '4': 2}
    report = dict(passed=True, scope='raw-evidence audit of a TRAIN-only difficulty calibration',
                  calibration_result=str(result_path), calibration_result_sha256=sha(result_path),
                  manifest=str(MANIFEST_PATH), manifest_sha256=MANIFEST_SHA,
                  initialization=str(INIT_PATH), initialization_sha256=INIT_SHA,
                  cells_reviewed=len(rows), unique_native_games=12,
                  wins_by_multiplier=wins, selected_multiplier=selected,
                  all_cell_audits_match_result=True, all_raw_hashes_match_audits=True,
                  all_game_overs_unique_and_complete=True,
                  all_inputs_unchanged=True, zero_GPU_zero_optimizer_zero_training_rows=True,
                  unexpected_cells=0, finaltest_touched=False, DEV_read=False,
                  native_runs_by_auditor=0, GPU_steps=0, optimizer_steps=0,
                  limitation='TRAIN-only selection; 2/4 is a small paired difficulty calibration, not an independent win-rate estimate or expert evidence.',
                  cells=rows)
    (OUT / 'AUDIT.json').write_text(json.dumps(report, indent=2) + '\n')
    (OUT / 'REPORT.md').write_text('\n'.join([
        '# Independent calibration raw audit',
        '',
        f"All 12 registered cells were read from disk and checked against `RESULT.json`, `MAP_MANIFEST.json`, the frozen initialization and each cell's native plan/execution/raw audit.",
        '',
        f"- Wins: x1 `{wins['1']}/4`, x2 `{wins['2']}/4`, x4 `{wins['4']}/4`",
        f"- Selected multiplier: `{selected}`",
        '- Every audit SHA, per-file raw SHA and single completed `game_over` matched.',
        '- Zero GPU runs, zero optimizer steps, zero training rows, no DEV/final-test path.',
        '',
        'This is TRAIN-only difficulty selection evidence, not an independent win-rate claim or expert demonstration.',
        '']))
    print(json.dumps({key: value for key, value in report.items() if key != 'cells'}, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
