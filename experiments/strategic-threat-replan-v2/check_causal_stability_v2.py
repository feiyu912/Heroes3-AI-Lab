"""CPU synthetic checks only: EOF-sensitive projections and stability counters."""
import argparse
import json
from pathlib import Path
import causal_stability_audit_v2 as audit


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out',type=Path,required=True)
    args = parser.parse_args()
    checks = []
    def check(name,condition):
        if not condition:
            raise AssertionError(name)
        checks.append(name)
    check('empty_equal',audit.first_difference([],[]) is None)
    check('equal_nonempty',audit.first_difference([1,2],[1,2]) is None)
    d = audit.first_difference([1],[1,2])
    check('off_eof_tail_not_lost',d['index']==2 and d['off_eof'] and not d['once_eof'])
    d = audit.first_difference([1,2],[1])
    check('once_eof_tail_not_lost',d['index']==2 and d['once_eof'] and not d['off_eof'])
    d = audit.first_difference([],[None])
    check('missing_tail_not_equal_to_json_null',d is not None and d['off_eof'])
    d = audit.first_difference([1,3],[1,4])
    check('first_semantic_difference',d['index']==2 and d['off']==3 and d['once']==4)
    log = '\n'.join([
        'Server: Hero before starts movement from (0 0 0) to (1 0 0).',
        'DirectorThreatReplan {"event":"bounded_threat_replan","decision_id":2}',
        'Server: Hero after starts movement from (3 0 0) to (2 0 0).'])
    parsed = audit.parse_log(log)
    prefix = [m for m in parsed['movements'] if m['line']<parsed['releases'][0]['line']]
    check('prefix_uses_true_release_line',len(prefix)==1 and prefix[0]['hero_log_name']=='before')
    d = audit.movement_comparison(prefix,parsed['movements'])
    check('movement_length_tail_not_lost',not d['recorded_order_exact'] and d['first_difference']['off_eof'])
    def p(identity,start,end,target,turn=1):
        candidate=dict(op='move',kind=5,position=target,next=end)
        return dict(request=dict(request_id=identity,day=turn,own_turn=turn,player=0,hero=1,
                                 **{'from':start},candidates=[candidate]),
                    response=dict(op='move',selected_index=0))
    proposals=[p(1,[0,0,0],[1,0,0],[3,0,0]),p(2,[1,0,0],[0,0,0],[-3,0,0])]
    counts=audit.stability(proposals,[],dict(budget_lines=[]),128)
    check('within_turn_goal_switch',counts['within_turn_goal_changes']==1)
    check('selected_step_reversal',counts['selected_immediate_step_reversals']==1)
    proposals[1]['request']['own_turn']=2
    counts=audit.stability(proposals,[],dict(budget_lines=[]),128)
    check('turn_boundary_does_not_count_as_immediate_reversal',counts['within_turn_goal_changes']==0 and counts['selected_immediate_step_reversals']==0)
    typed=[dict(event='native_action_sent',decision_id=None,automatic_reason='native_move_budget')]
    counts=audit.stability([],typed,dict(budget_lines=[dict(line=1,text='CPU fake cap')]),128)
    check('native_cap_events_counted',counts['native_cap_end_turn_count']==1 and counts['cap_log_and_end_turn_counts_agree'])
    args.out.mkdir(parents=True,exist_ok=False)
    result=dict(passed=True,fixture=True,real_execution_certified=False,new_native_games=0,
                optimizer_steps=0,training_samples=0,checks=checks,
                source_sha256={str(Path(__file__)):audit.sha(Path(__file__)),str(Path(audit.__file__)):audit.sha(Path(audit.__file__))})
    (args.out/'AUDIT.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
