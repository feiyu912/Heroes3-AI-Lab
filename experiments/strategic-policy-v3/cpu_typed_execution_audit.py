"""Constructed CPU protocol tests; no games, GPU, rollouts or optimizer updates."""
import argparse
import copy
import hashlib
import json
from pathlib import Path

from broker import Broker,validate_response
from audit_typed_execution import audit,BINDING


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    root=Path(__file__).resolve().parent
    base=json.loads((root.parent/'strategic-policy-v2/fixtures/visible-request.json').read_text())
    base.update(schema='strategy-candidates-v4',own_hero_count=1,own_turn=1,player=0,hero=44)
    move=dict(op='move',kind=0,position=[12,10,0],next=[12,10,0],path_cost=100,heuristic_score=2.)
    base['candidates']=[move,{'op':'end_turn'}]
    agent=args.out/'agent';agent.mkdir()
    diagnostic=Broker('diagnostic-only',diagnostic_action='alternate')
    proposals=[]
    for identity in range(1,5):
        request=copy.deepcopy(base);request.update(request_id=identity,own_turn=1 if identity<3 else 2)
        path=agent/f'request-{identity:08d}.json';path.write_text(json.dumps(request)+'\n')
        proposals.append(diagnostic.process(path,identity))
    policy=Broker('new-policy',args.checkpoint)
    assert next(policy.model.parameters()).device.type=='cpu'
    normal=policy.propose((agent/'request-00000001.json').read_bytes(),1)
    assert normal['response']['classification']=='new_policy' and not normal['ppo_sample_admitted']
    def turn(number):
        return dict(event='your_turn',player=0,own_turn=number)
    def idle(number,**updates):
        return dict(event='busy_state',player=0,own_turn=number,query_count=0,
                    movement_busy=False,economy_busy=False,battle_busy=False,**updates)
    def sent(proposal,identity):
        response=proposal['response'];request=proposal['request']
        return dict(event='native_action_sent',**{key:response[key] for key in
            ('decision_id','player','hero','own_turn','op','selected_index','request_sha256')},
            native_request_id=identity,pack_type='EndTurn' if response['op']=='end_turn' else 'MoveHero',
            candidate=request['candidates'][response['selected_index']])
    def evidence(action,kind,**values):
        return dict(event=kind,**{key:action[key] for key in BINDING},
                    source='client' if kind=='package_applied' else 'server',**values)
    def applied(action):
        return evidence(action,'server_action_applied',success=True)
    def ack(action):
        return evidence(action,'package_applied',success=True,package='PackageApplied')
    def result(action,value=1):
        return evidence(action,'move_result',result=value)
    a,b,c,d=[sent(proposal,100+index) for index,proposal in enumerate(proposals)]
    events=[turn(1),idle(1),a,result(a),ack(a),b,applied(b),turn(2),idle(2),c,
            ack(b),result(c,3),ack(c),d,applied(d),ack(d),dict(event='game_over',completed=True)]
    positives={};negatives={}
    def positive(name,rows,trace):
        report=audit(rows,trace,fixture=True)
        assert report['valid'],(name,report['errors'])
        assert not report['real_execution_certified'] and report['ppo_samples_admitted']==0
        positives[name]=report
    def negative(name,rows,trace):
        report=audit(rows,trace,fixture=True)
        assert not report['valid'],name
        assert report['reward'] is None and report['win'] is None
        negatives[name]=report['errors']
    positive('late_endturn_ack_during_newturn_move',proposals,events)
    assert positives['late_endturn_ack_during_newturn_move']['counts']['late_end_turn_acks']==1
    assert positives['late_endturn_ack_during_newturn_move']['counts']['blocking_visits']==1
    automatic=dict(event='native_action_sent',decision_id=None,native_request_id=200,player=0,hero=44,
                   own_turn=1,op='end_turn',pack_type='EndTurn',selected_index=None,request_sha256=None,
                   candidate={'op':'end_turn'},automatic_reason='no legal move after economic completion')
    positive('automatic_is_not_policy',[],[turn(1),idle(1),automatic,applied(automatic),ack(automatic),events[-1]])
    assert positives['automatic_is_not_policy']['counts']['automatic_end_turns']==1
    assert positives['automatic_is_not_policy']['potential_verified_policy_decisions']==0
    terminal_prefix=[turn(1),idle(1),a]
    positive('terminal_move_result_missing_ack',[proposals[0]],terminal_prefix+[result(a),events[-1]])
    visit=[evidence(a,kind) for kind in ('server_move_received','hero_visit','battle_or_capture_outcome')]
    positive('terminal_military_native_visit',[proposals[0]],terminal_prefix+visit+[events[-1]])
    negative('endturn_missing_server_apply',proposals,[event for event in events if not(event['event']=='server_action_applied' and event['native_request_id']==101)])
    negative('endturn_missing_ack_nextturn_not_substitute',proposals,[event for event in events if not(event['event']=='package_applied' and event['native_request_id']==101)])
    for name,field,value in [('late_ack_rewritten_turn','own_turn',2),('wrong_ack_request','native_request_id',999),
                              ('wrong_ack_op','op','move'),('wrong_ack_pack','pack_type','MoveHero'),('failed_ack','success',False)]:
        altered=copy.deepcopy(events);altered[10][field]=value;negative(name,proposals,altered)
    for key,value in [('query_count',1),('movement_busy',True),('economy_busy',True),('battle_busy',True)]:
        altered=copy.deepcopy(events);altered.insert(5,dict(idle(1),**{key:value}));negative('endturn_busy_'+key,proposals,altered)
    altered=copy.deepcopy(events);altered.insert(7,copy.deepcopy(c));negative('action_after_endturn_before_newturn',proposals,altered)
    altered=copy.deepcopy(events);altered[7]['own_turn']=3;negative('turn_sequence_gap',proposals,altered)
    altered=copy.deepcopy(events);altered.insert(11,copy.deepcopy(altered[10]));negative('duplicate_ack',proposals,altered)
    negative('late_old_ack_cannot_complete_new_move',proposals,[event for event in events if not(event['event']=='package_applied' and event['native_request_id']==102)])
    altered=copy.deepcopy(events);altered[5]['selected_index']=0;negative('selected_index_mismatch',proposals,altered)
    altered=copy.deepcopy(events);altered[5]['request_sha256']='0'*64;negative('request_sha_mismatch',proposals,altered)
    negative('terminal_winner_only',[proposals[0]],terminal_prefix+[dict(event='game_over',completed=True,winner='red')])
    negative('endturn_terminal_not_substitute',[proposals[1]],[turn(1),idle(1),b,events[-1]])
    negative('unconsumed_proposal',proposals,events[:5]+[events[-1]])
    negative('visit_after_terminal',[proposals[0]],terminal_prefix+[events[-1]]+visit)
    negative('visit_wrong_order',[proposals[0]],terminal_prefix+[visit[1],visit[0],visit[2],events[-1]])
    bad_auto=dict(automatic,automatic_reason=1)
    negative('automatic_reason_requires_string',[],[turn(1),idle(1),bad_auto,applied(bad_auto),ack(bad_auto),events[-1]])
    for kind in ('move_failed','economy_failed','query_failed','server_rejected'):
        negative(kind,proposals,events+[dict(event=kind)])
    response_rejections={}
    raw=(agent/'request-00000001.json').read_bytes()
    request=proposals[0]['request'];response=proposals[0]['response']
    for name,changed in [('plainint',0),('wrong_response_turn',dict(response,own_turn=2)),
                         ('bool_index',dict(response,selected_index=True)),('fake_native_id',dict(response,native_request_id=3)),
                         ('unknown_response_schema',dict(response,schema='strategy-candidates-v3'))]:
        try:
            validate_response(changed,request,raw)
        except (ValueError,TypeError,KeyError):
            response_rejections[name]=True
        else:
            raise AssertionError(name)
    move_only=dict(request,candidates=[move])
    try:
        Broker('diagnostic-only',diagnostic_action='end_turn').propose(json.dumps(move_only).encode(),1)
    except ValueError:
        response_rejections['diagnostic_missing_stop_no_fallback']=True
    else:
        raise AssertionError('Diagnostic substituted an unavailable stop')
    (args.out/'events-late-ack.jsonl').write_text(''.join(json.dumps(event)+'\n' for event in events))
    (args.out/'FIXTURES.json').write_text(json.dumps(dict(positive=positives,negative=negatives),indent=2)+'\n')
    report=dict(passed=True,cpu_only=True,constructed_events=True,native_started=False,gpu_started=False,
        optimizer_steps=0,ppo_samples_admitted=0,positive_cases=list(positives),negative_cases=list(negatives),
        response_rejections=response_rejections,normal_policy_cpu_inference=True,typed_checkpoint_sha256=policy.model_sha256,
        raw_native_execution_proven=False,source_sha256={name:hashlib.sha256((root/name).read_bytes()).hexdigest()
            for name in ('broker.py','audit_typed_execution.py','cpu_typed_execution_audit.py','TYPED_EXECUTION_CONTRACT.md')})
    (args.out/'AUDIT.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))


if __name__=='__main__':
    main()
