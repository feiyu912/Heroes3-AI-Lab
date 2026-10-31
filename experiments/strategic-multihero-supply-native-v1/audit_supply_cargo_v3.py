"""Dedicated read-only partial supply mechanism audit; no schema4 policy proof.

Only completed real native transactions are certified. Synthetic gate tests are
never native certificates. An interrupted tail is retained and never rewarded.
"""
import argparse,collections,hashlib,json,re,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
ANSI=re.compile(r'\x1b\[[0-9;]*m')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def require(ok,why):
    if not ok:raise ValueError(why)

def army(state,identity):
    matches=[r for r in state['roster']+state['towns'] if r['id']==identity]
    require(len(matches)==1,'Army object missing/duplicate')
    slots=matches[0]['army'];require(len(slots)==7,'Seven army slots required')
    require(all(len(s)==2 and type(s[0]) is int and type(s[1]) is int and s[1]>=0 and (s[1]==0 or s[0]>=0) for s in slots),'Malformed army')
    return [(c if n else -1,n) for c,n in slots]

def parse(raw):
    records=[];regs={};acks={};actual={};sends={};lines=[]
    for n,text in enumerate(raw.splitlines(),1):
        line=ANSI.sub('',text);lines.append(line)
        if 'DirectorSupplyEvent ' in line:
            event=json.JSONDecoder().raw_decode(line.split('DirectorSupplyEvent ',1)[1])[0];records.append(dict(line=n,event=event))
        for prefix,target,pattern in [
          ('DirectorNativeRequestRegistered ',regs,r'DirectorNativeRequestRegistered id=(\d+) player=(\d+) pack_type=(\d+) type=(\S+)$'),
          ('DirectorNativeRequestAck ',acks,r'DirectorNativeRequestAck id=(\d+) player=(\d+) pack_type=(\d+) success=([01])$'),
          ('NativeRequestAck ',actual,r'(?<!Director)NativeRequestAck id=(\d+) player=(-?\d+) pack_type=(\d+) success=([01])$')]:
            if prefix in line and not (prefix=='NativeRequestAck ' and 'DirectorNativeRequestAck ' in line):
                m=re.search(pattern,line);require(m is not None,'Malformed '+prefix)
                identity,owner,kind=map(int,m.groups()[:3]);require(identity>0 and identity not in target,'Duplicate request ledger entry')
                target[identity]=dict(line=n,player=owner,pack_type=kind,tail=m[4])
        m=re.search(r'Sending a request "(\S+)"\. It.ll have an ID=(\d+)\.',line)
        if m:
            identity=int(m[2]);require(identity not in sends,'Duplicate actual client send');sends[identity]=dict(line=n,type=m[1])
    return records,regs,acks,actual,sends,lines

def native_gate(events,raw):
    records,regs,acks,actual,sends,lines=parse(raw)
    require([r['event'] for r in records]==events,'DirectorSupplyEvent/file mirror mismatch')
    require(events,'No supply events')
    require(not any(t in raw for t in ['DirectorTypedProtocolError','Got false in applying','has to answer queries','Script layer not found']),'Native protocol/visitor failure')
    roles=(events[0]['main'],events[0]['courier'],events[0]['home']);main,courier,home=roles
    require(main>=0 and courier>main and home>=0,'Invalid stable roles')
    pending=None;completed=[];tails=[];queries={};move_results={};turns=[];certified_state=None
    for identity,r in regs.items():
        require(r['player']==0 and identity in sends and sends[identity]['line']<r['line'] and sends[identity]['type']==r['tail'],'Owned registration/send identity mismatch')
    for identity,ack in actual.items():
        require(identity in sends and sends[identity]['line']<ack['line'],'Actual ACK without real prior send')
        require(ack['player'] in range(8) or (ack['player']==-1 and ack['pack_type']==198 and sends[identity]['type']=='10MakeAction'),'Unverified actual ACK owner')
        if ack['player']==0:require(identity in regs,'Owned actual ACK without Director registration')
    for identity,ack in acks.items():
        require(identity in regs and identity in actual,'Owned ACK missing registration/unified ACK')
        r,a=regs[identity],actual[identity]
        require(r['player']==ack['player']==a['player']==0 and r['pack_type']==ack['pack_type']==a['pack_type'] and ack['tail']==a['tail']=='1','Owned registry ACK identity/type/result mismatch')
        require(r['line']<a['line']<ack['line'],'Owned registry ACK ordering mismatch')
    for record_index,record in enumerate(records):
        event=record['event'];line=record['line'];name=event['event']
        require(event['schema']=='scripted-supply-events-v3' and event['controller_epoch']=='scripted-supply-cargo-v3' and event['policy_transition'] is False and event['player']==0,'Wrong explicit cargo event epoch/owner/learning claim')
        require((event['main'],event['courier'],event['home'])==roles,'Role/home drift')
        require({r['id'] for r in event['roster']}=={main,courier} and len(event['roster'])==2,'Real two-hero roster required')
        for identity in [main,courier,home]:army(event,identity)
        if name=='turn_start':
            require(event['query']<0 and event['pending'] is None,'New own turn has live scripted transaction')
            if record_index:
                previous=records[record_index-1]['event']
                require(event['phase']==previous['phase'] and event['cycles']==previous['cycles'],'Job phase/cycles reset across own turn')
            turns.append(dict(line=line,turn=event['own_turn'],event=event))
        if name=='exchange_open':
            q=event['query'];require(q>=0 and q not in queries,'Invalid/duplicate exchange query')
            queries[q]=dict(open_line=line,event=event)
        if name=='prepared':
            require(pending is None,'Second scripted pending request')
            require(event['pending'] is not None,'Prepared without command');pending=dict(prepared=event,line=line)
        if name=='real_move_result':
            require(pending is not None and pending['prepared']['pending']['op']==0,'Move result without pending move')
            require('move_result' not in pending,'Duplicate move result');pending['move_result']=record
        if name in ['native_sent','prompt_native_sent']:
            identity=event['native_request_id'];require(identity in regs and identity in sends,'Supply send missing real register/send')
            r,s=regs[identity],sends[identity]
            require(r['player']==0 and s['line']<r['line']<line,'Actual ID allocation/register/binding order invalid')
            require(r['tail']==s['type'],'Registered/transport type mismatch')
            payload=event.get('actual_request');require(isinstance(payload,dict),'Actual native payload observation required')
            require(payload['request_id']==identity and payload['player']==0 and payload['pack_type']==r['pack_type'],'Actual payload identity mismatch')
            if name=='prompt_native_sent':
                require('prompt' not in move_results and pending is None,'Second prompt/scripted pending')
                require(s['type']=='10QueryReply' and payload['op']=='QueryReply' and type(payload['query']) is int and payload['query']>=0 and type(payload['reply']) is int,'Prompt actual payload mismatch')
                move_results['prompt']=dict(event=event,line=line,payload=payload)
            else:
                require(pending is not None and 'id' not in pending,'Unprepared/rebound native request')
                c=pending['prepared']['pending'];require(event['pending']==c,'Prepared/sent command changed')
                kinds={0:'8MoveHero',1:'13ArrangeStacks',2:'10QueryReply',3:'7EndTurn'}
                require(s['type']==kinds[c['op']],'Command native type mismatch')
                require(payload['op']=={0:'MoveHero',1:'ArrangeStacks',2:'QueryReply',3:'EndTurn'}[c['op']],'Actual native operation mismatch')
                if c['op']==0:
                    require(payload['hero']==c['actor'] and len(payload['path'])==1 and payload['transit'] is False and type(payload['layer']) is int,'Move payload actor/path mismatch')
                if c['op']==1:
                    require(all(payload[k]==c[v] for k,v in [('source','source'),('target','target'),('from_slot','from_slot'),('to_slot','to_slot')]),'Transfer native payload mismatch')
                if c['op']==2:require(payload['query']==event['query'] and payload['reply']==0,'Exchange close payload mismatch')
                if c['op']==3:require(payload['scope']=='player','EndTurn must be player-wide')
                pending.update(id=identity,sent=event,sent_line=line,payload=payload)
        if name=='prompt_real_ack':
            transaction=move_results.pop('prompt',None);require(transaction is not None and transaction['event']['native_request_id']==event['native_request_id'],'Prompt ACK mismatch')
            # Prompt lifecycles are logged separately and cannot close a hero exchange.
            identity=event['native_request_id']
            if identity not in acks:
                tails.append(dict(id=identity,stage='prompt_callback_without_complete_actual_ACK_ledger'));continue
            require(acks[identity]['line']>line,'Prompt actual ACK ordering mismatch')
            segment=lines[transaction['line']:line-1]
            require(sum('Received CPack of type 10QueryReply' in s for s in segment)==1 and sum('Message 10QueryReply successfully applied!' in s for s in segment)==1,'Prompt server receive/application missing or ambiguous')
        if name=='real_ack':
            require(pending is not None and pending.get('id')==event['native_request_id'],'Unmatched supply real ACK')
            t=pending;pending=None;identity=t['id'];c=t['prepared']['pending'];op=c['op']
            require(event['pending']==c,'ACK command mismatch')
            if identity not in acks or identity not in actual:
                tails.append(dict(id=identity,stage='callback_seen_without_complete_actual_ACK_ledger'));continue
            require(t['sent_line']<line<actual[identity]['line'],'Supply callback ACK/actual ledger order mismatch')
            # Single scripted request interval excludes next callback-dispatched request.
            segment=lines[t['sent_line']:line-1];kind=sends[identity]['type']
            counts=[sum(token+kind+suffix in s for s in segment) for token,suffix in [('Received CPack of type ',''),('Sending a pack of type ',''),('Message ',' successfully applied!')]]
            if op in (1,2):require(counts==[1,1,1],f'Ambiguous/missing server receive/transport/visitor success id={identity} type={kind}')
            else:require(all(n>=1 for n in counts),f'Missing server receive/transport/visitor success id={identity}')
            if op in (0,3):
                marker=f'TypedActionApplied player=0 native_request_id={identity} op='+('move' if op==0 else 'end_turn')+' success=1'
                require(sum(marker in s for s in segment)==1,'Missing exact-ID real server application')
            detail=dict(id=identity,op=op,actor=c['actor'],own_turn=event['own_turn'],prepared_line=t['line'],sent_line=t['sent_line'],ack_line=line,actual_request=t['payload'])
            if op==0:
                require('move_result' in t,'Move ACK without native move result')
                before=next(h for h in t['prepared']['roster'] if h['id']==c['actor']);after=next(h for h in event['roster'] if h['id']==c['actor'])
                start=list(before['position']);start[0]+=1
                endpoint=t['payload']['path'][0]
                native_moves=[]
                for text in segment:
                    m=re.search(r': Hero .*? starts movement from \(([-\d ]+)\) to \(([-\d ]+)\)\.',text)
                    if m:native_moves.append(([int(n) for n in m[1].split()],[int(n) for n in m[2].split()]))
                require(native_moves.count((start,endpoint))==1,'Move payload not bound to actual server movement coordinates')
                detail.update(start=before['position'],end=after['position'],displaced=before['position']!=after['position'])
            if op==1:
                donor,recipient=c['source'],c['target'];db=army(t['prepared'],donor);rb=army(t['prepared'],recipient);da=army(event,donor);ra=army(event,recipient)
                i,j=c['from_slot'],c['to_slot'];require(i in range(7) and j in range(7),'Invalid transfer slot')
                creature,count=db[i];require(count>0 and (rb[j][1]==0 or rb[j][0]==creature),'Transfer would swap/incompatible')
                require(t['payload']['what']==(2 if rb[j][1] else 1),'Wrong transfer operation')
                expectedD=list(db);expectedR=list(rb);expectedD[i]=(-1,0);expectedR[j]=(creature,rb[j][1]+count)
                require(da==expectedD and ra==expectedR,'Actual seven-slot transfer delta/conservation mismatch')
                for other in {main,courier,home}-{donor,recipient}:require(army(t['prepared'],other)==army(event,other),'Other supply army changed during transfer')
                delivery=donor==courier and recipient==main;pickup=donor==home and recipient==courier
                require(delivery or pickup,'Transfer outside town/courier/main roles')
                if delivery:require(sum(n>0 for _,n in da)>=1 and event['query'] in queries and event['delivery_exchange'] is True,'Delivery lost reserve or real exchange')
                if pickup:require(next(t for t in event['towns'] if t['id']==home)['visitor']==courier,'Pickup without real visitor')
                detail.update(delivery=delivery,pickup=pickup,creature=creature,count=count,query=event['query'],donor_before=db,donor_after=da,recipient_before=rb,recipient_after=ra)
            if op==2:
                q=event['query'];require(q in queries and queries[q]['open_line']<t['sent_line'],'Close without real exchange')
                pop=[s for s in segment if 'Entering void QueriesProcessor::popQuery(PlayerColor, QueryPtr)' in s and '20CGarrisonDialogQuery' in s and f'qid = {q} ' in s]
                require(len(pop)==1 and sum(f'Destructed the query with id {q}' in s for s in segment)==1,'Missing actual exchange query pop/destruction')
                require(not any('Cannot remove, not a top!' in s for s in segment),'Failed query pop')
                queries[q]['closed_id']=identity;detail['query']=q
                detail['actual_query_pop_lines']=[t['sent_line']+i+1 for i,s in enumerate(segment) if 'QueriesProcessor::popQuery(PlayerColor, QueryPtr)' in s and '20CGarrisonDialogQuery' in s and f'qid = {q} ' in s]
                if record_index+1<len(records):
                    after=records[record_index+1]['event'];expected_cycles=event['cycles']+int(event['delivery_exchange'])
                    require(after['query']<0 and after['phase']!=3 and after['cycles']==expected_cycles,'Closed native query not reflected in subsequent controller lifecycle')
            completed.append(detail)
            certified_state=event
    if pending:tails.append(dict(id=pending.get('id'),stage='prepared_or_sent_without_real_ACK',command=pending['prepared']['pending']))
    if 'prompt' in move_results:tails.append(dict(id=move_results['prompt']['event']['native_request_id'],stage='prompt_without_real_ACK'))
    require(turns and turns[0]['turn']==1 and all(b['turn']==a['turn']+1 for a,b in zip(turns,turns[1:])),'Own turn lifecycle invalid')
    moves=[t for t in completed if t['op']==0 and t['displaced']]
    pickups=[t for t in completed if t.get('pickup')];deliveries=[t for t in completed if t.get('delivery')];closes=[t for t in completed if t['op']==2]
    related_closes=[c for c in closes if any(d['query']==c['query'] and d['ack_line']<c['ack_line'] for d in deliveries)]
    post=any(t['op']==0 and t['displaced'] and t['actor']==courier and t['ack_line']>min((c['ack_line'] for c in related_closes),default=10**20) for t in completed)
    later_turn_scheduling=any(m['own_turn']>turns[0]['turn'] for m in moves)
    generic=len(turns)>=2 and later_turn_scheduling and {m['actor'] for m in moves}=={main,courier} and bool(pickups and deliveries and related_closes) and post
    cargo=collections.Counter();cargo_delivered=collections.Counter();noncargo_delivered=collections.Counter()
    for t in completed:
        if t.get('pickup'):cargo[t['creature']]+=t['count']
        if t.get('delivery'):
            amount=min(cargo[t['creature']],t['count']);cargo[t['creature']]-=amount;cargo_delivered[t['creature']]+=amount;noncargo_delivered[t['creature']]+=t['count']-amount
    initial_reserve={c for c,n in army(events[0],courier) if n>0}
    final_courier=collections.Counter()
    for c,n in army(certified_state or events[0],courier):
        if n:final_courier[c]+=n
    reserve_retained=any(final_courier[c]>0 for c in initial_reserve)
    cargo_goal=bool(sum(cargo_delivered.values())>0 and not any(cargo.values()) and reserve_retained)
    return dict(native_prefix_contract_valid=True,partial_mechanism_qualified=generic and cargo_goal,generic_transfer_mechanisms_qualified=generic,cargo_goal_qualified=cargo_goal,
                initial_supply_snapshot=events[0],last_completed_transaction_snapshot=certified_state,final_observed_supply_snapshot=events[-1],
                cargo_delivered_by_creature=dict(cargo_delivered),undelivered_picked_up_cargo=dict(cargo),noncargo_delivered_by_creature=dict(noncargo_delivered),initial_reserve_creature_retained=reserve_retained,
                cargo_provenance_limitation='Counts are a supply-flow attribution; indistinguishable merged creatures are not individually tagged. Full picked-up cargo delivery and an initial reserve creature retained are required for this fixture goal.',
                completed_transactions=completed,incomplete_tail=tails,
                owned_registered_unacked_ids=sorted(set(regs)-set(acks)),open_exchange_queries=[q for q,e in queries.items() if 'closed_id' not in e],
                roles=dict(main=main,courier=courier,home=home),own_turns=[t['turn'] for t in turns],both_heroes_displaced={m['actor'] for m in moves}=={main,courier},
                pickup_transactions=len(pickups),delivery_transactions=len(deliveries),real_exchange_closures=len(closes),post_close_courier_move=post,later_own_turn_real_scheduling=later_turn_scheduling)

def ledger_map(value):
    require(isinstance(value,list),'Cargo ledger must be pair array')
    require(all(isinstance(p,list) and len(p)==2 and type(p[0]) is int and p[0]>=0 and type(p[1]) is int and p[1]>0 for p in value),'Invalid cargo ledger entry')
    require([p[0] for p in value]==sorted({p[0] for p in value}),'Duplicate/unsorted cargo ledger species')
    return collections.Counter(dict(value))

def slots(value):
    require(isinstance(value,list) and len(value)==7,'Cargo/reserve requires seven slots')
    require(all(isinstance(s,list) and len(s)==2 and type(s[0]) is int and type(s[1]) is int and s[1]>=0 and (not s[1] or s[0]>=0) for s in value),'Invalid reserve/cargo slot')
    return [(c if n else -1,n) for c,n in value]

def cargo_gate(events,native):
    """Rebuild cargo from actual pickup/delivery army deltas, never self-reported success."""
    courier=events[0]['courier'];main=events[0]['main'];home=events[0]['home']
    reserve_slots=army(events[0],courier);reserve=collections.Counter()
    for creature,count in reserve_slots:
        if count:reserve[creature]+=count
    require(bool(reserve),'Actual initial reserve absent')
    cargo_slots=[(-1,0)]*7;cargo=collections.Counter();picked=collections.Counter();delivered=collections.Counter()
    job_id=status=successful=incomplete=0;prepared=None;active=None;waiting=None;certificates=[];unconfirmed=[];updates=[]
    complete={t['id']:t for t in native['completed_transactions']}
    for index,e in enumerate(events):
        name=e['event'];j=e['job']
        require(all(type(j[k]) is int and j[k]>=0 for k in ['id','status','successful_jobs','incomplete_attempts']) and j['status'] in range(4),'Cargo lifecycle fields must be actual nonnegative integers')
        require(slots(j['initial_reserve_slots'])==reserve_slots and ledger_map(j['reserve'])==reserve,'Initial reserve identity/slot ledger changed')
        actual=army(e,courier)
        for slot,(creature,count) in enumerate(reserve_slots):
            if count:require(actual[slot][0]==creature and actual[slot][1]>=count,'Native courier initial reserve reduced/moved')
        if name=='prepared':prepared=e
        if name=='native_sent':
            require(prepared is not None,'Cargo native send without prepared snapshot');active=(e['native_request_id'],prepared)
        if name=='real_ack':
            require(active is not None and active[0]==e['native_request_id'] and waiting is None,'Cargo callback ACK identity mismatch')
            waiting=(active[0],active[1],e);active=None;prepared=None
        if name=='control_ack_applied':
            require(waiting is not None and waiting[0]==e['native_request_id'] and index>0 and events[index-1]['event']=='real_ack','Control update lacks immediately prior actual ACK callback')
            identity,before,ack=waiting;waiting=None;c=before['pending'];op=c['op']
            require(e['pending'] is None,'Control ACK failed to clear pending transaction')
            require(e['roster']==ack['roster'] and e['towns']==ack['towns'],'World changed between native ACK and ledger update')
            if op==1:
                db=army(before,c['source']);rb=army(before,c['target']);da=army(ack,c['source']);ra=army(ack,c['target']);i=c['from_slot'];k=c['to_slot'];creature,count=db[i]
                require(count>0 and (rb[k][1]==0 or rb[k][0]==creature),'Cargo transfer not compatible')
                expectedD=list(db);expectedR=list(rb);expectedD[i]=(-1,0);expectedR[k]=(creature,rb[k][1]+count)
                require(da==expectedD and ra==expectedR,'Cargo ledger update not backed by actual seven-slot delta')
                if c['source']==home and c['target']==courier:
                    if not cargo and status in (0,2):job_id+=1;picked.clear();delivered.clear()
                    picked[creature]+=count;cargo[creature]+=count;status=1
                    require(cargo_slots[k][1]==0 or cargo_slots[k][0]==creature,'Cargo slot species changed')
                    cargo_slots[k]=(creature,cargo_slots[k][1]+count)
                else:
                    require(c['source']==courier and c['target']==main and cargo_slots[i]==db[i] and cargo[creature]>=count,'Delivery includes reserve/unacknowledged or mixed cargo')
                    cargo[creature]-=count
                    if not cargo[creature]:del cargo[creature]
                    cargo_slots[i]=(-1,0);delivered[creature]+=count
                updates.append(dict(id=identity,op=op,job=job_id,creature=creature,count=count,certified_native_transaction=identity in complete))
            if op==2 and ack['delivery_exchange']:
                success=bool(picked and not cargo and picked==delivered)
                if success:
                    status=2;successful+=1
                    entry=dict(job_id=job_id,close_request_id=identity,picked=dict(picked),delivered=dict(delivered),query=ack['query'])
                    if identity in complete and all(u['certified_native_transaction'] for u in updates if u['job']==job_id):certificates.append(entry)
                    else:unconfirmed.append(entry)
                else:status=3;incomplete+=1
            require(j['id']==job_id and j['status']==status,'Reported cargo job lifecycle differs from reconstructed native flow')
        require(ledger_map(j['picked'])==picked and ledger_map(j['cargo_remaining'])==cargo and ledger_map(j['delivered'])==delivered,'Reported cargo totals changed without actual pickup/delivery ACK')
        require(slots(j['cargo_slots'])==cargo_slots,'Reported cargo slot attribution differs from native deltas')
        slot_totals=collections.Counter()
        for creature,count in cargo_slots:
            if count:slot_totals[creature]+=count
        require(slot_totals==cargo and picked==cargo+delivered,'Cargo slot/species or picked/delivered conservation mismatch')
        require(j['id']==job_id and j['status']==status and j['successful_jobs']==successful and j['incomplete_attempts']==incomplete and j['success'] is (status==2),'Unproven/early self-reported cargo success or ledger state')
        if name!='real_ack':
            actual_totals=collections.Counter()
            for creature,count in actual:
                if count:actual_totals[creature]+=count
            require(all(actual_totals[c]>=count for c,count in (reserve+cargo).items()),'Native total army lacks reserved plus acknowledged cargo counts')
            for i,(creature,count) in enumerate(cargo_slots):
                if count:require(actual[i][0]==creature and actual[i][1]>=count+reserve_slots[i][1],'Native cargo contribution/initial reserve missing')
    return dict(independent_cargo_ledger_valid=True,slot_and_species_conservation_both_verified=True,certified_successful_jobs=certificates,unconfirmed_close_jobs=unconfirmed,
                reconstructed_job_id=job_id,reconstructed_status=status,reconstructed_successful_jobs=successful,reconstructed_incomplete_attempts=incomplete,
                reserve_slots=reserve_slots,reserve=dict(reserve),picked=dict(picked),cargo_remaining=dict(cargo),delivered=dict(delivered),cargo_slots=cargo_slots,
                native_ACK_backed_ledger_updates=updates,unfinished_control_update_request_id=None if waiting is None else waiting[0])

def gate(events,raw):
    native=native_gate(events,raw);ledger=cargo_gate(events,native)
    records=parse(raw)[0]
    for tail in native['incomplete_tail']:
        if tail['id'] is not None:
            anchors=[r['line'] for r in records if r['event']['native_request_id']==tail['id'] and r['event']['event']=='real_ack']
            if anchors:require(not any(t['ack_line']>min(anchors) for t in native['completed_transactions']),'Missing middle ACK ledger entry is not an interrupted EOF prefix')
    native.update(ledger)
    def counts(e,identity):
        result=collections.Counter()
        for creature,count in army(e,identity):
            if count:result[creature]+=count
        return dict(result)
    first=events[0];last=native['last_completed_transaction_snapshot'];m,c,h=first['main'],first['courier'],first['home']
    fixture_flow=last is not None and counts(first,m)=={0:5} and counts(first,c)=={2:3} and counts(first,h)=={0:10} and counts(last,m)=={0:15} and counts(last,c)=={2:3} and counts(last,h)=={}
    native['fixture_cargo_flow_qualified']=fixture_flow
    native['cargo_goal_qualified']=bool(ledger['certified_successful_jobs']) and fixture_flow
    native['partial_mechanism_qualified']=native['generic_transfer_mechanisms_qualified'] and native['cargo_goal_qualified']
    return native

def audit(root):
    plan=json.loads((root/'PLAN.json').read_text());execution=json.loads((root/'EXECUTION.json').read_text())
    require(plan['schema']=='scripted-supply-cargo-native-probe-v2' and plan['execute'] is True and plan['scripted_only'] is True,'Wrong native cargo probe plan')
    require(plan['game_score_eligible'] is False and plan['restoration_qualified'] is False,'Invalid whole-game/recovery claim')
    require(execution['input_sha_unchanged'] and execution['thread_server_verification']['passed'],'Missing actual input/thread verification')
    require(execution['loaded_library_observations'] and all(e['valid'] for e in execution['loaded_library_observations']),'Missing actual binary load proof')
    require(all(sha(Path(p))==h for p,h in plan['hashes'].items()),'Frozen input changed')
    cap=Path(plan['capsule']);candidate=Path(plan['candidate_root']);manifest=json.loads((candidate/'CANDIDATE_MANIFEST.json').read_text());att=json.loads((cap/'EXECUTION.json').read_text());sources=json.loads((cap/'build-source-manifest.json').read_text())
    require(manifest['schema']=='scripted-supply-native-candidate-v3' and manifest['controller_epoch']=='scripted-supply-cargo-v3' and manifest['observability_revision']==3,'Wrong compiled cargo controller epoch')
    require(att['passed'] and att['accepted_binaries_restored'] and len(manifest['files'])==11,'Unproven supply capsule')
    require(all(sha(cap/p)==h for p,h in att['candidate_artifacts'].items()),'Compiled artifact changed')
    for p,e in manifest['files'].items():require(sha(candidate/'candidate'/p)==sha(cap/'source-snapshot'/p)==sources[p]['sha256']==e['candidate_sha256'],'Native payload/source mismatch')
    scripts=[p for p in (root/'scripts').rglob('*') if p.is_file()]
    require(len(scripts)==41 and {str(p.relative_to(root)) for p in scripts}=={p for p in sources if p.startswith('scripts/') and 'sha256' in sources[p]},'Full 41-script source closure missing')
    require(all(sha(p)==sources[str(p.relative_to(root))]['sha256']==plan['hashes'][str(p)] for p in scripts),'Native script source binding mismatch')
    require(all(plan['hashes'][str(cap/p)]==h for p,h in att['candidate_artifacts'].items()),'Compiled artifacts not frozen in run input')
    support=HERE.parent/'multihero-mechanism-probe-v1/build-driver-frozen-03'
    sys.path.insert(0,str(support));from capsule_support import thread_server_gate
    require(thread_server_gate(execution['loaded_library_observations'],(root/'client.log').read_text(errors='replace'),False)==execution['thread_server_verification'],'Actual thread server gate differs')
    raw=(root/'client.log').read_text(errors='replace');events=[json.loads(s) for s in (root/'supply.jsonl').read_text().splitlines()]
    require(not list(root.rglob('request-*.json')) and not list(root.rglob('action-*.json')),'Supply probe emitted policy data')
    result=gate(events,raw)
    result.update(passed=result['partial_mechanism_qualified'],fixture=False,new_native_games=0,game_completed=False,winner=None,global_transport_drained=False,restoration_qualified=False,
                  training_samples=0,optimizer_steps=0,expert_labels=0,stop_reason=execution.get('stop_reason'),native_exit=execution.get('native_exit'),
                  input_sha256={**plan['hashes'],**{str(p):sha(p) for p in [root/'PLAN.json',root/'EXECUTION.json',root/'client.log',root/'supply.jsonl',Path(__file__),support/'capsule_support.py']}},
                  limitation='Completed transaction prefix only. Unfinished tail and unacked owned/native BattleAI requests are preserved, not certified successful, scored or used for learning. No full game, safe save boundary, restore or benefit claim.')
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    try:r=audit(a.run)
    except Exception as e:r=dict(passed=False,error=repr(e),game_completed=False,winner=None,training_samples=0,optimizer_steps=0)
    (a.out/'AUDIT.json').write_text(json.dumps(r,indent=2));print(json.dumps({k:v for k,v in r.items() if k not in ['completed_transactions','input_sha256','initial_supply_snapshot','final_observed_supply_snapshot','last_completed_transaction_snapshot']},indent=2));return 0 if r['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
