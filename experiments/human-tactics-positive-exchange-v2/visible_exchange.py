"""Positive expected exchange guard, a research script, never an expert label.

Only the current public graph and legal native teacher action are consumed.
The score remains a pairwise expected value proxy, NOT permanent casualties.
"""
import math

VERSION = 'positive-exchange-v2'
MIN_GAIN_PERMILLE = 1.0


def decide(legal, baseline, facts):
    legal = tuple(int(a) for a in legal)
    if not legal or len(set(legal)) != len(legal) or baseline not in legal:
        raise ValueError('Unique legal actions and a legal baseline required')
    if set(facts) != set(legal):
        raise ValueError('Exactly one fact row per legal action required')
    base = facts[baseline]

    def eligible(row):
        score = row.get('net_permille')
        return (row.get('ordinary_melee') is True
                and type(row.get('actor')) is int
                and row.get('actor') == base.get('actor')
                and type(score) in (int, float) and math.isfinite(score))

    selected = baseline
    if eligible(base):
        candidates = [a for a in legal if eligible(facts[a])
                      and facts[a]['net_permille'] > 0.0]
        if candidates:
            best = max(candidates, key=lambda a: (facts[a]['net_permille'], -a))
            if facts[best]['net_permille'] > base['net_permille'] + MIN_GAIN_PERMILLE:
                selected = best
    return selected, dict(version=VERSION, certified=False, eligible_for_bc=False,
        teacher_action=baseline, overrode_teacher=selected != baseline,
        reason='strict_positive_exchange' if selected != baseline else 'teacher_fallback',
        baseline_estimate=base.get('net_permille'),
        selected_estimate=facts[selected].get('net_permille'),
        estimate_is_rollout=False, estimate_is_permanent_gain=False)


def choose(obs):
    from vcmi_gym.envs.v15.vcmi_env import Action, Unit, ACTION_TYPES
    from experts_events import assess
    visible = {k: obs[k] for k in ('nodes', 'edges', 'active_action_ids')}
    units = Unit.decode_many(visible['nodes']['Unit'])
    public = assess(visible)
    facts = {}
    for raw in visible['active_action_ids']:
        action = int(raw)
        row = public[action]
        actor = units[row['actor_node']]
        primary = row['primary']
        ordinary = (int(Action.decode_one(visible['nodes']['Action'][action]).ACTION_TYPE)
                    == ACTION_TYPES['AMOVE'] and not row['secondary']
                    and len(primary) == 1 and bool(units[primary[0]].IS_ENEMY)
                    and not actor.HAS_TWO_HEX_ATTACK_BREATH)
        facts[action] = dict(actor=row['actor_node'], ordinary_melee=bool(ordinary),
                             net_permille=row['est_primary_net_rel_bf'])
    return decide(visible['active_action_ids'], int(obs['teacher_action_id']), facts)
