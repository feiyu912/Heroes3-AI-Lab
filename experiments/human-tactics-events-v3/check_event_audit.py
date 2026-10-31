"""Regression checks for attribution/round/identity failures from the review."""
from event_audit import action_window, update_identity, analyze_retaliations, demonstration_gate


def attack(uid, target, flags=0):
    return dict(kind=2, attacker_id=uid, attacker_side=int(uid==9), attack_flags=flags,
                targets=[dict(defender_id=target, defender_side=int(target==9), flags=0, damage=10, killed=0)])


def main():
    start = dict(kind=0, side=0, stack_number=1, action_type=6)
    finish = dict(kind=1, side=0, stack_number=1, action_type=6)
    own, counter, later = attack(1,9), attack(9,1,2), attack(9,1)
    events = [start,own,counter,finish,later]
    win = action_window(events,0,1)
    assert win['attack_indices']==[1] and win['counter_indices']==[2]
    assert action_window(events,0,2)['status']=='unknown'
    assert action_window(events[:-2],0,1)['status']=='unknown'
    assert action_window(events+[start,finish],0,1)['status']=='unknown'
    gate = demonstration_gate(dict(action_window=win),events,dict(terminated=True,truncated=False))
    assert gate['action_event_verified'] and not gate['eligible_for_bc']
    registry={}
    update_identity(registry,[dict(kind=2,attacker_id=1,attacker_node=-1,attacker_side=0,
                                   targets=[dict(defender_id=9,defender_node=0,defender_side=1)])],
                    {'0':dict(value_relative=.8)},0)
    assert registry['1']['unknown'] and not registry['9']['unknown']
    audit=analyze_retaliations([dict(round_before=1,round_after=1,events=[own,counter,attack(2,9)])])
    subject=next(r for r in audit['subjects'] if r['unit_id']==9)
    assert subject['primary_melee_received']==2 and subject['counters_emitted']==1
    assert not audit['finite_retaliation_proven']
    unknown=analyze_retaliations([dict(round_before=1,round_after=2,events=[own,counter])])
    assert unknown['unknown_round_attacks']==2 and not unknown['subjects']
    print('PASS: strict window, wrong actor, missing finish, multi-window, counters, unknown identity, round boundary, BC gate')


if __name__=='__main__':
    main()
