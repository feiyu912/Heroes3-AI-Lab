"""Strict proposed native event contract audit. CPU fixtures are never real execution evidence."""
import argparse
import copy
import json
from pathlib import Path

from broker import validate_response,atomic,digest

BINDING=('decision_id','native_request_id','player','hero','own_turn','op','pack_type')
BUSY=('movement_busy','economy_busy','battle_busy')


def audit(proposals,events,*,fixture=False):
    errors=[];pending={};decisions={};current={};busy={};ended=set();consumed=set();terminal=None
    counts=dict(policy_moves=0,policy_end_turns=0,automatic_end_turns=0,late_end_turn_acks=0,
                diagnostic_decisions=0,new_policy_decisions=0,blocking_visits=0)
    def integer(value,minimum=0):
        return type(value) is int and value>=minimum
    def require(condition,message):
        if not condition:
            raise ValueError(message)
    for proposal in proposals:
        try:
            request=proposal['request'];response=proposal['response']
            # Bytes cannot be reconstructed from JSON canonicalization. The IO
            # wrapper verifies exact bytes; here the original byte SHA is binding.
            require(response['schema']=='strategy-typed-action-response-v1','Wrong response schema')
            identity=response['decision_id']
            require(integer(identity,1) and identity not in decisions,'Duplicate/invalid policy decision')
            require(response['request_sha256']==proposal['request_sha256'],'Proposal SHA mismatch')
            from broker import encoder,RESPONSE_KEYS
            encoder.validate(request,identity)
            require(set(response)==RESPONSE_KEYS,'Wrong response key set')
            require(all(type(response[key]) is int and response[key]==request[key] for key in ('player','hero','own_turn')),'Policy context mismatch')
            index=response['selected_index']
            require(integer(index) and index<len(request['candidates']),'Bad selected index')
            require(response['op']==request['candidates'][index]['op'],'Policy op mismatch')
            require(response['classification'] in ('diagnostic_only','new_policy'),'Unknown proposal provenance')
            decisions[identity]=proposal
        except (ValueError,KeyError,TypeError) as error:
            errors.append(dict(phase='proposal',error=str(error)))
    for number,event in enumerate(events,1):
        try:
            kind=event['event']
            if kind in ('move_failed','economy_failed','query_failed','server_rejected'):
                raise ValueError('Native failure '+kind)
            if kind=='your_turn':
                player,turn=event['player'],event['own_turn']
                require(integer(player) and player<=7 and integer(turn,1),'Invalid turn identity')
                require(turn==current.get(player,0)+1,'Nonsequential own turn')
                current[player]=turn
            elif kind=='busy_state':
                player,turn=event['player'],event['own_turn']
                require(current.get(player)==turn,'Busy snapshot has wrong turn')
                require(integer(event['query_count']) and all(type(event[key]) is bool for key in BUSY),'Malformed busy snapshot')
                busy[player,turn]=copy.deepcopy(event)
            elif kind=='native_action_sent':
                require(terminal is None,'Action sent after native terminal')
                identity=event['native_request_id'];player=event['player'];turn=event['own_turn']
                require(integer(identity,1) and identity not in pending,'Reused or invalid native request ID')
                require(integer(player) and integer(event['hero']) and integer(turn,1),'Invalid action identity')
                require(current.get(player)==turn and (player,turn) not in ended,'Action outside current active own turn')
                require(event['op'] in ('move','end_turn') and event['pack_type']==('EndTurn' if event['op']=='end_turn' else 'MoveHero'),'Wrong op/pack')
                snapshot=busy.get((player,turn))
                require(snapshot is not None,'Missing pre-action busy state')
                require(snapshot['query_count']==0 and not any(snapshot[key] for key in BUSY),'Action sent before Query/Move/Economy/Battle drained')
                require(not any(row['sent']['player']==player and row['sent']['own_turn']==turn and not row['complete'] for row in pending.values()),'Unresolved same-turn action')
                decision=event['decision_id']
                if decision is None:
                    require(event['op']=='end_turn' and event.get('selected_index') is None and event.get('request_sha256') is None
                            and event['candidate']=={'op':'end_turn'} and isinstance(event.get('automatic_reason'),str)
                            and bool(event['automatic_reason'].strip()),'Malformed automatic EndTurn')
                    counts['automatic_end_turns']+=1
                else:
                    require(integer(decision,1) and decision in decisions and decision not in consumed,'Unknown/reused policy decision')
                    proposal=decisions[decision];response=proposal['response'];request=proposal['request']
                    require(all(event[key]==response[key] for key in ('decision_id','player','hero','own_turn','op','selected_index','request_sha256')),'Native consumption context mismatch')
                    require(event['candidate']==request['candidates'][response['selected_index']],'Native selected payload mismatch')
                    consumed.add(decision)
                    counts['policy_end_turns' if event['op']=='end_turn' else 'policy_moves']+=1
                    counts['diagnostic_decisions' if response['classification']=='diagnostic_only' else 'new_policy_decisions']+=1
                pending[identity]=dict(sent=copy.deepcopy(event),line=number,server_applied=False,ack=False,
                    move_result=None,visit_proof=[],complete=False,classification=None)
                if event['op']=='end_turn':
                    ended.add((player,turn))
            elif kind in ('server_action_applied','package_applied','move_result','server_move_received','hero_visit','battle_or_capture_outcome'):
                identity=event['native_request_id']
                require(identity in pending,'Unmatched native event')
                row=pending[identity];sent=row['sent']
                require(all(type(event[key]) is type(sent[key]) and event[key]==sent[key] for key in BINDING),'Immutable native binding mismatch')
                require(event.get('source')==('client' if kind=='package_applied' else 'server'),'Wrong evidence source')
                if kind=='server_action_applied':
                    require(event.get('success') is True and not row['server_applied'],'Failed/duplicate real server apply')
                    row['server_applied']=True
                elif kind=='package_applied':
                    require(event.get('success') is True and event.get('package')=='PackageApplied' and not row['ack'],'Failed/wrong/duplicate PackageApplied ACK')
                    if sent['op']=='end_turn':
                        require(row['server_applied'],'EndTurn ACK lacks successful service apply')
                        if current.get(sent['player'])!=sent['own_turn']:
                            counts['late_end_turn_acks']+=1
                    row['ack']=True
                elif kind=='move_result':
                    require(sent['op']=='move' and integer(event.get('result'),1) and row['move_result'] is None,'Failed/duplicate move result')
                    row['move_result']=event['result']
                    if event['result']==3:
                        counts['blocking_visits']+=1
                else:
                    require(sent['op']=='move','Visit proof cannot certify EndTurn')
                    require(terminal is None,'Military visit proof must precede native game_over')
                    expected=('server_move_received','hero_visit','battle_or_capture_outcome')
                    require(len(row['visit_proof'])<3 and kind==expected[len(row['visit_proof'])],'Out-of-order military visit proof')
                    row['visit_proof'].append(kind)
                row['complete']=(row['server_applied'] and row['ack']) if sent['op']=='end_turn' else (row['move_result'] is not None and row['ack'])
                if row['complete']:
                    row['classification']='complete_end_turn' if sent['op']=='end_turn' else 'complete_move'
            elif kind=='game_over':
                require(event.get('completed') is True and terminal is None,'Missing/duplicate native completion')
                terminal=number
        except (ValueError,KeyError,TypeError) as error:
            errors.append(dict(line=number,event=event.get('event'),error=str(error)))
    last_request=next(reversed(pending),None)
    for identity,row in pending.items():
        if not row['complete'] and row['sent']['op']=='move' and terminal is not None and identity==last_request:
            candidate=row['sent']['candidate']
            if row['move_result'] is not None and not row['ack']:
                row.update(complete=True,classification='terminal_move_result_ack_missing')
            elif (not row['ack'] and candidate.get('kind') in (0,1) and candidate.get('next')==candidate.get('position')
                  and len(row['visit_proof'])==3):
                row.update(complete=True,classification='terminal_native_military_visit_confirmed')
        if not row['complete']:
            errors.append(dict(native_request_id=identity,error='Unconfirmed execution; terminal/winner is not a substitute'))
    if set(decisions)!=consumed:
        errors.append(dict(error='Unconsumed policy proposals',decision_ids=sorted(set(decisions)-consumed)))
    if terminal is None:
        errors.append(dict(error='No native game_over completion'))
    valid=not errors
    return dict(valid=valid,fixture_only=fixture,real_execution_certified=False,
        certification_limit='Event-contract check only; raw native instrumentation/extraction needs independent real-run audit',
        errors=errors,counts=counts,actions=list(pending.values()),win=None,reward=None,
        ppo_samples_admitted=0,potential_verified_policy_decisions=counts['new_policy_decisions'] if valid else 0,
        automatic_policy_samples=0,diagnostic_policy_samples=0)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--proposals',type=Path,required=True)
    parser.add_argument('--events',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--fixture-only',action='store_true')
    args=parser.parse_args()
    if args.out.exists():
        raise ValueError('Refuse overwrite')
    sources={}
    def read(path):
        raw=path.read_bytes();sources[str(path)]=digest(raw);return raw
    try:
        proposals=[json.loads(line) for line in read(args.proposals).splitlines()]
        events=[json.loads(line) for line in read(args.events).splitlines()]
        for proposal in proposals:
            request=proposal['request']
            path=args.proposals.parent/f"request-{request['request_id']:08d}.json"
            raw=read(path)
            if json.loads(raw)!=request:
                raise ValueError('Persisted request bytes do not describe proposal')
            validate_response(proposal['response'],request,raw)
            response_path=args.proposals.parent/f"action-{request['request_id']:08d}.json"
            if json.loads(read(response_path))!=proposal['response']:
                raise ValueError('Persisted typed response mismatch')
        report=audit(proposals,events,fixture=args.fixture_only)
        if any(digest(Path(path).read_bytes())!=sha for path,sha in sources.items()):
            raise ValueError('Input changed during audit')
    except (ValueError,KeyError,TypeError,OSError) as error:
        report=dict(valid=False,fixture_only=args.fixture_only,real_execution_certified=False,
                    errors=[dict(phase='persisted_input',error=str(error))],ppo_samples_admitted=0,
                    potential_verified_policy_decisions=0,win=None,reward=None)
    report['input_sha256']=sources
    atomic(args.out,(json.dumps(report,indent=2)+'\n').encode())
    print(json.dumps(dict(valid=report['valid'],fixture_only=report['fixture_only'],errors=report['errors'])))
    return 0 if report['valid'] else 1


if __name__=='__main__':
    raise SystemExit(main())
