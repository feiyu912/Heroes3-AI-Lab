"""Independent regression checks for slot aggregation, not native gameplay."""
from collections import Counter
import json
from pathlib import Path
from recompute import army,transfers

before={'event':'before_army_transfer','day':51,'heroes':[{'id':21,'army':[[2,6],[2,4],[2,6],[10,8]]}],
        'towns':[{'id':18,'army':[[2,36],[0,56]]}]}
after={'event':'economy_applied','day':51,'heroes':[{'id':21,'army':[[2,42],[2,4],[2,6],[10,8]]}],
       'towns':[{'id':18,'army':[[0,56]]}]}
start={'event':'turn_start','day':1,'heroes':[{'id':2,'army':[[2,1]]}],'towns':[]}
assert army(before['heroes'][0])[2]==16 and army(after['heroes'][0])[2]==52
assert army(before['heroes'][0],True)[2]==army(after['heroes'][0],True)[2]==6
assert army({'army':[[2,4],[0,3],[2,5],[0,7]]})==Counter({2:9,0:10})
old=transfers([start,before,after],True);new=transfers([start,before,after])
assert len(old['errors'])==1 and not new['errors'] and new['delivered_count']==36 and new['delivered_to_main_count']==0
assert army({'army':list(reversed(before['heroes'][0]['army']))})==army(before['heroes'][0])
report={'passed':True,'tests':['reproduce_16_to_52_actual_slot_pattern','reproduce_old_6_to_6_false_ambiguity',
    'sum_mixed_duplicate_creatures','slot_order_invariance','36_conserved_replacement_delivery_not_original_main'],
    'native_games_started':0,'optimizer_steps':0}
(Path(__file__).parent/'CPU_CHECK.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
