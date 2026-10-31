#!/usr/bin/env python3
"""events-v2 demonstration extraction with quality gates.

Only episodes that passed paired controls may produce Q3 demonstrations:
  * Q3-retaliation-bait: bait policy episodes whose PAIRED cell beat the
    teacher on the FROZEN test split (scenario in {14,15}) — recorded with
    the paired delta that justifies the tier.
  * Q2-ability-verified: episodes where a selected breath/cloud ability
    attack is confirmed by native events (SECONDARY hit actually landed or
    primary damage actually dealt). Legal trajectory, normal end; no claim
    of step-level optimality.
Everything else is excluded. Unknown states are recorded as null; no
synthesized armies/coordinates.
"""
import argparse
import gzip
import json
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load_episode(path):
    with gzip.open(path.with_suffix('.json.gz'), 'rt') as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--bait-tag', default='bait-test-01')
    parser.add_argument('--bait-dev-tag', default='bait-pilot-01')
    parser.add_argument('--out', default=str(HERE / 'demonstrations-v1.jsonl'))
    args = parser.parse_args()

    out_rows = []
    stats = defaultdict(int)

    # ---- Q3: paired-verified bait episodes from the frozen test split
    rows = {}
    for path in sorted((HERE / 'runs' / args.bait_tag).glob('*.json')):
        if path.name in ('manifest.json', 'analysis.json'):
            continue
        rec = json.loads(path.read_text())
        if not rec.get('completed'):
            continue
        rows[path.stem] = rec

    cells = defaultdict(dict)
    for name, rec in rows.items():
        cells[(rec['scenario'], rec['role'], rec['seed'])][rec['policy']] = rec

    q3_episodes = []
    for (sc, role, seed), pols in sorted(cells.items()):
        if 'bait' not in pols or 'teacher' not in pols:
            continue
        b, t = pols['bait'], pols['teacher']
        # Q3 gate (per TACTIC_CURRICULUM_DESIGN): paired benefit AND the
        # predicted mechanism (main-force counter damage DOWN). Loss-only
        # improvement without mechanism is NOT Q3 (see results docs).
        main_b, main_t = None, None
        # mechanism from the paired analyses (recomputed here if available)
        try:
            fixed = json.loads((HERE / 'runs' / args.bait_tag / 'analysis-fixed.json').read_text())
            bykey = {(r['scenario'], r['role'], r['seed'], r['policy']): r for r in fixed['rows']}
            mb = bykey.get((sc, role, seed, 'bait'))
            mt = bykey.get((sc, role, seed, 'teacher'))
            if mb and mt:
                main_b = mb['counter_dmg_to_our_main']
                main_t = mt['counter_dmg_to_our_main']
        except Exception:
            pass
        loss_better = (b['permanent_army_loss_units'] < t['permanent_army_loss_units']
                       or (b['success'] and not t['success']))
        mechanism = (main_b is not None and main_t is not None and main_b < main_t)
        if loss_better and mechanism:
            q3_episodes.append((sc, role, seed, b, t))
            stats['q3_cells'] += 1
        else:
            stats['q3_rejected_no_mechanism'] += 1

    for sc, role, seed, b, t in q3_episodes:
        # pilot file name uses the scenarios.json INDEX: {policy}-{tactic}-{index:02d}-{role}-s{seed}
        cases = json.loads((HERE / 'scenarios.json').read_text())
        index = next(i for i, c in enumerate(cases) if c['id'] == sc)
        name = f'bait-retaliation-bait-{index:02d}-{role}-s{seed}'
        path = HERE / 'runs' / args.bait_tag / f'{name}.json'
        if not path.exists():
            print('WARN missing Q3 episode file:', name)
            continue
        data = load_episode(path)
        for d in data['decisions']:
            out_rows.append(dict(
                quality_tier='Q3-paired-verified',
                tactic_id='retaliation-bait',
                source='events-v2-bait-v1-frozen-test',
                paired_basis=dict(vs='teacher', dloss=b['permanent_army_loss_units'] - t['permanent_army_loss_units'],
                                  dwin=int(b['success']) - int(t['success'])),
                battle_id=d['battle_id'], scenario_seed=d['scenario_seed'],
                actor_side=d['actor_side'],
                observation=d['observation'], legal_action_ids=d['legal_actions'],
                expert_action=d['expert_action'], executed_action=d['executed_action'],
                policy_version=d['expert_version'],
                battle_events=d['battle_events'],
                episode_outcome=dict(success=data['episode']['success'],
                                     our_loss_units=data['episode']['permanent_army_loss_units']),
            ))
            stats['q3_decisions'] += 1

    # ---- Q2: ability-verified decisions from expert episodes (any split)
    for tag in ['cloud-pilot-01', 'dragon-pilot-02']:
        run_dir = HERE / 'runs' / tag
        if not run_dir.exists():
            continue
        for path in sorted(run_dir.glob('expert-*.json')):
            rec = json.loads(path.read_text())
            if not rec.get('completed') or rec['truncated'] or not rec['success']:
                continue
            data = load_episode(path)
            for d in data['decisions']:
                sel = d.get('selected_facts') or {}
                if not sel.get('ability'):
                    continue
                # native confirmation: our ability attack actually landed
                # in this decision's event batch
                confirmed = False
                our_side = d['actor_side']
                for ev in d['battle_events']:
                    if ev['kind'] != 2 or ev.get('attacker_side') != our_side:
                        continue
                    if any(t['damage'] > 0 for t in ev['targets']):
                        confirmed = True
                if not confirmed:
                    continue
                out_rows.append(dict(
                    quality_tier='Q2-ability-verified',
                    tactic_id=rec['tactic_id'],
                    source=f'events-v2-expert-{tag}',
                    paired_basis=None,
                    battle_id=d['battle_id'], scenario_seed=d['scenario_seed'],
                    actor_side=d['actor_side'],
                    observation=d['observation'], legal_action_ids=d['legal_actions'],
                    expert_action=d['expert_action'], executed_action=d['executed_action'],
                    policy_version=d['expert_version'],
                    battle_events=d['battle_events'],
                    episode_outcome=dict(success=rec['success'],
                                         our_loss_units=rec['permanent_army_loss_units']),
                ))
                stats['q2_decisions'] += 1

    with open(args.out, 'w') as f:
        for row in out_rows:
            f.write(json.dumps(row) + '\n')
    print(dict(stats), '->', args.out)


if __name__ == '__main__':
    main()
