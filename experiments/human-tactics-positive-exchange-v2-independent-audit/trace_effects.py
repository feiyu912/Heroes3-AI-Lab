"""Read-only native attack chronology after registered first overrides."""
import argparse
import gzip
import json
from pathlib import Path


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run',required=True);ap.add_argument('--output',required=True)
    args=ap.parse_args();run=Path(args.run);out=Path(args.output);assert not out.exists()
    rows=[]
    for seed in (2026111801,2026111802):
        for policy in ('teacher','positive-exchange'):
            path=run/'runs/train'/f'1-defender-{seed}-{policy}.json.gz'
            with gzip.open(path,'rt') as f:raw=json.load(f)
            attacks=[];actions=[]
            for t in raw['transitions'][11:]:
                batch=raw['batches'][t['post_batch_id']]
                actions.append(dict(step=t['step_id'],action=t['executed_action'],facts=t['selected_facts']))
                for i,e in enumerate(batch['events']):
                    if e['kind']==2:
                        attacks.append(dict(step=t['step_id'],batch_id=batch['batch_id'],event_index=i,
                            counter=bool(e['attack_flags']&2),attacker_id=e['attacker_id'],
                            attacker_side=e['attacker_side'],targets=e['targets']))
            rows.append(dict(seed=seed,policy=policy,terminal=raw['episode']['terminal_outcome'],
                             attacks=attacks,owned_actions=actions))
    out.write_text(json.dumps(dict(rows=rows),indent=2))
    for r in rows:
        print(json.dumps(dict(seed=r['seed'],policy=r['policy'],first_attacks=r['attacks'][:8])))


if __name__=='__main__':main()
