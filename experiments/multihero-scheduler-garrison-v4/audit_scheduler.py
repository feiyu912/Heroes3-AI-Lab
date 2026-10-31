"""Independently recompute native garrison state and per-hero, per-turn motion."""
import json
from collections import Counter
from pathlib import Path
from audit_legacy import audit as old_audit, load_lines

def hero(state, hid):
    hits=[h for h in state['heroes'] if h['id']==hid]
    assert len(hits)==1, ('hero_identity',hid,len(hits))
    return hits[0]

def army_totals(state):
    total=Counter()
    seen=set()
    for obj in state['heroes']:
        assert obj['id'] not in seen
        seen.add(obj['id'])
        for cid,n in obj['army']: total[cid]+=n
    for town in state['towns']:
        if town['upper_army_id'] in seen: continue
        seen.add(town['upper_army_id'])
        for cid,n in town['army']: total[cid]+=n
    return total

def strict(work, probe, trace):
    checks={}
    def require(name, value):
        checks[name]=bool(value)
    setup={event:[(i,r) for i,r in enumerate(probe) if r['event']==event]
           for event in ('garrison_setup_requested','garrison_setup_sent','garrison_setup_ack')}
    require('one_native_setup_handshake',all(len(v)==1 for v in setup.values()))
    assert checks['one_native_setup_handshake'], 'setup handshake missing/duplicated'
    (ri,requested),(si,sent),(ai,ack)=[setup[x][0] for x in setup]
    require('setup_order_and_request_tuple',ri<si<ai and sent['request_id']>0 and sent['request_id']==ack['request_id'] and ack['result']==1 and all(x['hero']==3 for x in (requested,sent,ack)))
    require('setup_before_any_selection',all(i>ai for i,r in enumerate(probe) if r['event'] in ('scheduler_selected','move_sent')))
    before=[r for r in trace if r['event']=='garrison_setup_before']
    after=[r for r in trace if r['event']=='garrison_setup_ack_state']
    require('one_before_after_state',len(before)==len(after)==1)
    assert checks['one_before_after_state'],'setup states missing/duplicated'
    b,a=before[0],after[0]
    bh,ah=hero(b,3),hero(a,3)
    bt=[t for t in b['towns'] if t['id']==bh['town_id']]
    at=[t for t in a['towns'] if t['id']==ah['town_id']]
    assert len(bt)==len(at)==1,'town identity missing'
    bt,at=bt[0],at[0]
    require('native_visiting_to_real_positive_mp_garrison',
        bh['owner']==ah['owner']==bt['owner']==at['owner']==b['player']==a['player'] and
        bh['garrisoned'] is False and ah['garrisoned'] is True and
        bh['town_id']==ah['town_id']==bt['id']==at['id'] and
        bt['visitor_id']==3 and bt['garrison_id']==-1 and
        at['visitor_id']==-1 and at['garrison_id']==3 and at['upper_army_id']==3 and ah['movement']>0)
    require('setup_seven_resources_conserved',len(b['resources'])==7 and b['resources']==a['resources'])
    require('setup_hero_identity_position_mp_conserved',
        sorted((h['id'],h['owner'],h['x'],h['y'],h['z'],h['movement']) for h in b['heroes'])==
        sorted((h['id'],h['owner'],h['x'],h['y'],h['z'],h['movement']) for h in a['heroes']))
    require('setup_army_conserved_deduplicated',army_totals(b)==army_totals(a))
    require('setup_town_buildings_stock_conserved',
        sorted((t['id'],t['owner'],t['buildings'],t['available']) for t in b['towns'])==
        sorted((t['id'],t['owner'],t['buildings'],t['available']) for t in a['towns']))
    post=trace[trace.index(a):]
    require('garrison_remains_fixed',all(
        hero(r,3)['garrisoned'] is True and hero(r,3)['owner']==a['player'] and hero(r,3)['town_id']==ah['town_id'] and
        (hero(r,3)['x'],hero(r,3)['y'],hero(r,3)['z'])==(ah['x'],ah['y'],ah['z'])
        for r in post))
    require('garrison_town_reference_persists',all(
        len([t for t in r['towns'] if t['id']==ah['town_id'] and t['owner']==a['player'] and t['garrison_id']==3 and t['upper_army_id']==3])==1
        for r in post))
    selected=[r for r in probe if r['event']=='scheduler_selected']
    require('only_mobile_heroes_selected',bool(selected) and all(r['hero'] in (0,2) for r in selected))
    motion={}
    for turn in (1,2):
        for hid in (0,2):
            sent=[r for r in probe if r['event']=='move_sent' and r['hero']==hid and r['own_turn']==turn]
            pairs=[]
            for r in sent:
                matches=[x for x in probe if x['event']=='move_ack' and x['request_id']==r['request_id'] and x['hero']==hid]
                if len(matches)==1 and matches[0]['result']==1 and matches[0]['own_turn']==turn: pairs.append(r['request_id'])
            states=[hero(r,hid) for r in trace if r['own_turn']==turn]
            positions={(h['x'],h['y'],h['z']) for h in states}
            require(f'mobile_{hid}_turn_{turn}_native_motion', bool(pairs) and len(positions)>1 and all(h['owner']==a['player'] and h['garrisoned'] is False for h in states))
            motion[f'{hid}:{turn}']={'successful_requests':pairs,'positions':sorted(positions)}
    move_sent=[(r['hero'],r['request_id']) for r in probe if r['event']=='move_sent']
    move_ack=[(r['hero'],r['request_id']) for r in probe if r['event']=='move_ack']
    require('move_request_ack_bijection',len(set(move_sent))==len(move_sent) and Counter(move_sent)==Counter(move_ack))
    boundary=[(i,r) for i,r in enumerate(probe) if r['event']=='scheduler_quiescent_boundary']
    require('one_quiescent_boundary',len(boundary)==1)
    if len(boundary)==1:
        bi,br=boundary[0]
        require('boundary_no_pending_requests',br['pending_move']==0 and br['pending_queries']==0 and br['query_requests']==0 and br['own_turn']==2)
        require('no_action_after_boundary',not any(r['event'] in ('scheduler_selected','move_issued','move_sent','endturn_sent','close_sent','transfer_sent') for r in probe[bi+1:]))
    return checks,{'motion':motion,'setup_request_id':ack['request_id'],
                   'control_selections':[r for r in selected if r['hero']==3],
                   'setup_army_totals_before':dict(army_totals(b)),
                   'setup_army_totals_after':dict(army_totals(a))}

def audit(work):
    work=Path(work)
    result=old_audit(work)
    try:
        checks,detail=strict(work,load_lines(work/'probe.jsonl'),load_lines(work/'strategy-trace.jsonl'))
        result['strict_checks']=checks
        result['strict_detail']=detail
        result['blockers']+=['strict:'+name for name,ok in checks.items() if not ok]
    except Exception as error:
        result['blockers'].append('strict_audit_exception:'+repr(error))
    result['blockers']=sorted(set(result['blockers']))
    result['engineering_pass']=not result['blockers']
    result['controlled_boundary']='real native positive-MP garrison and each mobile hero moves in each of turns 1 and 2; garrison never selected'
    return result

if __name__=='__main__':
    import sys
    result=audit(Path(sys.argv[1]))
    print(json.dumps(result,indent=2))
