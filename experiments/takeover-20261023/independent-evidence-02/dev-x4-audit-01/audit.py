"""Independent raw-evidence audit of the x4-training four-arm paired DEV run.

This script reads preserved evidence only.  It starts no native game, no GPU
work and no optimizer.  Wins are reported as small DEV counts, not a population
win rate or an ability guarantee.
"""
import hashlib
import json
from collections import Counter
from pathlib import Path

RUN = Path('/root/heroes3-ai-lab/evaluations/strategic-learned-recruitment-curriculum-x4-dev-20261023-01')
RUN_V2 = Path('/mnt/g/Heroes3-AI-Lab/experiments/strategic-learned-recruitment-run-v2')
OUT = Path('/mnt/g/Heroes3-AI-Lab/experiments/takeover-20261023/independent-evidence-02/dev-x4-audit-01')
EXPECTED_MODELS = {
    'minus4_initial': 'b9ede0d158d113eff42d58cb8a844277b42e8a0820122d985299dfcf9cdb7b79',
    'minus4_updated': '85c5fdda76e1d98fcc157f86f08203e7f9db0e1774f5b0f254ad5b20f9b55a9a',
    'zero_initial': '1510149ef1c2c896e3125e6468e9e58234a8bfc9e4278ad239f9d6840e1c62a1',
    'zero_updated': '6a0bd8f7c800157258e77cdbdece7fdb4da183ae2a86c103ed050fb6af6e876e',
}
EXPECTED_ARMS = ['minus4_initial', 'minus4_updated', 'zero_initial', 'zero_updated']
EXPECTED_JOBS = [
    dict(index=i, map=m, opponent=o, player=p, seed=2026104200 + i)
    for i, (m, o, p) in enumerate(
        (m, o, p)
        for m in ('takeover-v2-dev-01-river', 'takeover-v2-dev-02-reserves')
        for o in ('EmptyAI', 'Nullkiller2')
        for p in (0, 1)
    )
]


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

    plan = read(RUN / 'PLAN.json')
    result = read(RUN / 'RESULT.json')
    pairs = read(RUN / 'PROGRESS.json')['pairs']
    out['scope'] = 'independent raw-evidence audit of eight paired DEV cells, four arms, CPU argmax; no ability guarantee'
    out['run'] = str(RUN)
    out['plan_sha256'] = sha(RUN / 'PLAN.json')
    out['result_sha256'] = sha(RUN / 'RESULT.json')
    out['progress_sha256'] = sha(RUN / 'PROGRESS.json')
    out['training_samples'] = result.get('training_samples')
    out['optimizer_steps'] = result.get('optimizer_steps')
    out['finaltest_touched'] = result.get('finaltest_touched')

    check('result_passed', result.get('passed') is True, result.get('error'))
    check('training_samples_zero', result.get('training_samples') == 0)
    check('optimizer_steps_zero', result.get('optimizer_steps') == 0)
    check('finaltest_not_touched', result.get('finaltest_touched') is False)
    check('ability_claim_false', result.get('ability_improvement_claim') is False)
    check('eight_pairs', len(pairs) == 8)
    check('pair_indexes_exact', [p.get('index') for p in pairs] == list(range(8)))
    check('jobs_exact', [dict(index=p['index'], **{k: p['job'][k] for k in ('map', 'opponent', 'player', 'seed')}) for p in pairs] == EXPECTED_JOBS)
    check('plan_eight_jobs', len(plan.get('jobs', [])) == 8)
    check('plan_model_shas_exact', plan.get('model_sha256') == EXPECTED_MODELS, plan.get('model_sha256'))
    check('plan_sampling_cpu_argmax', plan.get('sampling') == 'CPU argmax')
    check('plan_no_training_or_optimizer', plan.get('training_samples') == 0 and plan.get('optimizer_steps') == 0)
    check('plan_finaltest_false', plan.get('finaltest_touched') is False)

    # Inputs were frozen before the first arm and must still match afterwards.
    input_bad = [p for p, h in plan['input_sha256'].items() if not Path(p).is_file() or sha(p) != h]
    out['frozen_inputs_checked'] = len(plan['input_sha256'])
    out['frozen_input_mismatches'] = input_bad
    check('frozen_inputs_all_match', not input_bad)

    arm_counts = {a: Counter() for a in EXPECTED_ARMS}
    arm_wins = {a: 0 for a in EXPECTED_ARMS}
    arm_details = {a: [] for a in EXPECTED_ARMS}
    initial_equal = {}
    all_native_runs = 0
    all_optimizer_zero = True
    all_gpu_zero = True
    all_native_runs_by_auditor_zero = True
    all_thread_server = True
    all_game_over_unique = True
    all_links_ok = True
    all_selected_valid = True
    all_initial_request_same = True
    all_sampling_seeds_paired = True
    all_drain = True
    raw_ok = True
    raw_count = 0
    recruit_totals = {a: 0 for a in EXPECTED_ARMS}
    model_paths = {}

    for pair in pairs:
        i = pair['index']
        job = pair['job']
        expected_arm_audit = {}
        for arm in EXPECTED_ARMS:
            root = RUN / f'pair-{i:02d}' / arm
            native = root / 'native'
            raw = root / 'raw-audit/AUDIT.json'
            audit = read(raw)
            execution = read(native / 'EXECUTION.json')
            native_plan = read(native / 'PLAN.json')
            ready = read(native / 'agent/broker-ready.json')
            all_native_runs += 1
            expected_arm_audit[arm] = sha(raw)

            all_optimizer_zero &= execution.get('optimizer_steps') == 0 and audit.get('optimizer_steps') == 0
            all_gpu_zero &= audit.get('gpu_runs') == 0
            all_native_runs_by_auditor_zero &= audit.get('native_runs_by_auditor') == 0
            all_thread_server &= execution.get('thread_server_verification', {}).get('passed') is True
            all_drain &= audit.get('drain', {}).get('passed') is True
            check(f'p{i:02d}_{arm}_raw_audit_sha',
                  sha(raw) == pair['arms'][arm]['audit_sha256'],
                  (sha(raw), pair['arms'][arm]['audit_sha256']))
            check(f'p{i:02d}_{arm}_audit_passed',
                  audit.get('passed') is True and audit.get('whole_game_valid') is True
                  and audit.get('native_game_completed') is True and audit.get('transport_drained') is True,
                  audit.get('passed'))
            check(f'p{i:02d}_{arm}_recruitment_transfer_epoch',
                  audit.get('full_state_recruitment_verified') is True
                  and audit.get('free_transfer_verified') is True
                  and audit.get('catalog_runtime_bound') is True
                  and audit.get('compiled_native_epoch_proven') is True
                  and audit.get('event_contract_valid') is True
                  and not audit.get('contract_errors'),
                  audit.get('contract_errors'))
            check(f'p{i:02d}_{arm}_execution_terminal',
                  execution.get('game_completed') is True and execution.get('transport_drained') is True
                  and execution.get('input_sha_unchanged') is True and execution.get('client_exit') == 0
                  and execution.get('broker_exit') == 0,
                  {k: execution.get(k) for k in ('game_completed', 'transport_drained', 'input_sha_unchanged', 'client_exit', 'broker_exit')})
            checkpoint = Path(native_plan.get('checkpoint') or '')
            model_paths.setdefault(arm, checkpoint)
            check(f'p{i:02d}_{arm}_broker_cpu_zero',
                  checkpoint.is_file() and sha(checkpoint) == EXPECTED_MODELS[arm]
                  and ready.get('model_sha256') == EXPECTED_MODELS[arm]
                  and ready.get('device') == 'cpu' and ready.get('optimizer_steps') == 0,
                  (native_plan.get('checkpoint'), ready.get('model_sha256'), ready.get('device')))
            expected_epoch = 'minus-four-control' if arm.startswith('minus4_') else 'prior-zero'
            check(f'p{i:02d}_{arm}_arm_epoch',
                  native_plan.get('policy_epoch') == expected_epoch
                  and native_plan.get('sampling') == 'CPU argmax'
                  and native_plan.get('training_samples') == 0
                  and native_plan.get('optimizer_steps') == 0,
                  native_plan.get('policy_epoch'))
            check(f'p{i:02d}_{arm}_native_job',
                  native_plan.get('map') == job['map'] and native_plan.get('owned_player') == job['player']
                  and native_plan.get('opponent') == job['opponent'] and native_plan.get('seed') == job['seed']
                  and native_plan.get('logical_update') == 0)
            less = [p for p, h in native_plan['hashes'].items() if not Path(p).is_file() or sha(p) != h]
            check(f'p{i:02d}_{arm}_native_inputs_unchanged', not less, less[:3])

            # All requests/actions must be present, linked, and selected from the
            # actual candidate list.  automatic_end_turns are not broker choices.
            agent = native / 'agent'
            reqs = sorted(agent.glob('request-*.json'))
            acts = sorted(agent.glob('action-*.json'))
            lines = [json.loads(x) for x in (agent / 'typed-broker.jsonl').read_text().splitlines() if x.strip()]
            check(f'p{i:02d}_{arm}_request_action_line_counts',
                  len(reqs) == len(acts) == len(lines) == audit['actual_decisions_checked'],
                  (len(reqs), len(acts), len(lines), audit['actual_decisions_checked']))
            ops = Counter()
            local_recruits = 0
            local_recruit_quantity = 0
            request_ids = []
            for req_path, act_path, row in zip(reqs, acts, lines):
                req = read(req_path)
                act = read(act_path)
                request_ids.append(req['request_id'])
                all_links_ok &= act.get('request_sha256') == sha(req_path)
                chosen = req['candidates'][act['selected_index']] if isinstance(act.get('selected_index'), int) and 0 <= act['selected_index'] < len(req['candidates']) else None
                all_selected_valid &= chosen is not None and chosen.get('op') == act.get('op')
                all_links_ok &= row.get('request') == req and row.get('response') == act
                ops[act.get('op')] += 1
                if act.get('op') == 'recruit' and chosen is not None:
                    local_recruits += 1
                    local_recruit_quantity += int(chosen.get('amount', 0))
                    recruit_totals[arm] += int(chosen.get('amount', 0))
            check(f'p{i:02d}_{arm}_request_ids_unique', len(set(request_ids)) == len(request_ids) and request_ids == list(range(1, len(request_ids) + 1)))
            check(f'p{i:02d}_{arm}_audit_counts_match_broker',
                  ops['move'] == audit['counts']['new_policy_decisions'] - ops['build'] - ops['recruit'] - ops['end_turn']
                  and ops['build'] == audit['counts']['policy_builds']
                  and ops['recruit'] == audit['counts']['policy_recruits'] == audit['actual_recruits_checked'],
                  (dict(ops), audit.get('counts')))
            arm_counts[arm].update(ops)
            won = audit.get('winner') == ('red' if job['player'] == 0 else 'blue')
            arm_wins[arm] += int(won)
            observed_recruit_days = []
            for request_path, action_path in zip(reqs, acts):
                action = read(action_path)
                if action['op'] == 'recruit':
                    observed_recruit_days.append(read(request_path)['day'])
            check(f'p{i:02d}_{arm}_eval_win_matches_raw',
                  pair['arms'][arm]['win'] is won
                  and pair['arms'][arm]['counts'] == audit['counts']
                  and pair['arms'][arm]['recruited_amount'] == local_recruit_quantity
                  and pair['arms'][arm]['recruitment_days'] == observed_recruit_days,
                  (pair['arms'][arm]['win'], won, pair['arms'][arm]['recruited_amount'], local_recruit_quantity, local_recruits))
            arm_details[arm].append(dict(pair=i, map=job['map'], player=job['player'], opponent=job['opponent'],
                                         seed=job['seed'], win=won, winner=audit.get('winner'),
                                         decisions=len(acts), moves=ops['move'], builds=ops['build'],
                                         recruits=ops['recruit'], end_turns=ops['end_turn'],
                                         recruited_amount=local_recruit_quantity,
                                         automatic_end_turns=audit['counts'].get('automatic_end_turns'),
                                         audit_sha256=sha(raw)))

            # Verify all raw files plus the experiment-shared source hashes.
            raw_root = Path(audit['raw'])
            for rel, digest in audit.get('raw_sha256', {}).items():
                raw_count += 1
                raw_ok &= (raw_root / rel).is_file() and sha(raw_root / rel) == digest
            for path, digest in audit.get('source_sha256', {}).items():
                if path.startswith('/mnt/g/Heroes3-AI-Lab/'):
                    raw_ok &= Path(path).is_file() and sha(path) == digest

        # Paired inputs: same initial observation and same native seed material.
        req_hashes = {sha(RUN / f'pair-{i:02d}' / arm / 'native/agent/request-00000001.json') for arm in EXPECTED_ARMS}
        initial_equal[i] = len(req_hashes) == 1
        all_initial_request_same &= initial_equal[i]
        seeds = {read(RUN / f'pair-{i:02d}' / arm / 'native/PLAN.json')['sampling_seed'] for arm in EXPECTED_ARMS}
        all_sampling_seeds_paired &= len(seeds) == 1
        check(f'p{i:02d}_initial_request_same',
              pair.get('initial_request_equal_all_four') is True and len(req_hashes) == 1)
        check(f'p{i:02d}_sampling_seed_paired', len(seeds) == 1)

        # Each cell must contain exactly one normal terminal.
        terminals = []
        for arm in EXPECTED_ARMS:
            typed = RUN / f'pair-{i:02d}' / arm / 'native/typed.jsonl'
            events = [json.loads(x) for x in typed.read_text().splitlines() if x.strip()]
            terminals.append(sum(1 for e in events if e.get('event') == 'game_over' and e.get('completed') is True))
        all_game_over_unique &= terminals == [1, 1, 1, 1]
        check(f'p{i:02d}_one_normal_terminal_per_arm', terminals == [1, 1, 1, 1], terminals)

    out['native_games'] = all_native_runs
    out['unique_paired_cells'] = 8
    check('four_model_files_match_plan_shas',
          set(model_paths) == set(EXPECTED_ARMS)
          and all(model_paths[a].is_file() and sha(model_paths[a]) == EXPECTED_MODELS[a] for a in EXPECTED_ARMS),
          {a: str(p) for a, p in model_paths.items()})
    out['arm_wins'] = arm_wins
    out['arm_counts'] = {a: dict(c) for a, c in arm_counts.items()}
    out['recruited_amounts'] = recruit_totals
    out['arm_details'] = arm_details
    out['initial_request_equal_all_pairs'] = initial_equal
    out['all_initial_requests_equal_all_four'] = all_initial_request_same
    out['all_sampling_seeds_paired'] = all_sampling_seeds_paired
    out['raw_files_hashed'] = raw_count
    out['all_raw_and_shared_hashes_match'] = raw_ok
    out['all_request_response_links_and_selections_valid'] = all_links_ok and all_selected_valid
    out['all_gpu_runs_zero'] = all_gpu_zero
    out['all_optimizer_steps_zero'] = all_optimizer_zero
    out['all_native_runs_by_auditor_zero'] = all_native_runs_by_auditor_zero
    out['all_thread_server_gates_passed'] = all_thread_server
    out['all_terminal_drains_passed'] = all_drain
    out['all_one_normal_terminal_per_arm'] = all_game_over_unique
    check('all_32_raw_files_and_shared_sources_hash', raw_ok)
    check('all_request_response_selections_valid', all_links_ok and all_selected_valid)
    check('all_32_gpu_zero', all_gpu_zero)
    check('all_32_optimizer_zero', all_optimizer_zero)
    check('all_32_auditor_native_runs_zero', all_native_runs_by_auditor_zero)
    check('all_32_thread_server_gates', all_thread_server)
    check('all_32_terminal_drains', all_drain)
    check('all_32_one_normal_terminal', all_game_over_unique)
    check('result_arm_wins_match_raw', result.get('arm_wins') == arm_wins, (result.get('arm_wins'), arm_wins))
    check('result_net_counts_match_raw',
          result.get('zero_prior_update_net_wins') == arm_wins['zero_updated'] - arm_wins['zero_initial']
          and result.get('minus4_update_net_wins') == arm_wins['minus4_updated'] - arm_wins['minus4_initial'])

    out['errors'] = errors
    out['passed'] = not errors
    out['limitation'] = ('Eight historically seen DEV cells, 32 runs total, CPU argmax. Arm wins are paired small-sample '
                         'counts and are not a population win rate. Four arms share a native seed within each cell, but '
                         'the policies can diverge after the first differing action; this is not hidden-world determinism. '
                         'No DEV labels enter training, and no promotion is justified by this audit alone.')
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'AUDIT.json').write_text(json.dumps(out, indent=2) + '\n')
    lines = [
        '# Four-arm x4-trained recruitment DEV audit', '',
        f"- Passed checks: **{out['passed']}**",
        f"- Native games audited: {out['native_games']} ({out['unique_paired_cells']} paired cells x 4 arms)",
        f"- Wins: {json.dumps(arm_wins, sort_keys=True)}",
        f"- Zero-prior update net wins: {arm_wins['zero_updated'] - arm_wins['zero_initial']}",
        f"- Minus-four update net wins: {arm_wins['minus4_updated'] - arm_wins['minus4_initial']}",
        f"- Training samples / optimizer steps: {out['training_samples']} / {out['optimizer_steps']}",
        f"- Final test touched: {out['finaltest_touched']}",
        f"- Initial requests identical across all four arms: {out['all_initial_requests_equal_all_four']}",
        f"- Raw files hashed: {out['raw_files_hashed']}", '',
        '## Arm totals', '',
        '| arm | wins | moves | builds | recruits | creatures recruited |',
        '|---|---:|---:|---:|---:|---:|',
    ]
    for arm in EXPECTED_ARMS:
        c = arm_counts[arm]
        lines.append(f"| {arm} | {arm_wins[arm]} | {c['move']} | {c['build']} | {c['recruit']} | {recruit_totals[arm]} |")
    lines += ['', 'These are paired DEV counts, not an ability estimate or a promotion decision. '
              'Raw terminal, recruitment, build and transfer evidence was retained; failures would be reported separately.',
              '']
    (OUT / 'REPORT.md').write_text('\n'.join(lines))
    print(json.dumps({k: v for k, v in out.items() if k not in ('errors', 'arm_details')}, indent=2))
    if errors:
        print(json.dumps(errors, indent=2))
    return 0 if out['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
