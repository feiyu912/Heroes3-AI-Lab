"""Conservative, deployment-eligible visible exchange probe; NOT an expert.

No native simulator, RNG, event log, outcome or demonstration label is read.
The one-step graph estimate includes ordinary retaliation but is not a rollout.
"""
import math

VERSION = 'visible-exchange-v1'
MIN_GAIN_PERMILLE = 1.0  # fixed before any new game; not fitted to outcomes


def decide(legal, baseline, facts):
    """Pure decision core. All facts are projected from the current public graph.

    Keep teacher movement/wait/defend and special attacks. Compare ordinary
    primary-only melee choices for the SAME active unit. Never create actions.
    """
    legal = tuple(int(a) for a in legal)
    if baseline not in legal:
        raise ValueError('Baseline must be legal')
    base = facts[baseline]

    def eligible(row):
        score = row.get('net_permille')
        return (row.get('ordinary_melee') is True
                and row.get('actor') == base.get('actor')
                and isinstance(score, (int, float)) and math.isfinite(score))

    selected = baseline
    if eligible(base):
        candidates = [a for a in legal if eligible(facts[a])]
        best = max(candidates, key=lambda a: (facts[a]['net_permille'], -a))
        if facts[best]['net_permille'] > base['net_permille'] + MIN_GAIN_PERMILLE:
            selected = best
    return selected, dict(version=VERSION, certified=False, eligible_for_bc=False,
                         teacher_action=baseline, overrode_teacher=selected != baseline,
                         reason='visible_exchange_improvement' if selected != baseline else 'teacher_fallback',
                         baseline_estimate=base.get('net_permille'),
                         selected_estimate=facts[selected].get('net_permille'),
                         estimate_is_rollout=False)


def choose(obs):
    # Lazy imports allow CPU-only validation of the decision contract.
    from vcmi_gym.envs.v15.vcmi_env import Action, Unit, ACTION_TYPES
    from experts_events import assess
    # Explicit projection: seed, native events and terminal data cannot enter assess.
    visible = {k: obs[k] for k in ('nodes', 'edges', 'active_action_ids')}
    units = Unit.decode_many(visible['nodes']['Unit'])
    public = assess(visible)
    facts = {}
    for action in visible['active_action_ids']:
        action = int(action)
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
