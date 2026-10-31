"""Bind selected build, real pack, server result, resources and actual ACK.

Relative resource packets have no native request ID. They are accepted only in
the one outstanding build interval and replayed against its real before state.
"""
import json,re
RES=('wood','mercury','ore','sulfur','crystal','gems','gold')
BINDING=('decision_id','native_request_id','player','hero','own_turn','op','pack_type',
         'selected_index','request_sha256','candidate','classification','actor','town_id','building_id')
def need(ok,msg):
    if not ok:raise ValueError(msg)
def resources(value,signed=False):
    need(isinstance(value,dict) and set(value)==set(RES),'Exact seven-resource object required')
    need(all(type(v) is int and (signed or v>=0) for v in value.values()),'Malformed resources')
    return dict(value)
def town(value,player,tid):
    need(isinstance(value,dict) and set(value)=={'town_id','owner','built_today','buildings','resources'},'Exact town-state keys required')
    need(value['town_id']==tid and type(value['town_id']) is int and type(value['owner']) is int and value['owner']==player,'Town identity/owner mismatch')
    need(type(value['built_today']) is int and value['built_today']>=0,'Invalid native built counter')
    ids=value['buildings'];need(isinstance(ids,list) and all(type(i) is int and i>=0 for i in ids) and ids==sorted(set(ids)),'Invalid actual building set')
    resources(value['resources']);return value
def verify(raw,proposals,pack_mirror):
    selected={p['response']['decision_id']:p for p in proposals}
    turns=set()
    for p in proposals:
        q=p['request'];turn=(q['player'],q['own_turn'])
        need(q['economy_window_open']==(turn not in turns),'Build window is not the first actual policy choice')
        if p['response']['op']=='build':need(turn not in turns,'Second build or reopened economic window')
        turns.add(turn)
    bindings={};pending=None;pack_rows=[];reports=[]
    for number,text in enumerate(raw.splitlines(),1):
        line=re.sub(r'\x1b\[[0-9;]*m','',text)
        if 'DirectorTypedEvent ' in line:
            e=json.loads(line.split('DirectorTypedEvent ',1)[1]);kind=e['event']
            if kind=='native_action_sent':
                need(pending is None,'Next real policy action precedes actual build ACK')
                if e['op']!='build':continue
                identity=e['native_request_id'];need(identity not in bindings,'Reused actual build ID')
                p=selected[e['decision_id']];q=p['request'];c=q['candidates'][p['response']['selected_index']]
                need(e['candidate']==c and c['op']=='build' and e['actor']=='player_town','Selected build payload mismatch')
                need(e['town_id']==c['town_id'] and e['building_id']==c['building_id'],'Wrong build subject')
                actual=dict(pack_type='BuildStructure',player=e['player'],native_request_id=identity,town_id=c['town_id'],building_id=c['building_id'])
                need(e['actual_request']==actual,'Actual BuildStructure payload mismatch')
                before=town(e['before_state'],e['player'],c['town_id'])
                qt=[t for t in q['own_towns'] if t['town_id']==c['town_id']]
                need(len(qt)==1 and qt[0]['buildings']==before['buildings'] and qt[0]['built_today']==before['built_today'],'Published/pre-send town state changed')
                need(q['resources']==before['resources'] and c['building_id'] not in before['buildings'],'Stale resources or already built')
                expected={k:before['resources'][k]-resources(c['cost'])[k] for k in RES}
                need(all(v>=0 for v in expected.values()),'Unaffordable actual build')
                pending=dict(sent=e,line=number,before=before,resources=dict(before['resources']),expected=expected,
                    structures=set(),callbacks=set(),observed=False,ack_state=None,server=False,ack=False,pack_count=0)
                bindings[identity]=pending
            elif e.get('op')=='build' and kind in ('build_changed','build_ack_state','package_applied'):
                identity=e['native_request_id'];need(identity in bindings,'Unbound build observation')
                row=bindings[identity];s=row['sent']
                need(all(type(e[k]) is type(s[k]) and e[k]==s[k] for k in BINDING),'Changed immutable build tuple')
                need(pending is row and not row['ack'],'Build evidence outside outstanding interval')
                if kind=='build_changed':
                    state=town(e['state'],s['player'],s['town_id'])
                    need(type(e['what']) is int and e['what']==1 and type(e['observed_building_id']) is int and e['observed_building_id'] in state['buildings'],'Not an actual added building')
                    need(e['observed_building_id'] not in row['callbacks'],'Duplicate actual building callback')
                    row['callbacks'].add(e['observed_building_id'])
                    if e['observed_building_id']==s['building_id']:row['observed']=True
                elif kind=='build_ack_state':
                    need(row['ack_state'] is None,'Duplicate build ACK state')
                    need(row['server'],'Build ACK state precedes actual subject-bound server application')
                    state=town(e['state'],s['player'],s['town_id'])
                    need(row['observed'] and s['building_id'] in row['structures'],'Missing received NewStructures/callback')
                    need(state['resources']==row['resources']==row['expected'],'Actual resource packets/state/cost disagree')
                    need(set(state['buildings'])==set(row['before']['buildings'])|row['structures'],'Unexplained building state change')
                    need(state['built_today']==row['before']['built_today']+1,'Build daily counter mismatch')
                    row['ack_state']=state
                else:
                    need(row['server'] and e.get('success') is True and e.get('package')=='PackageApplied' and row['ack_state'] is not None,'Missing real successful PackageApplied/state')
                    row['ack']=True;pending=None
        elif 'DirectorBuildPack ' in line:
            e=json.loads(line.split('DirectorBuildPack ',1)[1]);pack_rows.append(e)
            if pending is None:continue
            s=pending['sent']
            if e['event']=='set_resources_received' and e['player']==s['player']:
                delta=resources(e['resources'],signed=True)
                need(type(e['mode']) is int and e['mode'] in (0,1),'Unknown native ChangeValueMode')
                pending['resources']={k:pending['resources'][k]+delta[k] if e['mode']==0 else delta[k] for k in RES}
                need(all(v>=0 for v in pending['resources'].values()),'Negative actual resources')
                pending['pack_count']+=1
            elif e['event']=='new_structures_received' and e['town_id']==s['town_id']:
                need(type(e['town_id']) is int and type(e['built_today']) is int,'Malformed NewStructures identity/counter')
                ids=e['buildings'];need(isinstance(ids,list) and ids==sorted(set(ids)) and all(type(i) is int and i>=0 for i in ids),'Malformed NewStructures payload')
                need(e['built_today']==pending['before']['built_today']+1,'Actual NewStructures daily counter mismatch')
                need(not (set(ids)&pending['structures']),'Duplicate actual NewStructures building')
                pending['structures'].update(ids)
        elif 'TypedBuildApplied ' in line:
            m=re.search(r'TypedBuildApplied player=(\d+) native_request_id=(\d+) town_id=(\d+) building_id=(\d+) success=([01])$',line)
            need(m is not None,'Malformed actual build application marker')
            player,identity,tid,bid,success=map(int,m.groups())
            if player!=proposals[0]['request']['player']:continue
            need(identity in bindings,'Unbound real server build')
            row=bindings[identity];s=row['sent']
            need(pending is row and not row['ack'],'Actual subject-bound server application after build ACK')
            need(not row['server'] and success==1 and (player,tid,bid)==(s['player'],s['town_id'],s['building_id']),'Duplicate/failed/wrong server BuildStructure')
            row['server']=True
    need(pack_rows==pack_mirror,'Raw received-pack log/file mirror mismatch')
    need(pending is None,'Build still outstanding at EOF')
    for identity,row in bindings.items():
        need(row['server'] and row['ack'] and row['observed'] and row['ack_state'] is not None,'Incomplete real build evidence')
        need(row['pack_count']>=1,'No actual resource packet for build')
        reports.append(dict(native_request_id=identity,decision_id=row['sent']['decision_id'],
            town_id=row['sent']['town_id'],building_id=row['sent']['building_id'],before=row['before'],after=row['ack_state']))
    need(len(reports)==sum(p['response']['op']=='build' for p in proposals),'Unconsumed policy builds')
    return dict(passed=True,policy_builds=len(reports),received_packets=len(pack_rows),builds=reports)

