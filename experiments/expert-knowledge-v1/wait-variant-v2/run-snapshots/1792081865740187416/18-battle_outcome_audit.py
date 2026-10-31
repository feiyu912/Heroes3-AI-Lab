"""Audit reported wins against raw terminal flags and normal-battle casualties."""
def audit(records):
    wins=normal=0
    for record in records:
        outcome=record['terminal_outcome']
        expected=bool(record['terminated'] and not record['truncated'] and outcome
                      and outcome['result_type']==0
                      and outcome['winner']==int(record['role']=='defender'))
        assert record['success']==expected,'A reported win differs from raw termination/winner flags'
        wins+=expected
        if record['terminated'] and outcome and outcome['result_type']==0 and outcome['winner'] in [0,1]:
            normal+=1;winner=str(outcome['winner']);loser=str(1-outcome['winner'])
            initial=outcome['initial_armies'];casualties=outcome['casualties']
            # All fixtures in this benchmark have three ordinary stacks, no
            # summoning or resurrection: a normal loser must have no army left.
            for creature,count in initial[int(loser)].items():
                assert casualties[loser].get(creature,0)==count,'Normal loser has surviving units'
            remaining=sum(count-casualties[winner].get(creature,0)
                          for creature,count in initial[int(winner)].items())
            assert remaining>0,'Normal winner has no surviving units'
    return dict(battles=len(records),verified_wins=wins,normal_outcomes_checked=normal)
