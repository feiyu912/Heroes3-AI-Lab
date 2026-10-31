"""Paired fixed-seed outcome and exact bait->counter->main event ordering."""
import gzip
import json
import argparse
from pathlib import Path


def mechanism(data, round_mode='strict-action'):
    initial=data['batches'][0]['observation_flags']
    max_own=max(f['value_relative'] for f in initial.values() if not f['is_enemy'])
    consumed={}
    examples=[]
    overrides=wait_overrides=0
    for step in data['transitions']:
        quality=step['quality']
        overrides+=bool(quality.get('overrode_teacher'))
        wait_overrides+=bool(quality.get('overrode_teacher') and quality.get('reason')=='wait_main_for_low_value_counter_consumption')
        b=data['batches'][step['post_batch_id']]
        pre=data['batches'][step['pre_batch_id']]
        if round_mode=='same-batch' and b['round_before']!=b['round_after']:
            continue
        # The requested action starts at the PRE decision round. Its strict
        # START/FINISH window stays in that round even if later opponent
        # actions in the same returned batch advance the round. Whole-batch
        # round assignment is unknown; the owned action's round is known.
        flags=pre['observation_flags'].get(str(step['selected_facts']['actor_node']))
        if flags is None:
            continue
        band='bait' if flags['value_relative']<=.15*max_own else 'main'
        win=step['action_window']
        if win['status']!='matched':
            continue
        for index in win['attack_indices']:
            e=b['events'][index]
            if e.get('attack_flags',0)&(1|2|64):
                continue
            for target in e['targets']:
                if target.get('flags',0)&(2|16) or target.get('defender_side')==step['actor_side']:
                    continue
                uid=target['defender_id']
                counter=any(b['events'][j].get('attacker_id')==uid
                            and any(t.get('defender_id')==e['attacker_id'] for t in b['events'][j]['targets'])
                            for j in win['counter_indices'])
                key=(b['round_before'],uid)
                if band=='bait' and counter:
                    consumed[key]=dict(step=step['step_id'],batch_id=b['batch_id'],event_index=index,bait_id=e['attacker_id'])
                elif band=='main' and not counter and not target['flags']&1 and key in consumed:
                    examples.append(dict(round=key[0],subject_id=uid,bait=consumed[key],
                                         main_step=step['step_id'],main_id=e['attacker_id'],
                                         batch_id=b['batch_id'],event_index=index))
    return dict(overrides=overrides,wait_overrides=wait_overrides,mechanism_examples=examples)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--version',default='curriculum-v1')
    parser.add_argument('--round-mode',choices=('strict-action','same-batch'),default='strict-action')
    args=parser.parse_args()
    here=Path(__file__).resolve().parent/args.version
    pairs={}
    runs=[]
    for path in sorted((here/'runs').rglob('*.json')):
        if path.parent.name=='source-snapshots':
            continue
        record=json.loads(path.read_text())
        if not isinstance(record,dict) or not record.get('completed'):
            continue
        with gzip.open(record['archive'],'rt') as f:
            data=json.load(f)
        outcome=record['terminal_outcome']
        side=str(int(record['role']=='defender'))
        losses=outcome['casualties'][side]
        row=dict(file=str(path),scenario=record['scenario'],split=record['original_split'],
                 role=record['role'],seed=record['seed'],policy=record['policy'],
                 success=record['success'],main_loss=losses.get('6',0),total_loss=sum(losses.values()),
                 normal=record['terminated'] and not record['truncated'] and outcome['result_type']==0,
                 **mechanism(data,args.round_mode))
        runs.append(row)
        pairs.setdefault((row['scenario'],row['role'],row['seed']),{})[row['policy']]=row
    paired=[]
    for key,p in sorted(pairs.items()):
        if 'teacher' not in p or 'wait-bait' not in p:
            continue
        base,variant=p['teacher'],p['wait-bait']
        paired.append(dict(scenario=key[0],role=key[1],seed=key[2],
                           delta_main_loss=variant['main_loss']-base['main_loss'],
                           delta_total_loss=variant['total_loss']-base['total_loss'],
                           delta_wins=int(variant['success'])-int(base['success']),
                           variant_overrides=variant['overrides'],wait_overrides=variant['wait_overrides'],
                           variant_mechanism=len(variant['mechanism_examples']),
                           teacher_mechanism=len(base['mechanism_examples'])))
    result=dict(analysis_version='v2-owned-action-round' if args.round_mode=='strict-action' else 'v1-conservative-whole-batch',
                episodes=len(runs),pairs=len(paired),normal=sum(r['normal'] for r in runs),
                mean_delta_main_loss=sum(r['delta_main_loss'] for r in paired)/len(paired) if paired else None,
                mean_delta_total_loss=sum(r['delta_total_loss'] for r in paired)/len(paired) if paired else None,
                net_wins=sum(r['delta_wins'] for r in paired),
                wait_overrides=sum(r['wait_overrides'] for r in paired),
                variant_mechanism=sum(r['variant_mechanism'] for r in paired),
                teacher_mechanism=sum(r['teacher_mechanism'] for r in paired),
                certified=False,bc_eligible=False,paired=paired,runs=runs)
    filename='PAIRED_RESULTS.json' if args.round_mode=='strict-action' else 'PAIRED_RESULTS_CONSERVATIVE.json'
    (here/filename).write_text(json.dumps(result,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k not in ('runs','paired')}))


if __name__=='__main__':
    main()
