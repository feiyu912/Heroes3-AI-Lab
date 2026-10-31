"""Read-only salvage index: next decision contains previous action's events.

No observations/events are invented, terminal batches stay unrecoverable.
An index is not a promoted demonstration dataset.
"""
import gzip
import json
from pathlib import Path
import numpy as np
from event_audit import action_window
from events_provenance import digest


def main():
    from vcmi_gym.envs.v15.vcmi_env import Action, ACTION_TYPES
    native={ACTION_TYPES['WAIT']:6,ACTION_TYPES['DEFEND']:7,ACTION_TYPES['MOVE']:5,
            ACTION_TYPES['AMOVE']:8,ACTION_TYPES['SHOOT']:9}
    here=Path(__file__).resolve().parent
    old=here.parent/'human-tactics-events-v2/runs'
    rows=[]
    for path in sorted(old.rglob('*.json.gz')):
        with gzip.open(path,'rt') as stream:
            data=json.load(stream)
        episode=data.get('episode',{})
        if episode.get('schema')!='human-tactics-demonstration-events-v2':
            rows.append(dict(path=str(path),schema=episode.get('schema'),skipped=True))
            continue
        decisions=data['decisions']
        matches=[]
        unknown=0
        for i, decision in enumerate(decisions[:-1]):
            following=decisions[i+1]
            aid=decision['executed_action']
            node=np.asarray(decision['observation']['nodes']['Action'][aid],np.float32)
            typ=int(Action.decode_one(node).ACTION_TYPE)
            window=action_window(following['battle_events'],decision['actor_side'],expected_native_type=native[typ])
            if window['status']=='matched':
                matches.append(dict(action_decision=i,event_decision=i+1,window=window))
            else:
                unknown+=1
        rows.append(dict(path=str(path),sha256=digest(path),schema=episode['schema'],steps=len(decisions),
                         completed=episode.get('completed'),terminated=episode.get('terminated'),
                         recoverable_matched_windows=len(matches),unmatched_nonterminal=unknown,
                         permanently_missing_terminal_action_events=bool(decisions),
                         action_event_index=matches,eligible_for_bc=False))
    included=[r for r in rows if not r.get('skipped')]
    result=dict(read_only_source=str(old),archives_seen=len(rows),old_v2_archives=len(included),
                other_schema_archives=len(rows)-len(included),
                recorded_steps=sum(r['steps'] for r in included),
                recoverable_matched_action_windows=sum(r['recoverable_matched_windows'] for r in included),
                irrecoverable_last_action_batches=sum(r['permanently_missing_terminal_action_events'] for r in included),
                bc_eligible_decisions=0,
                limitation='Index recovers action/event timing only; terminal events cannot be reconstructed and per-action benefit remains unproven',rows=rows)
    (here/'V2_RECOVERY_AUDIT.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k!='rows'}))


if __name__=='__main__':
    main()
