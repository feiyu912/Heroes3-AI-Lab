#!/usr/bin/env python3
"""events-v3 retaliation analysis: correct SUBJECT + round grouping.

Fixes per WORKBUDDY_EVENTS_V2_REVIEW_20261018.md:
  * v2 counted recv_attacks/recv_counters by the DEFENDER of counter events,
    conflating "unit that received a counterattack" with "unit that spent a
    retaliation". The retaliation budget belongs to the COUNTER event's
    ATTACKER (the retaliating unit).
  * v2 did not group by round and did not exclude shots / spell-like /
    counter attacks, which cannot trigger (normal) retaliation.
  * v2 treated unknown units as chaff (value 0); v3 keeps them 'unknown'
    using the episode identity table.

Data model (v3 runner): each step records post_events with round_before/
round_after; batches that span a round boundary are flagged.
"""
import argparse
import gzip
import json
from collections import defaultdict
from pathlib import Path


def analyze(path):
    with gzip.open(path, 'rt') as f:
        data = json.load(f)
    ep = data['episode']
    our_side = 1 if ep['role'] == 'defender' else 0
    identity = ep.get('event_identity', {})

    def band_of_unit(uid, node, flags):
        """chaff/main/unknown from the identity table; never default to chaff."""
        if node is not None and node >= 0:
            v = flags.get(node, {}).get('value')
            if v is None:
                return 'unknown'
        rec = identity.get(str(uid)) or identity.get(uid)
        if rec and isinstance(rec.get('identity'), dict) and 'value' in rec['identity']:
            v = rec['identity']['value']
        else:
            return 'unknown'
        return 'unknown' if v is None else v

    max_own = 0.0
    for rec in identity.values():
        ident = rec.get('identity') if isinstance(rec, dict) else None
        if isinstance(ident, dict) and ident.get('value') and not ident.get('is_enemy'):
            max_own = max(max_own, ident['value'])
    if max_own <= 0:
        for node, f in ep.get('initial_lineup', {}).items():
            if not f.get('is_enemy'):
                max_own = max(max_own, f.get('value', 0.0))

    def band(uid, node, flags):
        v = band_of_unit(uid, node, flags)
        if v == 'unknown' or v is None:
            return 'unknown'
        return 'chaff' if v < 0.25 * max_own else 'main'

    # ---- corrected retaliation accounting -----------------------------------
    # triggering attacks on subject U in round R:
    #   melee (no SHOT=1), not spell-like (SPELL_LIKE=64), not a counter itself
    # COUNTER events issued by U: attacker==U and COUNTER=2
    received = defaultdict(int)     # (round, subject) -> triggering attacks
    issued = defaultdict(int)       # (round, subject) -> counters issued
    span_batches = 0
    counter_dmg = dict(chaff=0, main=0, unknown=0)
    counter_kills = dict(chaff=0, main=0, unknown=0)
    counter_dmg_enemy_on_us = 0
    our_counter_dmg_on_them = 0

    for s in data['step_log']:
        rb, ra = s['round_before'], s['round_after']
        if rb != ra:
            span_batches += 1
        # events delivered with an obs index into THAT obs's graph:
        # pre_events -> this decision's graph (pre_flags),
        # post_events -> the next decision's graph (post_flags).
        pre_flags = s.get('pre_flags', {})
        post_flags = s.get('post_flags', {})
        # Each interaction is delivered ONCE: as post_events of the step that
        # caused it (and again as pre_events of the next step - same list).
        # Count post_events only, plus the archived terminal batch.
        pairs = [(s['post_events'], s.get('post_flags', {}))]
        for events, flags in pairs:
            for e in events:
                if e['kind'] != 2:
                    continue
                atk_flags = e['attack_flags']
                is_counter = bool(atk_flags & 2)
                is_shot = bool(atk_flags & 1)
                spell_like = bool(atk_flags & 64)
                for t in e['targets']:
                    tgt, src = t['defender_id'], t['attacker_id']
                    if is_counter:
                        # subject of the retaliation budget = the counter's ATTACKER
                        subject = src
                        if subject is not None and subject >= 0:
                            issued[(rb, subject)] += 1
                        # counter damage split by the recipient's band
                        if e.get('attacker_side') != our_side:
                            counter_dmg_enemy_on_us += t['damage']
                            b = band(tgt, t.get('defender_node'), flags)
                            counter_dmg[b] += t['damage']
                            counter_kills[b] += t['killed']
                        else:
                            our_counter_dmg_on_them += t['damage']
                    else:
                        # triggering attack on subject = the defender
                        if tgt is not None and tgt >= 0 and not is_shot and not spell_like:
                            received[(rb, tgt)] += 1

    # terminal batch: archived separately by v3 (never a post_events of any step)
    term_round = data['step_log'][-1]['round_after'] if data['step_log'] else -1
    for e in data.get('terminal_events', []):
        if e['kind'] != 2:
            continue
        atk_flags = e['attack_flags']
        is_counter = bool(atk_flags & 2)
        is_shot = bool(atk_flags & 1)
        spell_like = bool(atk_flags & 64)
        for t in e['targets']:
            tgt, src = t['defender_id'], t['attacker_id']
            if is_counter and src is not None and src >= 0:
                issued[(term_round, src)] += 1
                if e.get('attacker_side') != our_side:
                    counter_dmg_enemy_on_us += t['damage']
                    b = band(tgt, t.get('defender_node'), {})
                    counter_dmg[b] += t['damage']
                    counter_kills[b] += t['killed']
                else:
                    our_counter_dmg_on_them += t['damage']
            elif tgt is not None and tgt >= 0 and not is_shot and not spell_like:
                received[(term_round, tgt)] += 1

    # ---- per-subject round stats -------------------------------------------
    subjects = sorted({u for (_, u) in received} | {u for (_, u) in issued})
    rounds_by_subject = defaultdict(set)
    for (r, u) in received:
        rounds_by_subject[u].add(r)
    for (r, u) in issued:
        rounds_by_subject[u].add(r)

    exhausted_examples = []   # A>=2 triggering attacks, C<A in the same round
    never_retaliated = []
    unknown_subjects = 0
    for u in subjects:
        rec = identity.get(str(u)) or identity.get(u)
        ident = rec.get('identity') if isinstance(rec, dict) else None
        if not (isinstance(ident, dict) and 'value' in ident):
            unknown_subjects += 1
        for r in sorted(rounds_by_subject[u]):
            a = received.get((r, u), 0)
            c = issued.get((r, u), 0)
            if a >= 2 and c < a:
                exhausted_examples.append((r, u, a, c))
            if a >= 1 and c == 0:
                never_retaliated.append((r, u, a))

    return dict(
        policy=ep['policy'], scenario=ep['scenario'], role=ep['role'], seed=ep['seed'],
        success=ep['success'], our_loss_units=ep.get('permanent_army_loss_units'),
        steps=ep['steps'],
        span_batches=span_batches,
        exhausted_rounds=len(exhausted_examples),
        exhausted_examples=exhausted_examples[:20],
        no_retaliation_rounds=len(never_retaliated),
        unknown_subjects=unknown_subjects,
        counter_dmg_to_us_split=dict(counter_dmg),
        counter_kills_to_us_split=dict(counter_kills),
        counter_dmg_enemy_on_us=counter_dmg_enemy_on_us,
        our_counter_dmg_on_them=our_counter_dmg_on_them,
    )


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
            rows.append(analyze(path))
        except Exception as e:
            print('ERR', path.name, repr(e)[:200])

    print(f'episodes: {len(rows)}')
    tot = dict(exhausted_rounds=0, no_retaliation_rounds=0, unknown_subjects=0,
               span_batches=0)
    for r in rows:
        for k in tot:
            tot[k] += r[k]
    print('totals:', tot)
    print('\n== per-episode ==",')
    for r in sorted(rows, key=lambda r: (r['policy'], r['scenario'], r['role'], r['seed'])):
        split = r['counter_dmg_to_us_split']
        print(f"  {r['policy']:12s} {r['scenario'][-14:]} {r['role']:8s} s{r['seed']}: "
              f"exhausted_rounds={r['exhausted_rounds']:2d} "
              f"no_retal={r['no_retaliation_rounds']:2d} unknown_subj={r['unknown_subjects']} "
              f"span_batches={r['span_batches']:2d} "
              f"counter_dmg(chaff={split['chaff']},main={split['main']},unknown={split['unknown']}) "
              f"loss={r['our_loss_units']} {'W' if r['success'] else 'L'}")

    if args.out:
        Path(args.out).write_text(json.dumps(rows, indent=1))
        print('wrote', args.out)


if __name__ == '__main__':
    main()
