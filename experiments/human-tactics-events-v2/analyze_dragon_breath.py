#!/usr/bin/env python3
"""events-v2 dragon-breath tactic analysis from native events.

Per episode:
  * identify breather units via the recorded Unit node flags
    (HAS_TWO_HEX_ATTACK_BREATH) and graph node indices carried by events
  * breath attacks: primary/secondary targets, enemy damage, friendly fire,
    kills, whether the breath was executed as a COUNTER attack
  * damage taken by our breathers (esp. by counter attacks)
  * terminal permanent losses (both sides)
Paired cells compare policies on identical (scenario, role, seed) with the
same native BattleAI opponent. Small-n findings are reported as-is; nothing
is extrapolated.
"""
import argparse
import gzip
import json
from collections import defaultdict
from pathlib import Path

AFLAG = {1: 'SHOT', 2: 'COUNTER', 64: 'SPELL_LIKE'}


def unit_flags(obs):
    """node_index -> dict(is_enemy, breath, death_cloud) from recorded nodes."""
    out = {}
    for i, row in enumerate(obs['nodes']['Unit']):
        # decode via gym namedtuple: last fields are flags (RAW 0/1)
        out[i] = dict(
            is_enemy=bool(row[-3] if False else None),  # placeholder, replaced below
        )
    return out


def analyze_episode(path, gz):
    with gzip.open(gz, 'rt') as f:
        data = json.load(f)
    ep = data['episode']
    our_side = 1 if ep['role'] == 'defender' else 0

    from vcmi_gym.envs.v15.vcmi_env import Unit  # only for decode context

    # Map node index -> flags PER DECISION. Unit node indices are NOT stable
    # across decisions (units die and later nodes shift); every event's
    # *_node fields index into the graph of the decision that carries it.
    import numpy as np
    flags_by_decision = []
    for d in data['decisions']:
        arr = np.asarray(d['observation']['nodes']['Unit'], dtype=np.float32)
        m = {}
        for i in range(arr.shape[0]):
            u = Unit.decode_one(arr[i])
            m[i] = dict(is_enemy=bool(u.IS_ENEMY),
                        breath=bool(u.HAS_TWO_HEX_ATTACK_BREATH),
                        cloud=bool(u.HAS_DEATH_CLOUD))
        flags_by_decision.append(m)

    res = dict(
        our_breath_attacks=0, our_breath_counter=0, our_breath_primary_dmg=0,
        our_breath_primary_kills=0, our_breath_secondary_dmg=0, our_breath_secondary_kills=0,
        our_breath_friendly_dmg=0, our_breath_friendly_kills=0,
        enemy_breath_attacks=0, enemy_breath_counter=0, enemy_breath_primary_dmg=0,
        enemy_breath_secondary_dmg=0, enemy_breath_friendly_dmg=0,
        our_breather_dmg_taken=0, our_breather_kills_taken=0,
        our_breather_dmg_by_counter=0,
        our_cloud_attacks=0, our_cloud_primary_dmg=0, our_cloud_secondary_dmg=0,
        enemy_cloud_attacks=0, enemy_cloud_secondary_dmg=0,
        expert_overrides=0, expert_breath_selected=0,
        counter_differs_from_teacher=0,
    )
    for di, d in enumerate(data['decisions']):
        flags_by_node = flags_by_decision[di]
        q = d.get('quality') or {}
        if q.get('override'):
            res['expert_overrides'] += 1
            if (d.get('selected_facts') or {}).get('ability'):
                res['expert_breath_selected'] += 1
        if d['policy'] == 'counter' and d.get('expert_action') is not None \
                and d['expert_action'] != d.get('quality', {}).get('teacher_action', -999):
            res['counter_differs_from_teacher'] += 1
        for ev in d['battle_events']:
            if ev['kind'] != 2:
                continue
            an = ev.get('attacker_node', -1)
            aflag = flags_by_node.get(an, {})
            by_us = ev.get('attacker_side', -1) == our_side
            is_counter = bool(ev['attack_flags'] & 2)
            breather = bool(aflag.get('breath'))
            cloud = bool(aflag.get('cloud'))
            for t in ev['targets']:
                tf = t['flags']
                sec = bool(tf & 2)
                dmg, killed = t['damage'], t['killed']
                t_side = t.get('defender_side', -1)
                own_side_hit = (t_side == ev.get('attacker_side', -1)) and t_side >= 0
                if breather:
                    key = 'our' if by_us else 'enemy'
                    res[f'{key}_breath_attacks'] += 1
                    if is_counter:
                        res[f'{key}_breath_counter'] += 1
                    if not sec:
                        res[f'{key}_breath_primary_dmg'] += dmg
                        if key == 'our':
                            res['our_breath_primary_kills'] += killed
                    else:
                        if own_side_hit:
                            res[f'{key}_breath_friendly_dmg'] += dmg
                            if key == 'our':
                                res['our_breath_friendly_kills'] += killed
                        else:
                            res[f'{key}_breath_secondary_dmg'] += dmg
                            if key == 'our':
                                res['our_breath_secondary_kills'] += killed
                if cloud:
                    key = 'our' if by_us else 'enemy'
                    res[f'{key}_cloud_attacks'] += 1
                    if sec:
                        res[f'{key}_cloud_secondary_dmg'] += dmg
                    else:
                        if key == 'our':
                            res['our_cloud_primary_dmg'] += dmg
                # damage taken by our breathers
                if not by_us and aflag.get('breath') is False:
                    pass
                dn = t.get('defender_node', -1)
                dflags = flags_by_node.get(dn, {})
                if dflags.get('breath') and t.get('defender_side', -1) == our_side:
                    res['our_breather_dmg_taken'] += dmg
                    res['our_breather_kills_taken'] += killed
                    if is_counter:
                        res['our_breather_dmg_by_counter'] += dmg
    res.update(dict(
        battle_id=ep['battle_id'], policy=ep['policy'], scenario=ep['scenario'],
        role=ep['role'], seed=ep['seed'], success=ep['success'],
        truncated=ep['truncated'], steps=ep['steps'],
        our_loss_units=ep.get('permanent_army_loss_units'),
        our_loss_by_creature=ep.get('permanent_army_loss_by_creature'),
    ))
    return res


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--tag', required=True)
    parser.add_argument('--out', default='')
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    run_dir = here / 'runs' / args.tag

    rows = []
    for path in sorted(run_dir.glob('*.json')):
        if path.name in ('manifest.json', 'analysis.json'):
            continue
        gz = path.with_suffix('.json.gz')
        if not path.exists() or not gz.exists():
            continue
        try:
            rows.append(analyze_episode(path, gz))
        except Exception as e:
            print('ERR', path.name, e)

    print(f'episodes analyzed: {len(rows)}')
    keys = ['our_breath_attacks', 'our_breath_counter', 'our_breath_primary_dmg',
            'our_breath_secondary_dmg', 'our_breath_friendly_dmg', 'our_breath_primary_kills',
            'our_breath_secondary_kills', 'enemy_breath_attacks', 'enemy_breath_primary_dmg',
            'enemy_breath_secondary_dmg', 'enemy_breath_friendly_dmg', 'our_breather_dmg_taken',
            'our_breather_dmg_by_counter', 'our_cloud_attacks', 'our_loss_units']

    by = defaultdict(list)
    for r in rows:
        by[r['policy']].append(r)
    print('\n== per-policy native aggregates ==')
    for policy in sorted(by):
        rs = by[policy]
        line = f'  {policy:9s} n={len(rs):2d} '
        for k in keys:
            line += f'{k}={sum(r[k] or 0 for r in rs)} '
        print(line)

    print('\n== expert override diagnostics ==')
    for r in rows:
        if r['policy'] == 'expert':
            print(f"  {r['scenario']} {r['role']:8s}: overrides={r['expert_overrides']} "
                  f"breath_selected={r['expert_breath_selected']} "
                  f"our_breath={r['our_breath_attacks']} sec_dmg={r['our_breath_secondary_dmg']} "
                  f"ff={r['our_breath_friendly_dmg']} loss={r['our_loss_units']} "
                  f"{'W' if r['success'] else 'L'}")

    print('\n== counter vs teacher divergence ==')
    for r in rows:
        if r['policy'] == 'counter':
            print(f"  {r['scenario']} {r['role']:8s}: counter_differs={r['counter_differs_from_teacher']} "
                  f"enemy_breath={r['enemy_breath_attacks']} enemy_sec_dmg={r['enemy_breath_secondary_dmg']} "
                  f"enemy_ff={r['enemy_breath_friendly_dmg']} our_loss={r['our_loss_units']}")

    if args.out:
        Path(args.out).write_text(json.dumps(rows, indent=1))
        print('wrote', args.out)


if __name__ == '__main__':
    main()
