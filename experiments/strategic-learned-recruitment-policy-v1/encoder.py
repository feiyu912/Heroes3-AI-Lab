"""Unqualified schema6 draft. Validate visible facts; never synthesize native legality."""
import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path

HERE=Path(__file__).resolve().parent
CONTRACT_PATH=HERE.parent/'strategic-learned-recruitment-native-v1/CONTRACT_DRAFT.md'
CONTRACT_SHA256='c3f432419bea862bfa1dcce051bd896ddcb9a5520963e161d3a6a864906c4af7'
if hashlib.sha256(CONTRACT_PATH.read_bytes()).hexdigest()!=CONTRACT_SHA256:
    raise RuntimeError('Recruit draft contract changed; review before updating the binding')
OLD=HERE.parent/'strategic-learned-economy-policy-v1/encoder.py'
if hashlib.sha256(OLD.read_bytes()).hexdigest()!='77210fd938d0e114e64f6d302f7749dc2a28e76c99e30d1a2488bd7afd02a259':
    raise RuntimeError('Frozen schema5 encoder changed')
spec=importlib.util.spec_from_file_location('_recruit_schema5_encoder',OLD)
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
SCHEMA='strategy-candidates-v6'
EPOCH='learned-economy-build-recruit-v1'
ENCODER_VERSION='schema6-recruit-encoder-draft-v1'
STATE_COUNT_CONVENTION='state[9]=number of move/end_turn candidates/64; excludes build and recruit to preserve legacy projection'
RESOURCES=old.RESOURCES
TOP_KEYS=set('schema request_id player own_turn own_hero_count day hero from gold wood ore own_army_value movement visible_threats economy_epoch economy_window_open resources own_towns candidates creature_catalog_sha256'.split())
RECRUIT_KEYS=set('op actor town_id destination_army_id destination_role creature_id amount level destination_slot quantity_bucket available affordable cost'.split())
STATE_KEYS=set('town_id owner built_today resources upper_army_id upper_army visitor recruit_stock'.split())
VOCAB_PATH=HERE/'creature_vocabulary.json'
VOCAB_SHA256=hashlib.sha256(VOCAB_PATH.read_bytes()).hexdigest()
vocabulary=json.loads(VOCAB_PATH.read_text())
if vocabulary['version']!='recruit-creature-vocabulary-draft-empty-v1' or vocabulary['creature_ids']!=[] or vocabulary['native_qualified'] is not False:
    raise ValueError('Draft supports only the explicitly unqualified empty vocabulary; changing vocabulary requires a new architecture')
CREATURE_IDS=tuple(vocabulary['creature_ids'])
BUCKETS=('one','half','affordable_all')
ROLES=('town','garrison_hero')
# Original 43 columns retain their exact indices. New op is column43.
# New-only columns: recruit op, quantity scalars(5), buckets(3), roles(2),
# stock-level categorical(8 incl UNK), actual destination-slot categorical(7),
# actor army facts(7), creature categorical(1 UNK in this unqualified draft).
EXTRA_DIM=34
STATE_DIM,CANDIDATE_DIM=35,43+EXTRA_DIM
INTEGER=old.integer

def exact(value,keys,label):
    if not isinstance(value,dict) or set(value)!=set(keys):raise ValueError(label+' exact keys required')

def army(value,label):
    if not isinstance(value,list) or len(value)!=7:raise ValueError(label+' requires seven actual slots')
    for slot,item in enumerate(value):
        if item is None:continue
        exact(item,{'slot','creature_id','count'},label)
        if INTEGER(item['slot'],label+'.slot')!=slot:raise ValueError('Army slot mismatch')
        INTEGER(item['creature_id'],label+'.creature_id');INTEGER(item['count'],label+'.count',1)

def project(request):
    result=copy.deepcopy(request);result['schema']=old.SCHEMA;result['economy_epoch']=old.EPOCH
    result['candidates']=[c for c in result['candidates'] if c.get('op')!='recruit']
    for town in result['own_towns']:town.pop('recruit_state',None)
    return result

def load_catalog(path,expected_sha256):
    """Strict runtime catalog bytes; this does NOT certify its capsule provenance."""
    raw=Path(path).read_bytes()
    if not isinstance(expected_sha256,str) or len(expected_sha256)!=64 or hashlib.sha256(raw).hexdigest()!=expected_sha256:
        raise ValueError('Runtime catalog SHA mismatch')
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result:raise ValueError('Duplicate catalog JSON key')
            result[key]=value
        return result
    value=json.loads(raw,object_pairs_hook=unique,parse_constant=lambda x:(_ for _ in ()).throw(ValueError('Nonfinite catalog')))
    exact(value,{'schema','entries'},'runtime catalog')
    if value['schema']!='strategy-runtime-creature-catalog-v1' or not isinstance(value['entries'],list) or not 1<=len(value['entries'])<=16384:
        raise ValueError('Nonempty runtime catalog required')
    ids=[];keys=[]
    for entry in value['entries']:
        exact(entry,{'creature_id','canonical_key'},'catalog entry')
        ids.append(INTEGER(entry['creature_id'],'catalog.creature_id'))
        key=entry['canonical_key']
        if not isinstance(key,str) or not key or len(key)>1024 or ':' not in key or any(ord(c)<32 for c in key):raise ValueError('Invalid canonical creature key')
        keys.append(key)
    if ids!=sorted(set(ids)) or len(keys)!=len(set(keys)):raise ValueError('Catalog IDs/keys must be distinct; IDs sorted')
    return dict(sha256=expected_sha256,ids=tuple(ids),keys=tuple(keys),runtime_provenance_qualified=False)

def require_training_catalog(catalog,qualification,offered_ids):
    """No standalone CPU fixture can satisfy the external native qualification."""
    raise ValueError('Draft training gate is unconditionally closed until actual capsule/catalog qualification is integrated')

def catalog_coverage(catalog,offered_ids):
    """Descriptive coverage only; never substitutes for native qualification."""
    ids=list(offered_ids);known=sum(cid in catalog['ids'] for cid in ids)
    if not ids or known==0:raise ValueError('All-unknown/empty actual recruit offer coverage is not trainable')
    return dict(known=known,total=len(ids),known_fraction=known/len(ids),unknown=len(ids)-known)

def validate(request,expected_id=None,catalog=None):
    exact(request,TOP_KEYS,'request')
    if request['schema']!=SCHEMA or request['economy_epoch']!=EPOCH or type(request['own_hero_count']) is not int or request['own_hero_count']!=1:
        raise ValueError('Strict schema6 singlehero epoch required')
    digest=request['creature_catalog_sha256']
    if not isinstance(digest,str) or len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest):raise ValueError('Explicit runtime catalog SHA required')
    if catalog is not None and digest!=catalog['sha256']:raise ValueError('Request/catalog binding mismatch')
    if (not isinstance(request['own_towns'],list) or not isinstance(request['candidates'],list)
            or not 1<=len(request['candidates'])<=16384 or any(not isinstance(c,dict) for c in request['candidates'])):raise ValueError('Invalid request arrays')
    old.validate(project(request),expected_id)
    towns={}
    for town in request['own_towns']:
        exact(town,{'town_id','faction_id','built_today','buildings','recruit_state','position','army_value'},'town')
        state=town['recruit_state'];exact(state,STATE_KEYS,'recruit_state')
        for key in ('town_id','owner','built_today','upper_army_id'):INTEGER(state[key],key)
        if (state['town_id']!=town['town_id'] or state['built_today']!=town['built_today']
                or state['resources']!=request['resources'] or state['owner']!=request['player']):
            raise ValueError('Inconsistent actor facts')
        old.resources(state['resources'],'town.resources');army(state['upper_army'],'upper_army')
        visitor=state['visitor']
        if visitor is not None:
            exact(visitor,{'hero_id','army_id','owner','army'},'visitor')
            for key in ('hero_id','army_id','owner'):INTEGER(visitor[key],'visitor.'+key)
            if visitor['hero_id']!=visitor['army_id']:raise ValueError('Visitor real army ID mismatch')
            army(visitor['army'],'visitor.army')
        stocks=state['recruit_stock']
        if not isinstance(stocks,list) or len(stocks)>16384:raise ValueError('Invalid stock array')
        for level,stock in enumerate(stocks):
            exact(stock,{'level','available','creature_ids'},'stock')
            if INTEGER(stock['level'],'stock.level')!=level:raise ValueError('Stock levels must match native array indices')
            INTEGER(stock['available'],'available')
            ids=stock['creature_ids']
            if not isinstance(ids,list) or len(ids)>16384:raise ValueError('Invalid native creature offers')
            for cid in ids:INTEGER(cid,'offered creature')
            # Native offer ordering is retained; duplicates are not assumed impossible.
        towns[town['town_id']]=state
    identities=[]
    for item in request['candidates']:
        if item['op']!='recruit':continue
        exact(item,RECRUIT_KEYS,'recruit')
        for key in ('town_id','destination_army_id','creature_id','level','destination_slot'):
            INTEGER(item[key],key)
        for key in ('amount','available','affordable'):INTEGER(item[key],key,1)
        state=towns.get(item['town_id'])
        if state is None or item['actor']!='player_town' or not request['economy_window_open']:
            raise ValueError('Invalid recruit actor/window')
        role='town' if state['upper_army_id']==item['town_id'] else 'garrison_hero'
        if item['destination_army_id']!=state['upper_army_id'] or item['destination_role']!=role or item['destination_slot']>6:
            raise ValueError('Recruit destination must be the actual upper army')
        level=item['level'];cid=item['creature_id'];amount=item['amount']
        if level>=len(state['recruit_stock']):raise ValueError('Unknown actual stock level')
        stock=state['recruit_stock'][level]
        if cid not in stock['creature_ids'] or item['available']!=stock['available']:raise ValueError('Recruit offer/stock mismatch')
        limit=min(item['available'],item['affordable'])
        quantities={1,max(1,limit//2),limit}
        bucket='one' if amount==1 else 'affordable_all' if amount==limit else 'half'
        if amount not in quantities or item['quantity_bucket']!=bucket:raise ValueError('Invalid deduplicated quantity bucket')
        cost=old.resources(item['cost'],'recruit.total_cost')
        if any(c>request['resources'][r] for c,r in zip(cost,RESOURCES)):raise ValueError('Unaffordable total cost')
        slot=state['upper_army'][item['destination_slot']]
        if slot is not None and slot['creature_id']!=cid:raise ValueError('Destination slot occupied by another creature')
        identities.append((item['town_id'],item['destination_army_id'],level,cid,amount))
    if len(identities)!=len(set(identities)):raise ValueError('Duplicate native recruit tuple')
    return request

def encode(request,catalog=None):
    validate(request,catalog=catalog)
    state,base=old.encode(project(request));iterator=iter(base);rows=[]
    towns={t['town_id']:t['recruit_state'] for t in request['own_towns']}
    scale=lambda value,limit:math.log1p(value)/math.log1p(limit)
    for item in request['candidates']:
        ids=catalog['ids'] if catalog else ()
        if item['op']!='recruit':rows.append(next(iterator)+[0.]*(EXTRA_DIM+len(ids)));continue
        row=[0.]*43
        row[23:30]=[scale(item['cost'][r],100000 if r=='gold' else 1000) for r in RESOURCES]
        row[30:37]=[item['cost'][r]/max(request['resources'][r],1) for r in RESOURCES]
        actor=towns[item['town_id']];slots=[s for s in actor['upper_army'] if s]
        visitor=actor['visitor'];vslots=[s for s in visitor['army'] if s] if visitor else []
        extra=[1.,scale(item['amount'],100000),scale(item['available'],100000),scale(item['affordable'],100000),item['amount']/item['available'],item['amount']/item['affordable']]
        extra += [float(item['quantity_bucket']==b) for b in BUCKETS]
        extra += [float(item['destination_role']==r) for r in ROLES]
        extra += [float(item['level']==level) for level in range(7)]+[float(item['level']>=7)]
        extra += [float(item['destination_slot']==slot) for slot in range(7)]
        extra += [len(slots)/7,scale(sum(s['count'] for s in slots),100000),scale(sum(s['count'] for s in slots if s['creature_id']==item['creature_id']),100000),float(visitor is not None),float(visitor is not None and visitor['owner']==request['player']),len(vslots)/7,scale(sum(s['count'] for s in vslots),100000)]
        extra += [float(item['creature_id']==cid) for cid in ids]+[float(item['creature_id'] not in ids)]
        assert len(extra)==EXTRA_DIM+len(ids)
        rows.append(row+extra)
    if not all(math.isfinite(v) for row in rows for v in row):raise ValueError('Nonfinite recruit features')
    return state,rows

def collate(requests,device='cpu',catalog=None):
    import torch
    if not requests:raise ValueError('Empty batch')
    encoded=[encode(q,catalog) for q in requests];width=max(len(rows) for _,rows in encoded)
    state=torch.tensor([s for s,_ in encoded],dtype=torch.float32,device=device)
    candidates=torch.zeros((len(encoded),width,CANDIDATE_DIM+(len(catalog['ids']) if catalog else 0)),dtype=torch.float32,device=device)
    mask=torch.zeros((len(encoded),width),dtype=torch.bool,device=device)
    for i,(_,rows) in enumerate(encoded):
        candidates[i,:len(rows)]=torch.tensor(rows,dtype=torch.float32,device=device);mask[i,:len(rows)]=True
    return dict(state=state,candidates=candidates,mask=mask)
