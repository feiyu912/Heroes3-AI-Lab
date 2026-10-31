import gzip,json
from pathlib import Path
root=Path(__file__).resolve().parent/'curriculum-v2/runs/train'
for path in root.glob('*wait-bait.json.gz'):
    with gzip.open(path,'rt') as f:data=json.load(f)
    for i,t in enumerate(data['transitions']):
        if t['quality'].get('reason')!='wait_main_for_low_value_counter_consumption':continue
        print(path.name,'WAIT',i)
        for s in data['transitions'][i:i+5]:
            b=data['batches'][s['post_batch_id']]
            pre=data['batches'][s['pre_batch_id']]
            v=pre['observation_flags'][str(s['selected_facts']['actor_node'])]['value_relative']
            print('STEP',s['step_id'],'round',b['round_before'],b['round_after'],'actor',s['action_window']['actor_id'],'value',v,'reason',s['quality'].get('reason'),
                  'events',[dict(actor=e['attacker_id'],flags=e['attack_flags'],targets=[(x['defender_id'],x['flags'],x['damage']) for x in e['targets']])
                  for e in b['events'] if e['kind']==2])
