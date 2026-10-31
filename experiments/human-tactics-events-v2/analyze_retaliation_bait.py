#!/usr/bin/env python3
"""events-v2 retaliation-bait analysis from native events.

Verifies, per episode, with native COUNTER events only:
  * retaliation exhaustion: per (round, defender) counts of COUNTER events
    vs the number of attacks received in that round (finite retaliation is
    the mechanism the tactic depends on)
  * bait absorption: COUNTER events whose defender is one of our low-value
    units vs our high-value units
  * our counter-damage taken split by own unit value band (chaff vs main)
Paired cells compare policies on identical (scenario, role, seed).
"""
import argparse
import gzip
import json
from collections import defaultdict
from pathlib import Path


def unit_flags_by_node(data):
    """Per-decision node index -> (value, is_enemy). Unit node indices are NOT
    stable across decisions (units die and later nodes shift)."""
    import numpy as np
    from vcmi_gym.envs.v15.vcmi_env import Unit
    out = []
    for d in data['decisions']:
        arr = np.asarray(d['observation']['nodes']['Unit'], dtype=np.float32)
        m = {}
        for i in range(arr.shape[0]):
            u = Unit.decode_one(arr[i])
            m[i] = dict(value=float(u.VALUE_REL), is_enemy=bool(u.IS_ENEMY))
        out.append(m)
    return out


def analyze(path):
    with gzip.open(path.with_suffix('.json.gz'), 'rt') as f:
        data = json.load(f)
    ep = data['episode']
    our_side = 1 if ep['role'] == 'defender' else 0
    flags_per_decision = unit_flags_by_node(data)

    own_values = []
    for m in flags_per_decision:
        own_values += [v['value'] for v in m.values() if not v['is_enemy']]
    max_own = max(own_values) if own_values else 0.0

    def band(node, flags):
        v = flags.get(node, {}).get('value', 0.0)
        if max_own <= 0:
            return 'unknown'
        return 'chaff' if v < 0.25 * max_own else 'main'

    res = dict(
        our_counter_events=0, our_counter_dmg_to_them=0,
        their_counter_events=0, their_counter_dmg_to_us=0,
        counter_dmg_to_our_chaff=0, counter_dmg_to_our_main=0,
        counter_kills_to_our_chaff=0, counter_kills_to_our_main=0,
        attacks_received_by_us=0, attacks_received_by_them=0,
        our_attacks=0, our_kills=0, our_dmg_dealt=0,
        bait_overrides=0, counter_overrides=0,
    )
    # per defender (unit id) per rough period: attacks received vs counters
    recv_attacks = defaultdict(int)
    recv_counters = defaultdict(int)

    for di, d in enumerate(data['decisions']):
        flags = flags_per_decision[di]
        q = d.get('quality') or {}
        if q.get('override'):
            if q.get('version', '').startswith('retaliation-bait-v1'):
                res['bait_overrides'] += 1
            elif q.get('version', '').startswith('retaliation-bait-counter'):
                res['counter_overrides'] += 1
        for ev in d['battle_events']:
            if ev['kind'] != 2:
                continue
            a_side = ev.get('attacker_side', -1)
            by_us = a_side == our_side
            is_counter = bool(ev['attack_flags'] & 2)
            for t in ev['targets']:
                t_side = t.get('defender_side', -1)
                dmg, killed = t['damage'], t['killed']
                if t_side == our_side:
                    recv_attacks[t['defender_id']] += 1
                    res['attacks_received_by_us'] += 1
                    if is_counter and a_side != our_side:
                        recv_counters[t['defender_id']] += 1
                        res['their_counter_events'] += 1
                        res['their_counter_dmg_to_us'] += dmg
                        b = band(t.get('defender_node', -1), flags)
                        if b == 'chaff':
                            res['counter_dmg_to_our_chaff'] += dmg
                            res['counter_kills_to_our_chaff'] += killed
                        elif b == 'main':
                            res['counter_dmg_to_our_main'] += dmg
                            res['counter_kills_to_our_main'] += killed
                elif t_side == 1 - our_side and t_side >= 0:
                    recv_attacks[t['defender_id']] += 1
                    res['attacks_received_by_them'] += 1
                    if is_counter and a_side == our_side:
                        recv_counters[t['defender_id']] += 1
                        res['our_counter_events'] += 1
                        res['our_counter_dmg_to_them'] += dmg
                if by_us:
                    res['our_dmg_dealt'] += dmg
                    res['our_kills'] += killed
            if by_us:
                res['our_attacks'] += 1

    res.update(dict(
        battle_id=ep['battle_id'], policy=ep['policy'], scenario=ep['scenario'],
        role=ep['role'], seed=ep['seed'], success=ep['success'],
        our_loss_units=ep.get('permanent_army_loss_units'),
        steps=ep['steps'],
        exhausted_defenders=sum(1 for k in recv_attacks if recv_counters[k] < recv_attacks[k]),
        multi_attack_defenders=sum(1 for k in recv_attacks if recv_attacks[k] >= 2),
        never_countered_defenders=sum(1 for k in recv_attacks if recv_counters[k] == 0),
    ))
    return res, recv_attacks, recv_counters


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--tag', required=True)
    parser.add_argument('--out', default='')
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    run_dir = here / 'runs' / args.tag

    rows = []
    all_recv = {}
    for path in sorted(run_dir.glob('*.json')):
        if path.name in ('manifest.json', 'analysis.json'):
            continue
        gz = path.with_suffix('.json.gz')
        if not path.exists() or not gz.exists():
            continue
        try:
            r, ra, rc = analyze(path)
            rows.append(r)
            all_recv[path.stem] = dict(attacks=ra, counters=rc)
        except Exception as e:
            print('ERR', path.name, e)

    print(f'episodes: {len(rows)}')
    by = defaultdict(list)
    for r in rows:
        by[r['policy']].append(r)
    print('\n== per-policy aggregates ==')
    keys = ['our_counter_events', 'their_counter_events', 'counter_dmg_to_our_chaff',
            'counter_dmg_to_our_main', 'counter_kills_to_our_chaff', 'counter_kills_to_our_main',
            'exhausted_defenders', 'multi_attack_defenders', 'never_countered_defenders',
            'our_loss_units', 'bait_overrides', 'counter_overrides']
    for policy in sorted(by):
        rs = by[policy]
        print(f"  {policy:12s} n={len(rs):2d} " + ' '.join(
            f'{k}={sum(r[k] or 0 for r in rs)}' for k in keys))

    print('\n== per-episode counter damage split ==')
    for r in sorted(rows, key=lambda r: (r['policy'], r['scenario'], r['role'], r['seed'])):
        print(f"  {r['policy']:12s} {r['scenario'][-12:]} {r['role']:8s} s{r['seed']}: "
              f"counter_dmg chaff={r['counter_dmg_to_our_chaff']:5d} main={r['counter_dmg_to_our_main']:5d} "
              f"exhausted={r['exhausted_defenders']:2d} multi_atk={r['multi_attack_defenders']:2d} "
              f"loss={r['our_loss_units']} {'W' if r['success'] else 'L'}")

    print('\n== paired cells ==')
    cells = defaultdict(dict)
    for r in rows:
        cells[(r['scenario'], r['role'], r['seed'])][r['policy']] = r
    for (sc, role, seed), pols in sorted(cells.items()):
        line = f'  {sc[-12:]} {role:8s} s{seed}: '
        for p in ['bait', 'bait-counter', 'teacher', 'random']:
            if p in pols:
                r = pols[p]
                line += f"{p}=[{'W' if r['success'] else 'L'}/{r['our_loss_units']}u/chaff{r['counter_dmg_to_our_chaff']}] "
        print(line)

    print('\n== bait vs teacher paired deltas (our loss units, counter-dmg-to-main) ==')
    ds = []
    for (sc, role, seed), pols in sorted(cells.items()):
        if 'bait' in pols and 'teacher' in pols:
            b, t = pols['bait'], pols['teacher']
            ds.append((sc[-12:], role, seed,
                       b['our_loss_units'] - t['our_loss_units'],
                       b['counter_dmg_to_our_main'] - t['counter_dmg_to_our_main'],
                       int(b['success']) - int(t['success'])))
    for d in ds:
        print(f'  {d[0]} {d[1]:8s} s{d[2]}: dloss={d[3]:+d} dmain_counter={d[4]:+d} dwin={d[5]:+d}')
    if ds:
        print(f"  n={len(ds)} mean dloss={sum(d[3] for d in ds)/len(ds):+.2f} "
              f"mean dmain_counter={sum(d[4] for d in ds)/len(ds):+.2f}")

    if args.out:
        Path(args.out).write_text(json.dumps(dict(rows=rows, recv=all_recv), indent=1))
        print('wrote', args.out)


if __name__ == '__main__':
    main()
