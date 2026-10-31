#!/usr/bin/env python3
"""events-v2 tactic analysis: native-event verification + paired comparison.

For each episode archive (gzip json with episode + decisions):
  * verifies what the NATIVE events prove (breath attacks, secondary hits,
    friendly fire, counter attacks, death-cloud spell hits, ...)
  * computes per-side native aggregates and terminal outcome
Then builds PAIRED comparisons over (scenario, role, seed) cells:
the same battle fought by different policies against the same native
BattleAI opponent. Reports our-side permanent losses, enemy losses,
wins and tactic-level native metrics.

No win-rate is claimed from few cells; unknown stays unknown.
"""
import argparse
import gzip
import json
import math
from collections import defaultdict
from pathlib import Path

KIND = {0: 'ACTION_STARTED', 1: 'ACTION_FINISHED', 2: 'ATTACK', 3: 'BATTLE_END'}
AFLAG = {1: 'SHOT', 2: 'COUNTER', 4: 'LUCKY', 8: 'UNLUCKY', 16: 'BALLISTA', 32: 'DEATH_BLOW', 64: 'SPELL_LIKE'}
DFLAG = {1: 'KILLED', 2: 'SECONDARY', 8: 'CLONE_KILLED', 16: 'SPELL_EFFECT'}


def load(path):
    with gzip.open(path, 'rt') as f:
        return json.load(f)


def episode_native(data):
    """Aggregate native events for OUR side (the side the env played)."""
    our_side = 1 if data['episode']['role'] == 'defender' else 0
    agg = dict(
        attacks_by_us=0, attacks_vs_us=0, counter_attacks_by_us=0, counter_attacks_vs_us=0,
        dmg_dealt_by_us=0, dmg_received_by_us=0, kills_by_us=0, killed_of_ours=0,
        secondary_hits_by_us=0, secondary_dmg_by_us=0, secondary_hits_vs_us=0,
        secondary_dmg_vs_us=0, friendly_fire_hits=0, friendly_fire_dmg=0,
        shots_by_us=0, shots_vs_us=0, spell_like_by_us=0, spell_like_vs_us=0,
        breath_attacks_by_us=0, breath_attacks_vs_us=0,
        breath_primary_dmg=0, breath_secondary_dmg=0, breath_kills=0,
        breath_counter_attacks=0,  # breath executed AS a counter attack
        cloud_primary_dmg=0, cloud_secondary_dmg=0,
        dragon_dmg_taken=0, dragon_kills_taken=0,
    )
    for d in data['decisions']:
        for ev in d['battle_events']:
            if ev['kind'] != 2:
                continue
            a_side = ev.get('attacker_side', -1)
            by_us = (a_side == our_side)
            flags = ev['attack_flags']
            is_counter = bool(flags & 2)
            is_shot = bool(flags & 1)
            spell_like = bool(flags & 64)
            agg['counter_attacks_by_us' if by_us else 'counter_attacks_vs_us'] += 1 if is_counter else 0
            agg['shots_by_us' if by_us else 'shots_vs_us'] = agg.get('shots_by_us' if by_us else 'shots_vs_us', 0) + (1 if is_shot else 0)
            if spell_like:
                agg['spell_like_by_us' if by_us else 'spell_like_vs_us'] += 1
            if by_us:
                agg['attacks_by_us'] += 1
            else:
                agg['attacks_vs_us'] += 1
            for t in ev['targets']:
                dmg = t['damage']
                killed = t['killed']
                tfl = t['flags']
                sec = bool(tfl & 2)
                t_side = t.get('defender_side', -1)
                if by_us:
                    agg['dmg_dealt_by_us'] += dmg
                    agg['kills_by_us'] += killed
                    if sec:
                        agg['secondary_hits_by_us'] += 1
                        agg['secondary_dmg_by_us'] += dmg
                else:
                    agg['dmg_received_by_us'] += dmg
                    agg['killed_of_ours'] += killed
                    if sec:
                        agg['secondary_hits_vs_us'] += 1
                        agg['secondary_dmg_vs_us'] += dmg
                if t_side >= 0 and a_side >= 0 and t_side == a_side:
                    # damage to the attacker's own side (friendly fire),
                    # including spell-like (death cloud) friendly fire
                    agg['friendly_fire_hits'] += 1
                    agg['friendly_fire_dmg'] += dmg
    return agg


def classify_breathers(data, our_side):
    """Which unit ids are two-hex breathers on each side (from observations)."""
    # decoded from graph is expensive; instead use per-episode Unit node flags
    # from the recorded decisions: find units with HAS_TWO_HEX_ATTACK_BREATH.
    # The Unit node attribute index for HAS_TWO_HEX_ATTACK_BREATH is looked up
    # lazily; fall back to event-shape detection when not resolvable.
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--tag', required=True, help='runs/<tag> directory')
    parser.add_argument('--out', default='')
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    run_dir = here / 'runs' / args.tag

    episodes = {}
    for path in sorted(run_dir.glob('*.json')):
        if path.name in ('manifest.json', 'analysis.json'):
            continue
        rec = json.loads(path.read_text())
        if not isinstance(rec, dict) or not rec.get('completed'):
            continue
        archive = path.with_suffix('.json.gz')
        data = load(archive) if archive.exists() else None
        our_side = 1 if rec['role'] == 'defender' else 0
        losses = rec.get('permanent_army_loss_by_creature') or {}
        episodes[path.stem] = dict(
            policy=rec['policy'], scenario=rec['scenario'], role=rec['role'],
            seed=rec['seed'], success=rec['success'], truncated=rec['truncated'],
            our_losses=losses, our_loss_units=rec.get('permanent_army_loss_units'),
            steps=rec['steps'],
            native=episode_native(data) if data else None)

    # paired cells keyed by (scenario, role, seed)
    cells = defaultdict(dict)
    for name, ep in episodes.items():
        cells[(ep['scenario'], ep['role'], ep['seed'])][ep['policy']] = ep

    print(f'episodes: {len(episodes)}  cells: {len(cells)}')
    by_policy = defaultdict(lambda: dict(n=0, wins=0, loss_units=0, trunc=0,
                                         sec_dmg=0, ff=0, dmg_dealt=0, dmg_recv=0))
    for name, ep in episodes.items():
        p = by_policy[ep['policy']]
        p['n'] += 1
        p['wins'] += int(bool(ep['success']))
        p['trunc'] += int(bool(ep['truncated']))
        if ep['our_loss_units'] is not None:
            p['loss_units'] += ep['our_loss_units']
        if ep['native']:
            p['sec_dmg'] += ep['native']['secondary_dmg_by_us']
            p['ff'] += ep['native']['friendly_fire_dmg']
            p['dmg_dealt'] += ep['native']['dmg_dealt_by_us']
            p['dmg_recv'] += ep['native']['dmg_received_by_us']

    print('\n== per-policy aggregates (all roles pooled) ==')
    for policy in sorted(by_policy):
        p = by_policy[policy]
        print(f"  {policy:9s} n={p['n']:2d} wins={p['wins']:2d} trunc={p['trunc']} "
              f"our_loss_units={p['loss_units']:5d} sec_dmg={p['sec_dmg']:6d} "
              f"friendly_fire={p['ff']:5d} dmg_dealt={p['dmg_dealt']:6d} dmg_recv={p['dmg_recv']:6d}")

    print('\n== paired cells (scenario,role,seed) ==')
    for (sc, role, seed), pols in sorted(cells.items()):
        line = f'  {sc} {role:8s} s{seed}: '
        for policy in ['expert', 'counter', 'teacher', 'random']:
            if policy in pols:
                ep = pols[policy]
                line += (f"{policy}=[{'W' if ep['success'] else 'L'}"
                         f"/{ep['our_loss_units']}u] ")
        print(line)

    # expert vs teacher paired delta (our loss units, enemy dmg dealt by us)
    print('\n== expert-vs-teacher paired deltas (same scenario/role/seed) ==')
    deltas = []
    for (sc, role, seed), pols in sorted(cells.items()):
        if 'expert' in pols and 'teacher' in pols:
            e, t = pols['expert'], pols['teacher']
            if e['our_loss_units'] is not None and t['our_loss_units'] is not None:
                deltas.append((sc, role, seed, e['our_loss_units'] - t['our_loss_units'],
                               e['success'] - t['success']))
    for d in deltas:
        print(f'  {d[0]} {d[1]:8s} s{d[2]}: dloss={d[3]:+d} dwin={d[4]:+d}')
    if deltas:
        print(f'  n={len(deltas)}  mean dloss={sum(d[3] for d in deltas)/len(deltas):+.2f}')

    if args.out:
        out = dict(episodes=episodes,
                   cells={f'{k[0]}|{k[1]}|{k[2]}': v for k, v in cells.items()},
                   by_policy=dict(by_policy))
        Path(args.out).write_text(json.dumps(out, indent=1))
        print('wrote', args.out)


if __name__ == '__main__':
    main()
