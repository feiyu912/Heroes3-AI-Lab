"""Compare the two four-arm DEV runs that differ only in the updated zero-prior checkpoint.

The three unchanged arms use identical checkpoints, maps, seeds and roles.  If
their raw action streams are byte-identical, the zero_updated comparison is a
cross-run paired comparison of two one-update training curricula, not a change
in the evaluation harness.
"""
import hashlib
import json
from pathlib import Path

CURRENT = Path('/root/heroes3-ai-lab/evaluations/strategic-learned-recruitment-curriculum-x4-dev-20261023-01')
PRIOR = Path('/root/heroes3-ai-lab/evaluations/strategic-learned-recruitment-prior-zero-four-arm-dev-20261023-01')
PRIOR_AUDIT = Path('/mnt/g/Heroes3-AI-Lab/experiments/takeover-20261023/independent-evidence-01/priorzero-dev-actual-01/AUDIT.json')
CURRENT_AUDIT = Path('/mnt/g/Heroes3-AI-Lab/experiments/takeover-20261023/independent-evidence-02/dev-x4-full-replay-01/AUDIT.json')
OUT = Path('/mnt/g/Heroes3-AI-Lab/experiments/takeover-20261023/independent-evidence-02/dev-x4-audit-01')
UNCHANGED = ['minus4_initial', 'minus4_updated', 'zero_initial']


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def byte_stream(root):
    out = {}
    agent = root / 'native/agent'
    for kind in ('request', 'action'):
        out[kind] = [(p.name, p.read_bytes()) for p in sorted(agent.glob(kind + '-*.json'))]
    out['typed'] = (agent / 'typed-broker.jsonl').read_bytes()
    return out


def wins_by(result, arm, key):
    values = {}
    for pair in result['pairs']:
        job = pair['job']
        values.setdefault(job[key], [0, 0])
        values[job[key]][0] += int(pair['arms'][arm]['win'])
        values[job[key]][1] += 1
    return {k: dict(wins=v[0], games=v[1]) for k, v in values.items()}


def main():
    current = read(CURRENT / 'RESULT.json')
    prior = read(PRIOR / 'RESULT.json')
    current_plan = read(CURRENT / 'PLAN.json')
    prior_plan = read(PRIOR / 'PLAN.json')
    prior_audit = read(PRIOR_AUDIT)
    current_audit = read(CURRENT_AUDIT)
    assert current['passed'] and prior['passed']
    assert current_audit['passed'] and prior_audit['passed']
    assert [dict(index=p['index'], **p['job']) for p in current['pairs']] == [dict(index=p['index'], **p['job']) for p in prior['pairs']]
    assert all(current['pairs'][i]['job'][k] == prior['pairs'][i]['job'][k] for i in range(8) for k in ('map', 'opponent', 'player', 'seed'))
    assert all(current_plan['model_sha256'][a] == prior_plan['model_sha256'][a] for a in UNCHANGED)
    assert current_plan['model_sha256']['zero_updated'] == '6a0bd8f7c800157258e77cdbdece7fdb4da183ae2a86c103ed050fb6af6e876e'
    assert prior_plan['model_sha256']['zero_updated'] == '1d1618bf6dd535e1e7d158ed6d194848eeaba4e8260e9e1cb5467f0db27cc81c'

    unchanged = {}
    for arm in UNCHANGED:
        bad = []
        for i in range(8):
            a = byte_stream(PRIOR / f'pair-{i:02d}' / arm)
            b = byte_stream(CURRENT / f'pair-{i:02d}' / arm)
            if a.keys() != b.keys():
                bad.append([i, arm, 'keys'])
                continue
            for kind in ('request', 'action'):
                if [n for n, _ in a[kind]] != [n for n, _ in b[kind]]:
                    bad.append([i, arm, kind, 'names'])
                elif any(x[1] != y[1] for x, y in zip(a[kind], b[kind])):
                    bad.append([i, arm, kind, 'bytes'])
            if a['typed'] != b['typed']:
                bad.append([i, arm, 'typed', 'bytes'])
        unchanged[arm] = dict(byte_identical=not bad, mismatches=bad)
    assert all(x['byte_identical'] for x in unchanged.values()), unchanged

    flips = []
    for i in range(8):
        a = prior['pairs'][i]['arms']['zero_updated']['win']
        b = current['pairs'][i]['arms']['zero_updated']['win']
        flips.append(dict(pair=i, job=current['pairs'][i]['job'], prior_zero_updated_win=a,
                          current_x4_zero_updated_win=b, changed=a != b,
                          direction=('gain' if b and not a else 'loss' if a and not b else 'unchanged')))
    within_flips = []
    for i in range(8):
        a = current['pairs'][i]['arms']['zero_initial']['win']
        b = current['pairs'][i]['arms']['zero_updated']['win']
        within_flips.append(dict(pair=i, job=current['pairs'][i]['job'], zero_initial_win=a,
                                 zero_updated_win=b, changed=a != b,
                                 direction=('gain' if b and not a else 'loss' if a and not b else 'unchanged')))

    def summary(audit, arm):
        s = audit['arm_summary'][arm]
        return dict(wins=s['wins'], rows=s.get('rows', s.get('CPU_full_proposals_recomputed')),
                    recruits=s['recruits'], recruited_quantity=s['recruited_quantity'],
                    free_transfers=s['free_transfers'], builds=s['builds'],
                    income_builds=s.get('income_builds'), town_moves=s.get('town_moves'))

    def pair_counts(audit, arm):
        total = {}
        for pair in audit['pairs']:
            for key, value in pair['arms'][arm]['counts'].items():
                total[key] = total.get(key, 0) + value
        return total

    prior_zero = summary(prior_audit, 'zero_updated')
    cur_zero = summary(current_audit, 'zero_updated')
    # Current audit also has exact broker counts; use its action totals for a
    # direct comparable count table alongside the prior independent audit.
    cur_counts = pair_counts(current_audit, 'zero_updated')
    prior_counts = pair_counts(prior_audit, 'zero_updated')
    out = dict(
        scope='paired cross-run comparison; unchanged arms reproduced byte-for-byte, zero_updated changed',
        current_run=str(CURRENT), prior_run=str(PRIOR),
        current_result_sha256=sha(CURRENT / 'RESULT.json'), prior_result_sha256=sha(PRIOR / 'RESULT.json'),
        current_audit_sha256=sha(CURRENT_AUDIT), prior_audit_sha256=sha(PRIOR_AUDIT),
        unchanged_arms=unchanged,
        all_unchanged_arms_byte_identical=all(x['byte_identical'] for x in unchanged.values()),
        prior_zero_updated_model='1d1618bf6dd535e1e7d158ed6d194848eeaba4e8260e9e1cb5467f0db27cc81c',
        current_x4_zero_updated_model=current_plan['model_sha256']['zero_updated'],
        current_arm_wins=current['arm_wins'], prior_arm_wins=prior['arm_wins'],
        current_wins_by_opponent={a: wins_by(current, a, 'opponent') for a in current['arm_wins']},
        current_wins_by_role={a: wins_by(current, a, 'player') for a in current['arm_wins']},
        prior_zero_updated_by_opponent=wins_by(prior, 'zero_updated', 'opponent'),
        current_zero_updated_by_opponent=wins_by(current, 'zero_updated', 'opponent'),
        prior_zero_updated=prior_zero, current_x4_zero_updated=cur_zero,
        current_zero_updated_counts=cur_counts,
        prior_zero_updated_counts=prior_counts,
        cross_run_zero_updated_flips=flips,
        within_current_zero_update_flips=within_flips,
        cross_run_zero_updated_net_wins=sum(x['current_x4_zero_updated_win'] - x['prior_zero_updated_win'] for x in flips),
        within_current_zero_update_net_wins=sum(x['zero_updated_win'] - x['zero_initial_win'] for x in within_flips),
        changed_factor='TRAIN-only owned-hero starting army x4 during one fresh PPO update; evaluation maps/seeds/models for the other three arms are unchanged',
        limitation=('The two zero_updated checkpoints are each one update from the same initialization but were trained on different '
                    'curriculum trajectories and have different Adam-step counts (208 vs 272), so their difference is not an equal-Adam '
                    'causal estimate. The three control arms are byte-identical, which rules out evaluator drift for this comparison. '
                    'Eight paired DEV cells are a small developmental sample, not a population win rate.'),
        training_samples=0, optimizer_steps=0, finaltest_touched=False, ability_improvement_claim=False,
    )
    (OUT / 'CROSS_RUN.json').write_text(json.dumps(out, indent=2) + '\n')
    lines = [
        '# Cross-run DEV comparison', '',
        f"- Unchanged arms byte-identical across the two runs: **{out['all_unchanged_arms_byte_identical']}**",
        f"- Prior zero-updated wins: {prior['arm_wins']['zero_updated']}/8; x4 zero-updated wins: {current['arm_wins']['zero_updated']}/8",
        f"- Cross-run zero-updated net wins: {out['cross_run_zero_updated_net_wins']}",
        f"- Within-current zero-update net wins: {out['within_current_zero_update_net_wins']}",
        f"- Prior zero-updated recruits/quantity: {prior_zero['recruits']}/{prior_zero['recruited_quantity']}",
        f"- x4 zero-updated recruits/quantity: {cur_zero['recruits']}/{cur_zero['recruited_quantity']}", '',
        '## Per-cell zero-updated outcomes', '',
        '| pair | map | opponent | role | prior | x4 | change |',
        '|---:|---|---|---:|---:|---:|---|',
    ]
    for x in flips:
        lines.append(f"| {x['pair']} | {x['job']['map']} | {x['job']['opponent']} | {x['job']['player']} | "
                     f"{int(x['prior_zero_updated_win'])} | {int(x['current_x4_zero_updated_win'])} | {x['direction']} |")
    lines += ['', 'The unchanged control arms being byte-identical makes evaluator drift an unlikely explanation for the '
              'zero-updated difference. It does not make the two training runs equal-Adam or establish a population effect.', '']
    (OUT / 'CROSS_RUN.md').write_text('\n'.join(lines))
    print(json.dumps({k: v for k, v in out.items() if k not in ('cross_run_zero_updated_flips', 'within_current_zero_update_flips')}, indent=2))


if __name__ == '__main__':
    main()
