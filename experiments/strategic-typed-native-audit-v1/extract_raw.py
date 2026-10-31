"""Read-only strict typed trace extraction from one ordered raw client.log.

Fixture checks certify tooling only. No ACK or client JSON assertion is promoted
to service application; only the actual TypedActionApplied log marker is used.
"""
import argparse
import builtins
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import types

HERE=Path(__file__).resolve().parent
V3=HERE.parent/'strategic-policy-v3'


def isolated(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


broker=isolated('_raw_audit_typed_broker',V3/'broker.py')
core=types.ModuleType('_raw_audit_typed_events')
private=dict(vars(builtins));original=builtins.__import__
private['__import__']=lambda name,*args,**kwargs: broker if name=='broker' else original(name,*args,**kwargs)
core.__dict__['__builtins__']=private
exec(compile((V3/'audit_typed_execution.py').read_text(),str(V3/'audit_typed_execution.py'),'exec'),core.__dict__)
TYPED=re.compile(r'DirectorTypedEvent (\{.*\})\s*$')
SERVER=re.compile(r'TypedActionApplied player=(\d+) native_request_id=(\d+) op=(move|end_turn) success=([01])\s*$')
STEP=re.compile(r'DirectorAI: step finished result=(\d+) points_left=.* from .* to ')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def strict_json(raw):
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result:
                raise ValueError('Duplicate JSON key: '+key)
            result[key]=value
        return result
    return json.loads(raw,object_pairs_hook=unique,parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Nonfinite JSON '+value)))


def extract(client_log,typed_events,strategy_trace,move_decisions,agent,*,fixture=False):
    inputs={};errors=[];proofs=[];events=[];proposals=[];sent={};server_seen=set();move_results=[]
    def read(path):
        raw=path.read_bytes();inputs[str(path.resolve())]=sha(raw);return raw
    def require(condition,message):
        if not condition:
            raise ValueError(message)
    try:
        raw_lines=read(client_log).decode('utf-8',errors='replace').splitlines()
        typed_lines=read(typed_events).splitlines()
        declared=[strict_json(line) for line in typed_lines]
        legacy=[strict_json(line) for line in read(strategy_trace).splitlines()]
        moves=[strict_json(line) for line in read(move_decisions).splitlines()]
        for record in legacy:
            if record.get('event') in ('move_failed','economy_failed','query_failed','typed_protocol_error'):
                errors.append(dict(source='strategy_trace',error='Native failure',event=record))
        requests=sorted(agent.glob('request-*.json'))
        require(len(requests)>0 or not list(agent.glob('action-*.json')),'Actions without requests')
        for identity,path in enumerate(requests,1):
            require(path.name==f'request-{identity:08d}.json','Request sequence gap')
            raw=read(path);request=broker.encoder.validate(strict_json(raw),identity)
            response=strict_json(read(agent/f'action-{identity:08d}.json'))
            broker.validate_response(response,request,raw)
            proposals.append(dict(request=request,response=response,request_sha256=sha(raw),execution_verified=False,ppo_sample_admitted=False))
        by_decision={row['response']['decision_id']:row for row in proposals}
        logged=[];unbound_server=[];last_step=None
        for number,line in enumerate(raw_lines,1):
            if ('DirectorTypedProtocolError' in line or 'DirectorTypedResponseRejected' in line or
                'has to answer queries' in line or 'Got false in applying' in line or
                re.search(r'(?:QueryReply|query reply).*?(?:failed|success=0|result=0)',line,re.I)):
                errors.append(dict(source='client.log',line=number,error='Native rejection/protocol failure',text=line))
            step=STEP.search(line)
            if step:
                last_step=(number,int(step[1]))
            match=TYPED.search(line)
            if match:
                event=strict_json(match[1]);logged.append(event)
                require(event.get('event')!='server_action_applied','Client JSON cannot assert service application')
                if event.get('event')=='typed_protocol_error':
                    errors.append(dict(source='client.log',line=number,error='Typed protocol failed',event=event))
                if event.get('event')=='native_action_sent':
                    key=(event['player'],event['native_request_id'],event['op'])
                    require(key not in sent,'Duplicate native sent tuple')
                    sent[key]=(copy.deepcopy(event),number)
                elif event.get('event') in ('package_applied','move_result'):
                    key=(event['player'],event['native_request_id'],event['op'])
                    require(key in sent,'Client ACK/result has no preceding sent tuple')
                    action,source_line=sent[key]
                    immutable=core.BINDING+('selected_index','request_sha256','candidate')
                    require(all(event.get(field)==action.get(field) and type(event.get(field)) is type(action.get(field)) for field in immutable),'Client result changed saved context')
                    if event['event']=='move_result':
                        require(last_step is not None and source_line<last_step[0]<number and last_step[1]==event['result'],
                                'Move result lacks matching real native step-result log')
                        move_results.append(dict(native_request_id=event['native_request_id'],raw_line=last_step[0],event_line=number))
                        last_step=None
                event=dict(event,raw_client_line=number)
                events.append(event)
            service=SERVER.search(line)
            if service:
                player,identity,op,success=int(service[1]),int(service[2]),service[3],service[4]=='1'
                key=(player,identity,op)
                if key not in sent:
                    # Other players are logged in the same process. They are not
                    # evidence for DirectorAI. Own-player unbound events fail below.
                    unbound_server.append(dict(player=player,native_request_id=identity,op=op,line=number,text=line))
                    continue
                require(key not in server_seen,'Duplicate real server apply marker')
                server_seen.add(key);action,source_line=sent[key]
                require(source_line<number,'Service evidence preceded its requestSent binding')
                event={field:copy.deepcopy(action[field]) for field in core.BINDING}
                event.update(event='server_action_applied',source='server',success=success,raw_client_line=number)
                events.append(event)
                proofs.append(dict(kind='actual_server_apply',raw_client_line=number,text=line,
                                   native_request_id=identity,player=player,op=op,success=success,sent_line=source_line))
        require(logged==declared,'typed JSONL differs from ordered raw DirectorTypedEvent log')
        players={event['player'] for event in logged if 'player' in event}
        require(len(players)<=1,'Expected one DirectorAI player in this audit')
        own_unbound=[row for row in unbound_server if row['player'] in players]
        require(not own_unbound,'Own server marker lacks earlier exact native_action_sent; no reordering allowed')
        policy_moves=[row for row in events if row['event']=='native_action_sent' and row['op']=='move']
        require(len(policy_moves)==len(moves),'Move-only native decision count mismatch')
        for event,move in zip(policy_moves,moves):
            require(event['decision_id'] in by_decision,'Move missing policy proposal')
            proposal=by_decision[event['decision_id']];request=proposal['request'];response=proposal['response']
            candidate=request['candidates'][response['selected_index']]
            require(all(move.get(field)==request[field] for field in ('player','day','hero','from')),'Move decision context mismatch')
            require(move.get('selected_candidate')==response['selected_index'] and move.get('candidates')==request['candidates']
                    and move.get('destination')==candidate['position'] and move.get('step')==candidate['next'],
                    'Move actual destination/step/payload differs from proposed candidate')
        # Preserve the old final military visit exception, deriving every proof
        # from original raw lines, never solely from a gameOver or winner field.
        sent_moves=[event for event in events if event['event']=='native_action_sent' and event['op']=='move']
        terminals=[event for event in events if event['event']=='game_over']
        if sent_moves and terminals:
            action=sent_moves[-1];identity=action['native_request_id'];candidate=action['candidate']
            actual_result=any(event['event']=='move_result' and event['native_request_id']==identity for event in events)
            if not actual_result and candidate.get('kind') in (0,1) and candidate.get('next')==candidate.get('position'):
                service=movement=visit=outcome=None;hero_name=None
                start=action['raw_client_line'];end=terminals[-1]['raw_client_line']
                for number in range(start+1,end):
                    line=raw_lines[number-1]
                    if re.search(r'Player '+str(action['player'])+r' .*wants to move hero '+str(action['hero'])+r' from ',line):
                        service=number
                    match=re.search(r'Hero (.*?) starts movement from ',line)
                    if service and match:
                        movement=number;hero_name=match[1]
                    if hero_name and 'Hero '+hero_name+' visits ' in line:
                        visit=number
                    if visit and any(text in line for text in ('BattleResult','SetObjectProperty','ChangeObjectOwner')):
                        outcome=number;break
                if all(value is not None for value in (service,movement,visit,outcome)):
                    for kind,number in [('server_move_received',service),('hero_visit',visit),('battle_or_capture_outcome',outcome)]:
                        event={field:copy.deepcopy(action[field]) for field in core.BINDING}
                        event.update(event=kind,source='server',raw_client_line=number)
                        events.append(event)
                    proofs.append(dict(kind='terminal_military_visit',native_request_id=identity,hero_name=hero_name,
                        original_raw_lines=[dict(line=n,text=raw_lines[n-1]) for n in (service,movement,visit,outcome)],
                        target=candidate['position'],candidate_kind=candidate['kind']))
        events.sort(key=lambda event:event['raw_client_line'])
        report=core.audit(proposals,events,fixture=fixture)
        errors.extend(report['errors'])
        unchanged=all(sha(Path(path).read_bytes())==value for path,value in inputs.items())
        require(unchanged,'Raw inputs changed during read-only audit')
    except (ValueError,TypeError,KeyError,OSError) as error:
        errors.append(dict(source='extractor',error=str(error)))
        report={}
    report.update(valid=not errors,errors=errors,fixture_only=fixture,raw_evidence_crosschecked=not errors,
        real_execution_certified=False,independent_runtime_provenance_verified=False,
        ppo_samples_admitted=0,win=None,reward=None,input_sha256=inputs,raw_proofs=proofs,
        real_step_result_crosschecks=move_results,
        note='Raw log/trace/IO execution gate only. Native build/runtime freeze and actual-run provenance must be independently certified; fixture inputs prove tooling only.')
    return report,events,proposals


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('client-log','typed-events','strategy-trace','move-decisions','agent-dir','out'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--fixture-only',action='store_true')
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    report,events,proposals=extract(args.client_log,args.typed_events,args.strategy_trace,args.move_decisions,args.agent_dir,fixture=args.fixture_only)
    report['source_sha256']={str(path):sha(path.read_bytes()) for path in (Path(__file__),V3/'broker.py',V3/'encoder.py',V3/'audit_typed_execution.py')}
    for name,data in [('AUDIT.json',json.dumps(report,indent=2)+'\n'),
                      ('extracted-events.jsonl',''.join(json.dumps(row)+'\n' for row in events))]:
        broker.atomic(args.out/name,data.encode())
    print(json.dumps(dict(valid=report['valid'],fixture_only=report['fixture_only'],errors=report['errors'])))
    return 0 if report['valid'] else 1


if __name__=='__main__':
    raise SystemExit(main())
