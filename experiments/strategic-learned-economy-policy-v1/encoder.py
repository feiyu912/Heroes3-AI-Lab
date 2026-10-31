"""Strict schema5 build pilot; native legality remains native, never simulated here."""
import hashlib
import importlib.util
import math
from pathlib import Path

LEGACY_PATH = Path(__file__).resolve().parent.parent/'strategic-policy-v3/encoder.py'
LEGACY_SHA256 = '3c613ab07b3d3a4d09bef544c34883e2ba07c04d9114d55a929ebfbd9b4f5056'
if hashlib.sha256(LEGACY_PATH.read_bytes()).hexdigest() != LEGACY_SHA256:
    raise RuntimeError('Frozen movement encoder changed')
_spec = importlib.util.spec_from_file_location('_economy_frozen_move_encoder', LEGACY_PATH)
legacy = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(legacy)
SCHEMA = 'strategy-candidates-v5'
ENCODER_VERSION = 'strategy-learned-build-encoder-v1'
EPOCH = 'learned-economy-build-v1'
RESOURCES = ('wood', 'mercury', 'ore', 'sulfur', 'crystal', 'gems', 'gold')
CATEGORIES = ('income', 'dwelling', 'infrastructure')
OPS = ('move', 'end_turn', 'build')
STATE_DIM, CANDIDATE_DIM = 35, 43
OP_START, COST_START, FRACTION_START, CATEGORY_START = 40, 23, 30, 37
STATE_COUNT_CONVENTION = 'state[9]=number of nonbuild candidates/64; preserves frozen movement projection'

def integer(value, label, minimum=0):
    if type(value) is not int or value < minimum or value > 2**53-1:
        raise ValueError(label+' must be a bounded nonnegative integer')
    return value

def resources(value, label):
    if not isinstance(value, dict) or set(value) != set(RESOURCES):
        raise ValueError(label+' requires exactly seven named resources')
    return [integer(value[key], label+'.'+key) for key in RESOURCES]

def validate(request, expected_id=None):
    if not isinstance(request, dict) or request.get('schema') != SCHEMA or request.get('economy_epoch') != EPOCH:
        raise ValueError('Strict schema5/economy epoch required')
    if type(request.get('economy_window_open')) is not bool:
        raise ValueError('Explicit economy window required')
    res = resources(request.get('resources'), 'resources')
    for key in ('gold', 'wood', 'ore'):
        if integer(request.get(key), key) != request['resources'][key]:
            raise ValueError('Legacy resource alias mismatch')
    for key in ('request_id', 'own_turn', 'day'):
        integer(request.get(key), key, 1)
    for key in ('player', 'hero'):
        integer(request.get(key), key)
    towns = request.get('own_towns')
    if not isinstance(towns, list) or len(towns)>16384:
        raise ValueError('Explicit own towns required')
    by_id = {}
    for town in towns:
        if not isinstance(town, dict): raise ValueError('Invalid own town')
        tid = integer(town.get('town_id'), 'town_id')
        if tid in by_id: raise ValueError('Duplicate own town ID')
        integer(town.get('faction_id'), 'faction_id'); integer(town.get('built_today'), 'built_today')
        buildings = town.get('buildings')
        if not isinstance(buildings, list) or len(buildings)>16384: raise ValueError('Explicit buildings required')
        for bid in buildings: integer(bid, 'building_id')
        if buildings != sorted(set(buildings)): raise ValueError('Buildings must be sorted distinct IDs')
        by_id[tid]=town
    candidates = request.get('candidates')
    if not isinstance(candidates, list) or not 1<=len(candidates)<=16384: raise ValueError('Invalid candidate array')
    projected=[]; pairs=[]
    for item in candidates:
        if not isinstance(item, dict): raise ValueError('Candidate must be object')
        op=item.get('op')
        if op in ('move','end_turn'):
            expected={'op'} if op=='end_turn' else {'op','kind','position','next','path_cost','heuristic_score'}
            if set(item)!=expected: raise ValueError('Unexpected move/end_turn payload')
            projected.append(item)
        elif op=='build':
            if set(item)!={'op','actor','town_id','building_id','category','cost'} or item['actor']!='player_town':
                raise ValueError('Build requires exact town actor payload without move coordinates')
            tid=integer(item['town_id'],'build.town_id'); bid=integer(item['building_id'],'build.building_id')
            cost=resources(item['cost'],'cost')
            if (not request['economy_window_open'] or tid not in by_id or by_id[tid]['built_today']!=0
                    or bid in by_id[tid]['buildings'] or any(a>b for a,b in zip(cost,res))
                    or item['category'] not in CATEGORIES):
                raise ValueError('Inconsistent visible build facts')
            pairs.append((tid,bid))
        else: raise ValueError('Unknown candidate op')
    if pairs!=sorted(set(pairs)): raise ValueError('Build candidates must be sorted distinct town/building pairs')
    # This checks observations and movement syntax, not native construction prerequisites.
    if not projected: raise ValueError('At least genuine EndTurn or move required')
    legacy.validate(dict(request,schema=legacy.SCHEMA,candidates=projected),expected_id)
    return request

def encode(request):
    validate(request)
    projected=[c for c in request['candidates'] if c['op']!='build']
    state, oldrows=legacy.encode(dict(request,schema=legacy.SCHEMA,candidates=projected))
    scale=lambda v,limit: math.log1p(v)/math.log1p(limit)
    state += [scale(request['resources'][r],100000 if r=='gold' else 1000) for r in RESOURCES]
    state += [float(request['economy_window_open'])]
    oldrows=iter(oldrows); rows=[]
    for item in request['candidates']:
        row=[0.]*CANDIDATE_DIM; op=item['op']; row[OP_START+OPS.index(op)]=1.
        if op!='build': row[:23]=next(oldrows)[:23]
        else:
            row[COST_START:FRACTION_START]=[scale(item['cost'][r],100000 if r=='gold' else 1000) for r in RESOURCES]
            row[FRACTION_START:CATEGORY_START]=[item['cost'][r]/max(request['resources'][r],1) for r in RESOURCES]
            row[CATEGORY_START:CATEGORY_START+3]=[float(item['category']==c) for c in CATEGORIES]
        rows.append(row)
    assert len(state)==STATE_DIM and all(math.isfinite(x) for x in state)
    return state,rows

def collate(requests,device='cpu'):
    import torch
    if not requests: raise ValueError('Empty batch')
    rows=[encode(r) for r in requests]; width=max(len(c) for _,c in rows)
    state=torch.tensor([s for s,_ in rows],dtype=torch.float32,device=device)
    candidates=torch.zeros((len(rows),width,CANDIDATE_DIM),dtype=torch.float32,device=device)
    mask=torch.zeros((len(rows),width),dtype=torch.bool,device=device)
    for i,(_,features) in enumerate(rows):
        candidates[i,:len(features)]=torch.tensor(features,dtype=torch.float32,device=device); mask[i,:len(features)]=True
    return dict(state=state,candidates=candidates,mask=mask)
