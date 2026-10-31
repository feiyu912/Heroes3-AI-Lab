"""events-v2 experts: visible-state, legal-action decision policies.

NOT a claim of optimal play. Every action comes from obs['active_action_ids'].
No hidden state, no future RNG, no teacher actions as input (the depth-2
teacher action is used ONLY as a fallback baseline when provided, same as
human-tactics-v1; it is recorded, never fed as a feature).

Policies:
  breath-exchange-v1      : dragon two-hex breath AMOVE selection. Uses the
                            visible IS_PRIMARY_TARGET edge flag, the engine's
                            pairwise MeleeDmg estimates for the PRIMARY exchange
                            and relative-value proxies for secondary targets.
                            Overrides the depth-2 teacher only when the teacher
                            did not itself select a breath action and a strictly
                            positive-estimate breath action exists.
  dragon-threat-counter-v1: counter play vs an enemy two-hex breath unit.
                            Prioritizes legally attacking the breather
                            (estimated damage > 0), else prefers keeping
                            high-value own stacks out of breath-adjacent
                            clusters. No invented "avoid retaliation" action.
  teacher / random        : pass-through controls (handled by the runner).
"""
from vcmi_gym.envs.v15.vcmi_env import Unit, Action, ACTION_TYPES
from vcmi_gym.envs.v15.pyconnector import EDGE_TYPES
from collections import defaultdict

VERSION = 'breath-exchange-v1'
COUNTER_VERSION = 'dragon-threat-counter-v3'

# Weights for the breath score (documented, not tuned):
#   primary exchange estimate is the dominant term; secondary coverage and
#   friendly-fire are proxies; attacker HP loss is a smaller term.
W_PRIMARY = 1.0
W_SECONDARY = 0.5
W_FRIENDLY = 1.0
W_ATTACKER_HP = 0.5

PROXY_LIMITATIONS = ('Relative value is a proxy, not damage. Secondary breath '
                     'damage is not directly estimated by the graph; the primary '
                     'pairwise estimate does not model AoE. Remaining counterattacks '
                     'are not visible (interface gap).')


def _decode_linnorm(attrs_row, attr_names):
    """Decode LINNORM attrs back to raw permille values (encoded = raw/1000)."""
    out = {}
    for i, (name, enc, vmax) in enumerate(attr_names):
        if enc == 'LINNORM':
            out[name] = float(attrs_row[i]) * float(vmax)
        elif enc == 'CATEGORICAL':
            out[name] = int(round(attrs_row[i] * float(vmax)))
        else:
            out[name] = float(attrs_row[i])
    return out


def _edge_attr_names(relation):
    """Per-edge (name, encoding, vmax) for LINNORM decoding."""
    return [(attr['name'], attr['encoding'], attr.get('vmax', 0))
            for attr in EDGE_TYPES[relation]['attributes']]


def _cat_value(attrs_row, col, n):
    """CATEGORICAL one-hot column -> value."""
    best, bestv = 0, -1.0
    for i in range(n):
        if attrs_row[col + i] > bestv:
            bestv = attrs_row[col + i]
            best = i
    return best


def _edge_columns(relation):
    """Return list of (attr_name, encoding, n_columns, vmax) per edge relation."""
    cols = []
    for attr in EDGE_TYPES[relation]['attributes']:
        enc = attr['encoding']
        n = attr['size']
        vmax = attr.get('vmax', 0)
        cols.append((attr['name'], enc, n, vmax))
    return cols


def assess(obs):
    """Per-action visible facts. Same shape as v1 plus primary/secondary split."""
    units = Unit.decode_many(obs['nodes']['Unit'])
    actors = {int(action): int(unit) for action, unit in
              obs['edges'][('Action', 'By', 'Unit')]['index'].T}

    melee_cols = _edge_columns(('Unit', 'IsMeleedBy', 'Action'))
    shot_cols = _edge_columns(('Unit', 'IsShotBy', 'Action'))

    targets = {}
    for relation, cols in [(('Unit', 'IsMeleedBy', 'Action'), melee_cols),
                          (('Unit', 'IsShotBy', 'Action'), shot_cols)]:
        index = obs['edges'][relation]['index']
        attrs = obs['edges'][relation]['attrs']
        for e in range(index.shape[1]):
            unit, action = int(index[0, e]), int(index[1, e])
            primary = _cat_value(attrs[e], 0, cols[0][2])
            targets.setdefault(action, []).append((unit, bool(primary)))

    # MeleeDmg pairwise estimates: (Unit,MeleeDmg,Unit) -> 5 LINNORM permille attrs
    md_edges = {}
    md_rel = ('Unit', 'MeleeDmg', 'Unit')
    if md_rel in obs['edges']:
        md_index = obs['edges'][md_rel]['index']
        md_attrs = obs['edges'][md_rel]['attrs']
        md_names = _edge_attr_names(md_rel)
        for e in range(md_index.shape[1]):
            src, dst = int(md_index[0, e]), int(md_index[1, e])
            dec = _decode_linnorm(md_attrs[e], md_names)
            md_edges[(src, dst)] = dec

    result = {}
    for raw in obs['active_action_ids']:
        action = int(raw)
        actor = units[actors[action]]
        kind = int(Action.decode_one(obs['nodes']['Action'][action]).ACTION_TYPE)
        affected = targets.get(action, [])
        ability = ((kind == ACTION_TYPES['AMOVE'] and actor.HAS_TWO_HEX_ATTACK_BREATH)
                   or (kind == ACTION_TYPES['SHOOT'] and actor.HAS_DEATH_CLOUD))
        primary = [u for u, p in affected if p]
        secondary = [u for u, p in affected if not p]
        est = md_edges.get((actors[action], primary[0])) if primary else None
        result[action] = dict(
            ability=bool(ability),
            actor_node=int(actors[action]),
            primary=primary, secondary=secondary,
            targets=sorted(u for u, _ in affected),
            enemy_targets=sum(bool(units[u].IS_ENEMY) for u, _ in affected),
            friendly_targets=sum(not units[u].IS_ENEMY for u, _ in affected),
            enemy_secondary=[u for u in secondary if units[u].IS_ENEMY],
            friendly_secondary=[u for u in secondary if not units[u].IS_ENEMY],
            coverage_value=sum((1 if units[u].IS_ENEMY else -1) * units[u].VALUE_REL
                               for u in sorted({u for u, _ in affected})),
            est_primary_net_rel_bf=(est or {}).get('ESTIMATED_NET_VALUE_REL_BF'),
            est_attacker_hp_rel_self=(est or {}).get('ESTIMATED_ATTACKER_HPDIFF_REL_SELF'),
        )
    return result


def _is_cloud_action(obs, action):
    """True if a legal action is a death-cloud SHOT (vs a breath AMOVE)."""
    kind = int(Action.decode_one(obs['nodes']['Action'][action]).ACTION_TYPE)
    if kind != ACTION_TYPES['SHOOT']:
        return False
    actors = {int(a): int(u) for a, u in obs['edges'][('Action', 'By', 'Unit')]['index'].T}
    node = actors.get(int(action))
    if node is None:
        return False
    return bool(Unit.decode_one(obs['nodes']['Unit'][node]).HAS_DEATH_CLOUD)


def choose(obs):
    """breath-exchange-v1 expert (dragon side)."""
    legal = [int(v) for v in obs['active_action_ids']]
    teacher = int(obs.get('teacher_action_id', -1))
    assert teacher in legal, 'depth-2 teacher must provide a mapped legal action'
    metrics = assess(obs)
    tfacts = metrics[teacher]
    teacher_is_breath = tfacts['ability']

    def score(a):
        m = metrics[a]
        s = 0.0
        if m['est_primary_net_rel_bf'] is not None:
            s += W_PRIMARY * m['est_primary_net_rel_bf'] / 1000.0
        s += W_SECONDARY * sum(_value_proxy(obs, u) for u in m['enemy_secondary']) / 1000.0
        s -= W_FRIENDLY * sum(_value_proxy(obs, u) for u in m['friendly_secondary']) / 1000.0
        if m['est_attacker_hp_rel_self'] is not None:
            s += W_ATTACKER_HP * m['est_attacker_hp_rel_self'] / 1000.0
        return s

    candidates = [a for a in legal if metrics[a]['ability']
                  and metrics[a]['primary']
                  and (metrics[a]['est_primary_net_rel_bf'] or 0) > 0]

    action = teacher
    override = False
    if not teacher_is_breath and candidates:
        best = max(candidates, key=lambda a: (score(a), -a))
        if score(best) > 0:
            action, override = best, True

    m = metrics[action]
    kind = 'cloud-exchange-v1' if (m['ability'] and action in legal
                                   and not m['primary'] == [] and metrics[action]['ability']
                                   and _is_cloud_action(obs, action)) else VERSION
    return action, dict(
        version=kind, selected=m, teacher_action=teacher, override=override,
        quality='provisional-visible-estimate-expert',
        limitations=PROXY_LIMITATIONS)


def _value_proxy(obs, node):
    from vcmi_gym.envs.v15.vcmi_env import Unit
    return Unit.decode_one(obs['nodes']['Unit'][node]).VALUE_REL * 1000.0


# ============================================================ retaliation bait
# Mechanism (event-verifiable): a stack can retaliate only a limited number of
# times per round; a low-value unit attacking first SOAKS the retaliation, so
# the high-value follow-up attack in the same round takes none. Native COUNTER
# events prove absorption vs non-absorption.

def _own_units_by_value(units):
    own = [i for i, u in enumerate(units) if not u.IS_ENEMY]
    own.sort(key=lambda i: -units[i].VALUE_REL)
    return own


def bait_choose(obs):
    """retaliation-bait-v1: low-value unit attacks the target that a more
    valuable own unit (still able to act) will attack in the same round.

    Legal actions only. No invented "refuse retaliation" action. Falls back to
    the depth-2 teacher when no bait opportunity exists.
    """
    legal = [int(v) for v in obs['active_action_ids']]
    teacher = int(obs.get('teacher_action_id', -1))
    units = Unit.decode_many(obs['nodes']['Unit'])
    metrics = assess(obs)
    own = _own_units_by_value(units)
    if not own:
        return teacher, dict(version='retaliation-bait-v1', quality='no-own-units')

    # future attackers of each enemy unit, from ALL action nodes in the graph
    # (a unit has action nodes only while it can still act this round)
    # NOTE: ("Action","By","Unit") edge index rows are (action_node, unit_node)
    action_actor = {int(action): int(unit)
                    for action, unit in obs['edges'][('Action', 'By', 'Unit')]['index'].T}
    targets_of = {}
    for rel in [('Unit', 'IsMeleedBy', 'Action'), ('Unit', 'IsShotBy', 'Action')]:
        if rel not in obs['edges']:
            continue
        for unit, action in obs['edges'][rel]['index'].T:
            targets_of.setdefault(int(action), set()).add(int(unit))

    enemy_attackers = defaultdict(set)  # enemy unit -> {own unit nodes}
    for action, actor_node in action_actor.items():
        actor = units[actor_node]
        if actor.IS_ENEMY:
            continue
        for tgt in targets_of.get(action, set()):
            enemy_attackers[tgt].add(actor_node)

    max_own_value = units[own[0]].VALUE_REL if own else 0

    def is_chaff(node):
        return units[node].VALUE_REL < 0.25 * max_own_value

    actor_node = None
    for a in legal:
        if metrics[a]['actor_node'] in own and not units[metrics[a]['actor_node']].IS_ENEMY:
            actor_node = metrics[a]['actor_node']
            break

    best_action, best_score = teacher, 0.0
    for a in legal:
        m = metrics[a]
        if not m['primary'] or actor_node is None or not is_chaff(actor_node):
            continue
        primary = m['primary'][0]
        if units[primary].IS_ENEMY is False:
            continue
        future = [u for u in enemy_attackers.get(primary, set())
                  if u != actor_node and units[u].VALUE_REL > units[actor_node].VALUE_REL]
        if not future:
            continue
        score = max(units[u].VALUE_REL for u in future)
        if score > best_score:
            best_action, best_score = a, score

    override = best_action != teacher and best_score > 0
    m = metrics[best_action if override else teacher]
    return (best_action if override else teacher), dict(
        version='retaliation-bait-v1', selected=m, teacher_action=teacher,
        override=override, bait_score=best_score,
        quality='provisional-visible-bait-heuristic',
        limitations='Baiting soaks a per-round retaliation with a low-value unit; '
                    'viability depends on the target having finite counterattacks '
                    '(native counterAttacks remaining is NOT visible; only past '
                    'COUNTER events are recorded). No refusal-of-retaliation action '
                    'exists or is invented. Waiting so a chaff unit can soak first '
                    'is NOT implemented in v1.')


def bait_counter_choose(obs):
    """retaliation-bait-counter-v1: kill the enemy bait before it soaks.

    When an enemy low-value unit is adjacent to (meleeable by) our high-value
    unit, prefer the legal action that attacks that low-value unit, so the
    enemy's high-value follow-up cannot enjoy a free (unretaliated) hit.
    Legal actions only; teacher fallback otherwise.
    """
    legal = [int(v) for v in obs['active_action_ids']]
    teacher = int(obs.get('teacher_action_id', -1))
    units = Unit.decode_many(obs['nodes']['Unit'])
    metrics = assess(obs)
    own = _own_units_by_value(units)
    if not own:
        return teacher, dict(version='retaliation-bait-counter-v1', quality='no-own-units')
    max_own_value = units[own[0]].VALUE_REL if own else 0

    actor_node = None
    for a in legal:
        if metrics[a]['actor_node'] in own:
            actor_node = metrics[a]['actor_node']
            break
    if actor_node is None:
        return teacher, dict(version='retaliation-bait-counter-v1', quality='no-own-actor')

    # enemy low-value units that our (high-value) actor can attack
    best_action, best_score = teacher, 0.0
    for a in legal:
        m = metrics[a]
        for tgt in m['primary']:
            if not units[tgt].IS_ENEMY:
                continue
            if units[tgt].VALUE_REL < 0.25 * max_own_value and units[actor_node].VALUE_REL > units[tgt].VALUE_REL:
                score = max_own_value - units[tgt].VALUE_REL
                if score > best_score:
                    best_action, best_score = a, score

    override = best_action != teacher and best_score > 0
    m = metrics[best_action if override else teacher]
    return (best_action if override else teacher), dict(
        version='retaliation-bait-counter-v1', selected=m, teacher_action=teacher,
        override=override, bait_score=best_score,
        quality='provisional-visible-bait-counter',
        limitations='Clears enemy chaff before it can soak retaliation. Does not '
                    'refuse retaliation (no such action exists) and does not use '
                    'spells. v1 only covers the melee-adjacent case.')


def counter_choose(obs):
    """dragon-threat-counter-v3 (side facing an enemy two-hex breather).

    Learned from v1/v2 paired failures:
      v1: identical to teacher (no differentiation => untested).
      v2: separation penalty made own breathers passive => harmful (0/24 wins).
    v3 is minimal and falsifiable: concentrate legal fire on the breather
    (choose, among legal actions that hit it, the one with the largest
    estimated defender HP loss); otherwise follow the teacher.
    No positional invention; every action still from active_action_ids.
    """
    legal = [int(v) for v in obs['active_action_ids']]
    teacher = int(obs.get('teacher_action_id', -1))
    units = Unit.decode_many(obs['nodes']['Unit'])
    metrics = assess(obs)

    breathers = {i for i, u in enumerate(units) if u.IS_ENEMY and u.HAS_TWO_HEX_ATTACK_BREATH}
    clouds = {i for i, u in enumerate(units) if u.IS_ENEMY and u.HAS_DEATH_CLOUD}
    threats = breathers | clouds

    md_rel = ('Unit', 'MeleeDmg', 'Unit')
    md_edges = {}
    if md_rel in obs['edges']:
        md_index = obs['edges'][md_rel]['index']
        md_attrs = obs['edges'][md_rel]['attrs']
        md_names = _edge_attr_names(md_rel)
        for e in range(md_index.shape[1]):
            src, dst = int(md_index[0, e]), int(md_index[1, e])
            md_edges[(src, dst)] = _decode_linnorm(md_attrs[e], md_names)

    def score(a):
        m = metrics[a]
        s = 0.0
        for t in threats:
            est = md_edges.get((m['actor_node'], t))
            if est and est.get('ESTIMATED_DEFENDER_HPDIFF_REL_SELF', 0) < 0:
                s += min(-est['ESTIMATED_DEFENDER_HPDIFF_REL_SELF'], 1000) / 10.0
        return s

    best = max(legal, key=lambda a: (score(a), -a))
    action = best
    override = False
    if teacher in legal and score(best) <= score(teacher):
        action = teacher
    elif teacher in legal:
        override = True
    m = metrics[action]
    return action, dict(
        version=COUNTER_VERSION, selected=m, teacher_action=teacher,
        quality='provisional-visible-threat-counter',
        limitations='Counter prioritizes legally hitting the breather with the '
                    'largest estimated defender HP loss; otherwise teacher. '
                    'No invented actions (no retaliation refusal, no spells).'
                    ' v1 no-op, v2 harmful; v3 minimal focus-fire variant.')

