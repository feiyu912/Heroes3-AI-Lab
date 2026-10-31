"""Visible-state, legal-action coverage policy; not a claim of optimal play."""
from vcmi_gym.envs.v15.vcmi_env import Unit, Action, ACTION_TYPES

VERSION = 'coverage-value-v1'


def coverage_score(targets, units):
    # Relative stack value is only a proxy for damage. Preserve ally sign and
    # deduplicate two-hex/overlapping targets. No reward is awarded for this score.
    return sum((1 if units[index].IS_ENEMY else -1) * units[index].VALUE_REL
               for index in set(targets))


def assess(obs):
    units = Unit.decode_many(obs['nodes']['Unit'])
    actors = {int(action): int(unit) for action, unit in
              obs['edges'][('Action', 'By', 'Unit')]['index'].T}
    targets = {}
    for relation in [('Unit', 'IsMeleedBy', 'Action'), ('Unit', 'IsShotBy', 'Action')]:
        for unit, action in obs['edges'][relation]['index'].T:
            targets.setdefault(int(action), set()).add(int(unit))
    result = {}
    for raw in obs['active_action_ids']:
        action = int(raw)
        actor = units[actors[action]]
        kind = int(Action.decode_one(obs['nodes']['Action'][action]).ACTION_TYPE)
        affected = targets.get(action, set())
        ability = ((kind == ACTION_TYPES['AMOVE'] and actor.HAS_TWO_HEX_ATTACK_BREATH)
                   or (kind == ACTION_TYPES['SHOOT'] and actor.HAS_DEATH_CLOUD))
        result[action] = dict(ability=bool(ability), targets=sorted(affected),
            enemy_targets=sum(bool(units[index].IS_ENEMY) for index in affected),
            friendly_targets=sum(not units[index].IS_ENEMY for index in affected),
            coverage_value=coverage_score(affected, units))
    return result


def choose(obs):
    legal = [int(value) for value in obs['active_action_ids']]
    teacher = int(obs.get('teacher_action_id', -1))
    assert teacher in legal, 'Native search teacher must provide a mapped legal action'
    metrics = assess(obs)
    candidates = [action for action in legal if metrics[action]['ability']
                  and metrics[action]['enemy_targets'] >= 2
                  and metrics[action]['coverage_value'] > 0]
    action = teacher
    if candidates:
        best = max(candidates, key=lambda a: (metrics[a]['coverage_value'],
                   -metrics[a]['friendly_targets'], -a))
        if metrics[best]['coverage_value'] > metrics[teacher]['coverage_value']:
            action = best
    assert action in legal
    return action, dict(version=VERSION, selected=metrics[action], teacher_action=teacher,
        override=action != teacher, quality='provisional-visible-coverage-proxy',
        limitations='Not exact damage/search optimality. Non-AoE and bait/counter behavior delegates to the native search teacher; no certified bait expert yet.')
