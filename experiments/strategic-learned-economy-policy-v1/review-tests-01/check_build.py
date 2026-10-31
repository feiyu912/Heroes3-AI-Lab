"""Synthetic independent negative review of root build auditor. No native evidence."""
import copy,hashlib,importlib.util,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;POLICY=HERE.parent;RUN=POLICY.parent/'strategic-learned-economy-run-v1'
sys.path.insert(0,str(POLICY))
from check_cpu import fixture
spec=importlib.util.spec_from_file_location('_review_root_build_evidence',RUN/'build_evidence.py')
audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)

def data():
    q=fixture();c=q['candidates'][2];response=dict(schema='strategy-typed-action-response-v2',selected_index=2,decision_id=1,player=0,hero=0,own_turn=1,op='build',request_sha256='0'*64,classification='diagnostic_only')
    proposals=[dict(request=q,response=response)]
    before=dict(town_id=3,owner=0,built_today=0,buildings=[0],resources=copy.deepcopy(q['resources']))
    after=copy.deepcopy(before);after.update(built_today=1,buildings=[0,11]);after['resources']['gold']-=2500
    binding=dict(decision_id=1,native_request_id=17,player=0,hero=0,own_turn=1,op='build',pack_type='BuildStructure',selected_index=2,request_sha256='0'*64,candidate=c,classification='diagnostic_only',actor='player_town',town_id=3,building_id=11)
    event=lambda name,**kwargs:('DirectorTypedEvent',dict(binding,event=name,**kwargs))
    packs=[dict(event='set_resources_received',player=0,mode=0,resources={r:(-2500 if r=='gold' else 0) for r in audit.RES}),dict(event='new_structures_received',town_id=3,built_today=1,buildings=[11])]
    records=[event('native_action_sent',actual_request=dict(pack_type='BuildStructure',player=0,native_request_id=17,town_id=3,building_id=11),before_state=before),
        ('DirectorBuildPack',packs[0]),('DirectorBuildPack',packs[1]),
        event('build_changed',what=1,observed_building_id=11,state=after),
        ('server','TypedBuildApplied player=0 native_request_id=17 town_id=3 building_id=11 success=1'),
        event('build_ack_state',state=after),event('package_applied',success=True,package='PackageApplied')]
    return proposals,records,packs

def run(p,records,packs):
    raw='\n'.join(v if k=='server' else k+' '+json.dumps(v) for k,v in records)
    return audit.verify(raw,p,packs)

def main():
    p,records,packs=data();assert run(p,records,packs)['policy_builds']==1
    results=[]
    def reject(name,mutation):
        pp,rr,kk=copy.deepcopy((p,records,packs));mutation(pp,rr,kk)
        try:run(pp,rr,kk)
        except (ValueError,KeyError,TypeError,IndexError) as e:results.append(dict(case=name,rejected=True,error=str(e)))
        else:results.append(dict(case=name,rejected=False))
    reject('wrong_cost',lambda p,r,k:p[0]['request']['candidates'][2]['cost'].update(gold=2400))
    reject('wrong_actual_nativeid',lambda p,r,k:r[0][1]['actual_request'].update(native_request_id=18))
    reject('wrong_server_nativeid',lambda p,r,k:r.__setitem__(4,('server',r[4][1].replace('id=17','id=18'))))
    reject('missing_ack',lambda p,r,k:r.pop())
    reject('missing_structures',lambda p,r,k:(r.pop(2),k.pop(1)))
    reject('missing_resources',lambda p,r,k:(r.pop(1),k.pop(0)))
    reject('missing_build_callback',lambda p,r,k:r.pop(3))
    reject('missing_server_apply',lambda p,r,k:r.pop(4))
    reject('wrong_ack_resource_state',lambda p,r,k:r[5][1]['state']['resources'].update(gold=7600))
    reject('wrong_town',lambda p,r,k:r[0][1].update(town_id=4))
    reject('wrong_building',lambda p,r,k:r[0][1].update(building_id=12))
    reject('wrong_ack_binding',lambda p,r,k:r[-1][1].update(native_request_id=18))
    reject('wrong_daily_counter',lambda p,r,k:r[5][1]['state'].update(built_today=2))
    reject('mirror_mismatch',lambda p,r,k:k.pop())
    reject('second_window_reopened',lambda p,r,k:p.append(copy.deepcopy(p[0])))
    reject('late_subject_server_apply_after_ACK',lambda p,r,k:r.append(r.pop(4)))
    reject('early_ack_state_before_subject_server_apply',lambda p,r,k:r.insert(4,r.pop(5)))
    # Close window rather than manufacturing a second build proposal.
    reject('window_reopened_after_move',lambda p,r,k:p.insert(0,dict(request=copy.deepcopy(p[0]['request']),response=dict(p[0]['response'],op='move',selected_index=0,decision_id=2))))
    report=dict(synthetic_only=True,positive_fixture_passed=True,native_games=0,optimizer_steps=0,
        rejection_cases=results,unrejected=[x['case'] for x in results if not x['rejected']],
        reviewed_source_sha256={n:hashlib.sha256((RUN/n).read_bytes()).hexdigest() for n in ['build_evidence.py','collect_episode_v5.py','pipeline_common.py','audit_contract.py','raw_events_v5.py','audit_game_v6.py']})
    (HERE/'AUDIT.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
