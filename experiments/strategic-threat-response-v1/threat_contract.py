"""CPU design prototype only. No game connection, native path creation or model."""
from dataclasses import dataclass
import math

RATIO=1.5
GRID_RADIUS=12
V3_KEYS={'schema','request_id','player','day','hero','gold','wood','ore',
         'own_army_value','movement','from','visible_threats','own_towns','candidates'}

def numeric(value):
    if type(value)not in (int,float)or not math.isfinite(value)or value<0:
        raise ValueError('Expected nonnegative finite number')
    return value

def point(value):
    if not isinstance(value,list)or len(value)!=3 or any(type(v)is not int for v in value):
        raise ValueError('Expected native integer coordinates')
    return value

def grid(a,b):
    return max(abs(a[0]-b[0]),abs(a[1]-b[1]))if a[2]==b[2]else None

def validate_v3(request):
    if not isinstance(request,dict)or request.get('schema')!='strategy-candidates-v3':
        raise ValueError('No implicit v3 upgrade')
    if set(request)!=V3_KEYS:raise ValueError('Missing or unexpected observation fields')
    for key in ('request_id','player','day','hero','gold','wood','ore','own_army_value','movement'):
        numeric(request[key])
    if type(request['request_id'])is not int or request['request_id']<1:raise ValueError('Invalid ID')
    point(request['from'])
    for name,value in (('visible_threats','approx_army_value'),('own_towns','army_value')):
        if not isinstance(request[name],list):raise ValueError('Explicit visible list required')
        for entry in request[name]:
            if set(entry)!={'position',value}:raise ValueError('Unexpected visible fields')
            point(entry['position']);numeric(entry[value])
    if not isinstance(request['candidates'],list)or not request['candidates']:raise ValueError('No native actions')
    for c in request['candidates']:
        if set(c)!={'kind','position','next','path_cost','heuristic_score'}:raise ValueError('Unexpected candidate fields')
        if type(c['kind'])is not int or not 0<=c['kind']<6:raise ValueError('v3 is move-only')
        point(c['position']);point(c['next']);numeric(c['path_cost'])
        if type(c['heuristic_score'])not in (int,float)or not math.isfinite(c['heuristic_score']):raise ValueError('Invalid score')
    return request

def release_gate(request):
    """Native would call BEFORE candidate collapse; archive output is diagnostic."""
    validate_v3(request)
    own=request['own_army_value']
    threats=[t for t in request['visible_threats']if t['approx_army_value']>=RATIO*max(1,own)
             and grid(request['from'],t['position'])is not None
             and grid(request['from'],t['position'])<=GRID_RADIUS]
    return dict(keep_full_native_candidates=bool(threats),trigger_count=len(threats),
                reason='visible_coordinate_pressure'if threats else'no_visible_coordinate_trigger',
                reachability_or_interception_proven=False)

def choose_existing_retreat_proxy(request,baseline_index):
    """Only rank the given native candidates. No candidate/path/hold fabrication."""
    active=release_gate(request)['keep_full_native_candidates']
    if type(baseline_index)is not int or not 0<=baseline_index<len(request['candidates']):raise ValueError('Illegal baseline')
    if not active:return baseline_index,'baseline_no_trigger'
    strong=[t for t in request['visible_threats']if t['approx_army_value']>=RATIO*max(1,request['own_army_value'])
            and grid(request['from'],t['position'])is not None]
    def clearance(position):return min(grid(position,t['position'])for t in strong)if position[2]==request['from'][2]else None
    base=request['candidates'][baseline_index];base_clear=clearance(base['next']);here=clearance(request['from'])
    if base_clear is None:return baseline_index,'baseline_other_layer_unmodelled'
    choices=[]
    for index,c in enumerate(request['candidates']):
        gap=clearance(c['next'])
        # Enemy attack and siege goals are never advertised as retreat choices.
        if c['kind']in (0,1)or gap is None or gap<here or gap<=base_clear:continue
        garrison=sum(t['army_value']for t in request['own_towns']if t['position']==c['position'])
        support=math.log1p(garrison/max(1,request['own_army_value']))/(1+c['path_cost'])
        choices.append(((gap,support,-c['path_cost'],-index),index))
    if not choices:return baseline_index,'baseline_no_better_existing_coordinate_option'
    return max(choices)[1],'existing_native_move_coordinate_proxy_only'


def validate_v4_action(candidate,*,from_pos,own_hero_count):
    """Proposed Phase B wire type. Not accepted by current broker/native."""
    op=candidate.get('op')
    if op=='move':
        required={'op','kind','position','next','path_cost','heuristic_score'}
        if set(candidate)!=required:raise ValueError('Malformed move')
        clone=dict(candidate);clone.pop('op')
        shell=dict(schema='strategy-candidates-v3',request_id=1,player=0,day=1,hero=0,gold=0,
                   wood=0,ore=0,own_army_value=1,movement=1,**{'from':from_pos},
                   visible_threats=[],own_towns=[],candidates=[clone])
        validate_v3(shell)
        return 'MoveHero' # Even a legitimate same-tile interaction is a move, never hold.
    if op=='end_turn':
        if set(candidate)!={'op','scope'}or candidate['scope']!='player':raise ValueError('No fake hold coordinates/path')
        if own_hero_count!=1:raise ValueError('Phase B pilot is explicitly single-hero only')
        return 'EndTurn'
    raise ValueError('Unknown action op')


@dataclass
class ExecutionContract:
    """Verifier state model, not a producer of fake server ACKs."""
    pending:tuple|None=None
    terminal:bool=False
    def sent(self,decision_id,native_request_id,pack_type):
        if self.terminal or self.pending is not None:raise ValueError('Blocked scheduling')
        if pack_type not in ('MoveHero','EndTurn'):raise ValueError('Unexpected pack')
        self.pending=(decision_id,native_request_id,pack_type)
        return dict(event='native_action_sent',decision_id=decision_id,native_request_id=native_request_id,pack_type=pack_type)
    def confirm(self,native_request_id,pack_type,*,server_received,server_applied,ack_success):
        if self.pending is None or self.pending[1:]!=(native_request_id,pack_type):raise ValueError('Wrong request/type ACK')
        if not(server_received and server_applied and ack_success):raise ValueError('No full native execution evidence')
        decision_id=self.pending[0];self.pending=None
        return dict(event='native_action_confirmed',decision_id=decision_id,pack_type=pack_type)
    def game_over(self):
        self.terminal=True
        # An outstanding action stays outstanding; victory is not execution proof.
    def settled(self):return self.pending is None
