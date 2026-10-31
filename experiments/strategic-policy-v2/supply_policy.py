"""Visible-only reinforcement dispatch, fixed before any native v3 pilot.

choose(request, baseline_index) -> (legal candidate index, reason string).
No model, filesystem, event history, map name, side, seed, RNG or outcome input.
The threat metric is coordinate proximity, NOT native interception prediction.
Unknown/malformed optional information preserves the supplied legal baseline.
"""
import math

SCHEMA = 'strategy-candidates-v3'
VERSION = 'supply-aware-visible-v1'
MIN_REINFORCEMENT_RATIO = 0.25
MIN_DISPATCH_UTILITY = 0.60
RESELECT_MARGIN = 0.10
THREAT_RADIUS_TILES = 8.0
MAX_THREAT_PRESSURE = 3.0
MAX_STEP_EXPOSURE_INCREASE = 0.15


def _number(value):
    return (isinstance(value, (float, int)) and not isinstance(value, bool)
            and math.isfinite(value) and value >= 0)


def _position(value):
    return (isinstance(value, (tuple, list)) and len(value) == 3
            and all(_number(v) for v in value))


def _pressure(point, threats, own_value):
    """Max visible stronger-army proximity; other map levels do not interact."""
    pressures = [0.0]
    for enemy in threats:
        position = enemy['position']
        if position[2] != point[2]:
            continue
        excess = min(MAX_THREAT_PRESSURE, max(0.0, enemy['approx_army_value'] / own_value - 1.0))
        distance = math.hypot(position[0] - point[0], position[1] - point[1])
        pressures.append(excess * max(0.0, 1.0 - distance / THREAT_RADIUS_TILES))
    return max(pressures)


def choose(request, baseline_index):
    """Select only from the current candidate array; preserve unknown baselines.

    Utility = relative reinforcement / (0.5 + actual native path_cost), with
    bounded visible-threat urgency and next-step proximity adjustment. This
    estimates a dispatch preference; it is not a win probability or proof that
    the route/town is safe. Garrison size alone never forces a return.
    """
    if not isinstance(request, dict) or not isinstance(request.get('candidates'), list):
        raise ValueError('A real candidate array is required')
    candidates = request['candidates']
    if type(baseline_index) is not int or not 0 <= baseline_index < len(candidates):
        raise ValueError('Baseline index must identify a current legal candidate')
    fallback = (baseline_index, VERSION + ':baseline_unknown_or_unprofitable')
    if request.get('schema') != SCHEMA:
        return baseline_index, VERSION + ':baseline_schema_unsupported'
    own_value = request.get('own_army_value')
    origin = request.get('from')
    towns = request.get('own_towns')
    threats = request.get('visible_threats')
    baseline = candidates[baseline_index]
    if (not _number(own_value) or own_value <= 0 or not _position(origin)
            or not isinstance(towns, list) or not isinstance(threats, list)
            or not isinstance(baseline, dict) or not _position(baseline.get('next'))):
        return fallback
    if any(not isinstance(town, dict) or not _position(town.get('position'))
           or not _number(town.get('army_value')) for town in towns):
        return fallback
    if any(not isinstance(enemy, dict) or not _position(enemy.get('position'))
           or not _number(enemy.get('approx_army_value')) for enemy in threats):
        return fallback
    # Duplicate own-town positions are ambiguous, not additive extra troops.
    by_position = {tuple(town['position']): town['army_value'] for town in towns}
    if len(by_position) != len(towns):
        return fallback
    current_pressure = _pressure(origin, threats, own_value)
    baseline_pressure = _pressure(baseline['next'], threats, own_value)
    utilities = {}
    for index, candidate in enumerate(candidates):
        if (not isinstance(candidate, dict) or type(candidate.get('kind')) is not int
                or candidate['kind'] != 4 or not _position(candidate.get('position'))
                or not _position(candidate.get('next')) or not _number(candidate.get('path_cost'))):
            continue
        town_value = by_position.get(tuple(candidate['position']))
        if town_value is None or candidate['position'][2] != origin[2]:
            continue
        ratio = town_value / own_value
        if ratio < MIN_REINFORCEMENT_RATIO:
            continue
        step_pressure = _pressure(candidate['next'], threats, own_value)
        if step_pressure > max(current_pressure, baseline_pressure) + MAX_STEP_EXPOSURE_INCREASE:
            continue
        urgency = 1.0 + 0.5 * min(current_pressure, 1.0)
        # A bounded adjustment favors a less exposed next tile, never an oracle.
        safety_adjustment = max(-0.25, min(0.25, baseline_pressure - step_pressure))
        utility = ratio / (0.5 + candidate['path_cost']) * urgency + safety_adjustment
        if math.isfinite(utility):
            utilities[index] = utility
    if not utilities:
        return fallback
    best = max(utilities, key=lambda index: (utilities[index], -index))
    baseline_utility = utilities.get(baseline_index, 0.0)
    if best == baseline_index:
        return baseline_index, VERSION + ':baseline_already_preferred_supply'
    if utilities[best] < MIN_DISPATCH_UTILITY or utilities[best] <= baseline_utility + RESELECT_MARGIN:
        return fallback
    return best, VERSION + ':dispatch_value_cost_and_visible_proximity'
