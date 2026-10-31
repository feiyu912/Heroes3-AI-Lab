"""Strict visible-threat/supply observation. Coordinate risks are not path forecasts."""
import math

SCHEMA = 'strategy-candidates-v3'
ENCODER_VERSION = 'strategy-visible-threat-supply-encoder-v2'
LEGACY_STATE_DIM, LEGACY_CANDIDATE_DIM = 11, 15
KINDS = ('enemy_army', 'enemy_town', 'mine', 'pickup', 'reinforce', 'frontier')
STATE_ADDED_FEATURES = (
    'visible_enemy_hero_count_log', 'stronger_enemy_hero_count_log',
    'nearest_stronger_dx', 'nearest_stronger_dy', 'nearest_stronger_dz', 'nearest_stronger_coordinate_distance',
    'max_enemy_to_hero_army_logratio', 'own_town_count_log',
    'total_garrison_to_hero_logratio', 'max_garrison_to_hero_logratio',
    'nearest_own_town_dx', 'nearest_own_town_dy', 'nearest_own_town_dz', 'nearest_own_town_coordinate_distance',
    'max_visible_enemy_to_garrison_pressure')
CANDIDATE_ADDED_FEATURES = (
    'target_own_garrison_to_hero_logratio', 'target_nearest_stronger_coordinate_distance',
    'target_visible_enemy_pressure', 'next_nearest_stronger_coordinate_distance', 'next_visible_enemy_pressure',
    'target_nearest_own_town_coordinate_distance', 'next_nearest_own_town_coordinate_distance',
    'target_own_garrison_support_pressure')
STATE_DIM = LEGACY_STATE_DIM + len(STATE_ADDED_FEATURES)
CANDIDATE_DIM = LEGACY_CANDIDATE_DIM + len(CANDIDATE_ADDED_FEATURES)
DISTANCE_CONVENTION = 'sqrt(dx^2+dy^2+(36*dz)^2); /36 for distance features; no reachability/interception claim'


def number(value, label, minimum=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'{label} must be finite numeric')
    if minimum is not None and value < minimum:
        raise ValueError(f'{label} must be >= {minimum}')
    return float(value)


def position(value, label):
    if isinstance(value, dict):
        if not all(key in value for key in ('x', 'y', 'z')):
            raise ValueError(f'{label} must contain x,y,z')
        value = [value[key] for key in ('x', 'y', 'z')]
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ValueError(f'{label} must contain x,y,z')
    result = [number(item, label) for item in value]
    if any(abs(item) > 1000000 for item in result):
        raise ValueError(f'{label} outside supported coordinate range')
    return result


def validate(request, expected_id=None):
    if not isinstance(request, dict) or request.get('schema') != SCHEMA:
        raise ValueError(f'Expected strict {SCHEMA}; legacy observations must not silently become zero threats')
    for key in ('request_id', 'player', 'day', 'hero', 'gold', 'wood', 'ore', 'own_army_value',
                'movement', 'from', 'candidates', 'visible_threats', 'own_towns'):
        if key not in request:
            raise ValueError(f'Missing required visible observation field: {key}')
    identity = request['request_id']
    if type(identity) is not int or identity < 1 or (expected_id is not None and identity != expected_id):
        raise ValueError('Invalid or mismatched request_id')
    for key in ('player', 'day', 'hero', 'gold', 'wood', 'ore', 'own_army_value', 'movement'):
        number(request[key], key, 0)
    if request['player'] > 7:
        raise ValueError('Player outside native range')
    position(request['from'], 'from')
    candidates = request['candidates']
    if not isinstance(candidates, list) or not 1 <= len(candidates) <= 16384:
        raise ValueError('Expected nonempty bounded legal candidate array')
    for candidate in candidates:
        if not isinstance(candidate, dict) or type(candidate.get('kind')) is not int or not 0 <= candidate['kind'] < 6:
            raise ValueError('Invalid candidate kind')
        for key in ('position', 'next', 'path_cost', 'heuristic_score'):
            if key not in candidate:
                raise ValueError('Missing candidate field: ' + key)
        position(candidate['position'], 'candidate.position')
        position(candidate['next'], 'candidate.next')
        number(candidate['path_cost'], 'path_cost', 0)
        number(candidate['heuristic_score'], 'heuristic_score')
    for key, army_key in (('visible_threats', 'approx_army_value'), ('own_towns', 'army_value')):
        values = request[key]
        if not isinstance(values, list) or len(values) > 16384:
            raise ValueError(f'{key} must be a bounded explicit array; [] explicitly means none observed')
        for item in values:
            if not isinstance(item, dict) or 'position' not in item or army_key not in item:
                raise ValueError(f'{key} entry missing position or {army_key}')
            position(item['position'], key + '.position')
            if number(item[army_key], key + '.' + army_key, 0) > 1e18:
                raise ValueError('Visible army value outside supported numeric range')
    return request


def legacy_projection(request):
    """Explicit new-native baseline projection, never a new-model fallback."""
    validate(request)
    return dict(request, schema='strategy-candidates-v2')


def distance(a, b):
    return math.sqrt((a[0]-b[0]) ** 2 + (a[1]-b[1]) ** 2 + (36*(a[2]-b[2])) ** 2)


def ratio_feature(value, reference):
    return math.log1p(min(float(value) / max(float(reference), 1.), 1e6)) / math.log1p(100.)


def relative(target, origin):
    if target is None:
        return [0., 0., 0., 0.]
    return [(target[0]-origin[0])/36., (target[1]-origin[1])/36., (target[2]-origin[2])/2., distance(target, origin)/36.]


def encode(request):
    validate(request)
    origin = position(request['from'], 'from')
    scale_log = lambda value, limit: math.log1p(float(value)) / math.log1p(limit)
    # These prefixes exactly preserve v1 numerical transforms and ordering.
    state = [min(request['day']/28., 100.), scale_log(request['gold'], 100000),
             scale_log(request['wood'], 1000), scale_log(request['ore'], 1000),
             scale_log(request['own_army_value'], 1000000), request['movement']/2500.,
             origin[0]/36., origin[1]/36., origin[2]/2., len(request['candidates'])/64., request['player']/7.]
    threats = [(position(item['position'], 'threat'), item['approx_army_value']) for item in request['visible_threats']]
    towns = [(position(item['position'], 'town'), item['army_value']) for item in request['own_towns']]
    own = request['own_army_value']
    stronger = [(point, army) for point, army in threats if army > own]
    nearest = lambda points, source: min((point for point, _ in points),
        key=lambda point: (distance(point, source), tuple(point)), default=None)
    near_strong, near_town = nearest(stronger, origin), nearest(towns, origin)
    state += [scale_log(len(threats), 16), scale_log(len(stronger), 16)]
    state += relative(near_strong, origin)
    state += [ratio_feature(max((army for _, army in threats), default=0), own), scale_log(len(towns), 16),
              ratio_feature(sum(army for _, army in towns), own), ratio_feature(max((army for _, army in towns), default=0), own)]
    state += relative(near_town, origin)
    state += [max((ratio_feature(enemy, garrison) / (1 + distance(enemy_pos, town_pos)/6.)
                   for enemy_pos, enemy in threats for town_pos, garrison in towns), default=0.)]
    encoded = []
    for candidate in request['candidates']:
        target, step = position(candidate['position'], 'target'), position(candidate['next'], 'next')
        delta, next_delta = [target[i]-origin[i] for i in range(3)], [step[i]-origin[i] for i in range(3)]
        row = [float(candidate['kind'] == kind) for kind in range(6)]
        row += [delta[0]/36., delta[1]/36., delta[2]/2., next_delta[0]/36., next_delta[1]/36., next_delta[2]/2.]
        row += [scale_log(candidate['path_cost'], 10000), math.tanh(candidate['heuristic_score']/100.), math.hypot(delta[0], delta[1])/36.]
        nearest_distance = lambda points, source: min((distance(point, source)/36. for point, _ in points), default=0.)
        pressure = lambda source: max((ratio_feature(army, own)/(1+distance(point, source)/6.) for point, army in threats), default=0.)
        row += [ratio_feature(sum(army for point, army in towns if point == target), own),
                nearest_distance(stronger, target), pressure(target), nearest_distance(stronger, step), pressure(step),
                nearest_distance(towns, target), nearest_distance(towns, step),
                max((ratio_feature(army, own)/(1+distance(point, target)/6.) for point, army in towns), default=0.)]
        assert len(row) == CANDIDATE_DIM
        encoded.append(row)
    assert len(state) == STATE_DIM and all(math.isfinite(value) for value in state)
    assert all(math.isfinite(value) for row in encoded for value in row)
    return state, encoded


def collate(requests, device='cpu'):
    import torch
    if not requests:
        raise ValueError('Empty batch')
    rows = [encode(request) for request in requests]
    width = max(len(candidates) for _, candidates in rows)
    state = torch.tensor([state for state, _ in rows], dtype=torch.float32, device=device)
    candidates = torch.zeros((len(rows), width, CANDIDATE_DIM), dtype=torch.float32, device=device)
    mask = torch.zeros((len(rows), width), dtype=torch.bool, device=device)
    for index, (_, features) in enumerate(rows):
        candidates[index, :len(features)] = torch.tensor(features, dtype=torch.float32, device=device)
        mask[index, :len(features)] = True
    return dict(state=state, candidates=candidates, mask=mask)
