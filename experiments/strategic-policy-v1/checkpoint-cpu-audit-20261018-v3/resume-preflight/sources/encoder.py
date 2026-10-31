"""Player-visible strategic candidate encoding; no access to native hidden state."""
import math

SCHEMA = 'strategy-candidates-v2'
ENCODER_VERSION = 'strategy-visible-encoder-v1'
STATE_DIM = 11
CANDIDATE_DIM = 15
KINDS = ('enemy_hero', 'enemy_town', 'mine', 'pickup', 'reinforce', 'frontier')


def number(value, label, minimum=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'{label} must be finite numeric')
    if minimum is not None and value < minimum:
        raise ValueError(f'{label} must be >= {minimum}')
    return float(value)


def position(value, label):
    if isinstance(value, dict):
        value = [value[k] for k in ('x', 'y', 'z')]
    if not isinstance(value, (tuple, list)) or len(value) != 3:
        raise ValueError(f'{label} must contain x,y,z')
    return [number(v, label) for v in value]


def validate(request, expected_id=None):
    if not isinstance(request, dict) or request.get('schema') != SCHEMA:
        raise ValueError(f'Expected {SCHEMA}')
    request_id = request.get('request_id')
    if type(request_id) is not int or request_id < 1:
        raise ValueError('request_id must be a positive integer')
    if expected_id is not None and request_id != expected_id:
        raise ValueError('Filename/request_id mismatch')
    for key in ('player', 'day', 'hero', 'gold', 'wood', 'ore', 'own_army_value', 'movement'):
        number(request[key], key, 0)
    if request['player'] > 7:
        raise ValueError('Player outside native player range')
    position(request['from'], 'from')
    candidates = request.get('candidates')
    if not isinstance(candidates, list) or not candidates:
        raise ValueError('No legal candidates supplied')
    if len(candidates) > 16384:
        raise ValueError('Unexpected candidate count')
    for candidate in candidates:
        if type(candidate.get('kind')) is not int or not 0 <= candidate['kind'] < len(KINDS):
            raise ValueError('Unknown candidate kind')
        position(candidate['position'], 'candidate.position')
        position(candidate['next'], 'candidate.next')
        number(candidate['path_cost'], 'path_cost', 0)
        number(candidate['heuristic_score'], 'heuristic_score')
    return request


def encode(request):
    validate(request)
    origin = position(request['from'], 'from')
    scale_log = lambda x, limit: math.log1p(float(x)) / math.log1p(limit)
    state = [min(request['day'] / 28.0, 100.0), scale_log(request['gold'], 100000),
             scale_log(request['wood'], 1000), scale_log(request['ore'], 1000),
             scale_log(request['own_army_value'], 1000000), request['movement'] / 2500.0,
             origin[0] / 36.0, origin[1] / 36.0, origin[2] / 2.0,
             len(request['candidates']) / 64.0, request['player'] / 7.0]
    encoded = []
    for candidate in request['candidates']:
        target, step = position(candidate['position'], 'position'), position(candidate['next'], 'next')
        delta = [target[i] - origin[i] for i in range(3)]
        next_delta = [step[i] - origin[i] for i in range(3)]
        row = [float(candidate['kind'] == kind) for kind in range(len(KINDS))]
        row += [delta[0] / 36.0, delta[1] / 36.0, delta[2] / 2.0]
        row += [next_delta[0] / 36.0, next_delta[1] / 36.0, next_delta[2] / 2.0]
        row += [scale_log(candidate['path_cost'], 10000),
                math.tanh(candidate['heuristic_score'] / 100.0),
                math.hypot(delta[0], delta[1]) / 36.0]
        assert len(row) == CANDIDATE_DIM
        encoded.append(row)
    assert len(state) == STATE_DIM
    return state, encoded


def collate(requests, device='cpu'):
    import torch
    if not requests:
        raise ValueError('Empty batch')
    rows = [encode(request) for request in requests]
    width = max(len(candidates) for _, candidates in rows)
    state = torch.tensor([s for s, _ in rows], dtype=torch.float32, device=device)
    candidates = torch.zeros((len(rows), width, CANDIDATE_DIM), dtype=torch.float32, device=device)
    mask = torch.zeros((len(rows), width), dtype=torch.bool, device=device)
    for index, (_, features) in enumerate(rows):
        candidates[index, :len(features)] = torch.tensor(features, dtype=torch.float32, device=device)
        mask[index, :len(features)] = True
    return {'state': state, 'candidates': candidates, 'mask': mask}
