"""Strict, dependency-free event association. No guessed dead-unit identity."""
from collections import defaultdict


def references(event):
    if event['kind'] in (0, 1):
        yield event.get('stack_number', -1), event.get('stack_node', -1), event.get('side', -1)
    if event['kind'] == 2:
        yield event.get('attacker_id', -1), event.get('attacker_node', -1), event.get('attacker_side', -1)
        for target in event.get('targets', []):
            yield target.get('defender_id', -1), target.get('defender_node', -1), target.get('defender_side', -1)


def update_identity(registry, events, flags, batch_id):
    """Node indices in a delivered batch refer to ITS delivered graph only.

    VALUE_REL is observation-relative; retain history instead of assuming it
    defines a permanent main/chaff class. Unknown is never value zero.
    """
    mapping = {}
    for event in events:
        for uid, node, side in references(event):
            if uid < 0:
                continue
            entry = registry.setdefault(str(uid), dict(unit_id=uid, side=None, evidence=[], unknown=True))
            if side in (0, 1):
                if entry['side'] is not None and entry['side'] != side:
                    entry['side_conflict'] = True
                else:
                    entry['side'] = side
            if node >= 0 and str(node) in flags:
                if node in mapping and mapping[node] != uid:
                    raise AssertionError('Two stable units mapped to one current graph node')
                mapping[node] = uid
                row = dict(batch_id=batch_id, node=node, flags=flags[str(node)])
                if row not in entry['evidence']:
                    entry['evidence'].append(row)
                entry['unknown'] = False
    return mapping


def action_window(events, side, known_actor_id=None, expected_native_type=None):
    """Require a single requested-side action with its native matching finish.

    The env makes one legal request per step. Other-side actions after its
    finish and our automatic counters never become demonstration labels.
    Missing/ambiguous windows fail closed, even at terminal.
    """
    starts = [(i, e) for i, e in enumerate(events) if e['kind'] == 0 and e.get('side') == side]
    result = dict(status='unknown', reason=None, start=None, finish=None,
                  actor_id=None, attack_indices=[], counter_indices=[], enemy_attack_indices=[])
    if len(starts) != 1:
        result['reason'] = 'not_exactly_one_requested_side_action'
        return result
    start, action = starts[0]
    uid = action.get('stack_number', -1)
    result.update(start=start, actor_id=uid, native_action_type=action.get('action_type'))
    if expected_native_type is not None and action.get('action_type') != expected_native_type:
        result['reason'] = 'native_action_type_mismatch'
        return result
    if uid < 0 or (known_actor_id is not None and uid != known_actor_id):
        result['reason'] = 'actor_mismatch_or_nonunit'
        return result
    finishes = [i for i in range(start + 1, len(events))
                if events[i]['kind'] == 1 and events[i].get('side') == side
                and events[i].get('stack_number') == uid
                and events[i].get('action_type') == action.get('action_type')]
    if len(finishes) != 1:
        result['reason'] = 'missing_or_ambiguous_matching_finish'
        return result
    finish = finishes[0]
    if any(e['kind'] == 0 for e in events[start + 1:finish]):
        result['reason'] = 'nested_action_window'
        return result
    for i in range(start + 1, finish):
        e = events[i]
        if e['kind'] != 2:
            continue
        if e.get('attack_flags', 0) & 2:
            result['counter_indices'].append(i)
        elif e.get('attacker_id') == uid and e.get('attacker_side') == side:
            result['attack_indices'].append(i)
        else:
            result['enemy_attack_indices'].append(i)
    result.update(status='matched', finish=finish,
                  binding='stable_actor_id' if known_actor_id is not None else 'single_env_request_protocol')
    return result


def analyze_retaliations(batches):
    """Count received primary melee attacks and EMITTED counters per stack/round.

    Cross-round batches have no per-event round in this native schema, so
    they are unknown. No eligibility claim: no-retaliation abilities, death,
    incapacitation and remaining counters are not exposed by this stream.
    """
    rows = defaultdict(lambda: dict(primary_melee_received=0, counters_emitted=0,
                                    primary_hits=[], counter_targets=[]))
    unknown_round_attacks = 0
    for batch in batches:
        same_round = batch.get('round_before') == batch.get('round_after')
        for e in batch['events']:
            if e['kind'] != 2:
                continue
            if not same_round or batch.get('round_before') is None:
                unknown_round_attacks += 1
                continue
            rnd = batch['round_before']
            flags = e.get('attack_flags', 0)
            if flags & 2:
                uid = e.get('attacker_id', -1)
                if uid >= 0:
                    row = rows[(rnd, uid)]
                    row['counters_emitted'] += 1
                    row['counter_targets'].extend(t.get('defender_id') for t in e.get('targets', [])
                                                 if not t.get('flags', 0) & 2)
            elif not flags & (1 | 64):
                for target in e.get('targets', []):
                    if target.get('flags', 0) & (2 | 16):
                        continue
                    uid = target.get('defender_id', -1)
                    if uid >= 0 and target.get('defender_side') != e.get('attacker_side'):
                        row = rows[(rnd, uid)]
                        row['primary_melee_received'] += 1
                        row['primary_hits'].append(dict(attacker_id=e.get('attacker_id'),
                                                        killed=target.get('killed'), damage=target.get('damage')))
    return dict(subjects=[dict(round=rnd, unit_id=uid, **row) for (rnd, uid), row in sorted(rows.items())],
                unknown_round_attacks=unknown_round_attacks,
                finite_retaliation_proven=False,
                limitation='Correct subjects and same-round observations only; eligibility/remaining counters unknown')


def demonstration_gate(step, events, episode):
    window = step['action_window']
    reasons = []
    if not episode.get('terminated') or episode.get('truncated'):
        reasons.append('not_normal_complete_episode')
    if window['status'] != 'matched':
        reasons.append('unmatched_action_window')
    groups = [events[i] for i in window['attack_indices']]
    positive = any(t.get('damage', 0) > 0 for e in groups for t in e.get('targets', []))
    if not positive:
        reasons.append('no_positive_damage_by_selected_actor_inside_action')
    # Q2 means only action-level event correspondence, never optimality or expert certification.
    return dict(action_event_verified=not reasons, reasons=reasons,
                max_quality='Q2-event-correspondence' if not reasons else 'Q1-legal-execution',
                certified_expert=False, eligible_for_bc=False,
                bc_blocker='No preregistered paired benefit and independent tactic certification')
