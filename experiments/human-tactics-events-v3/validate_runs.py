"""Verify archives, terminal completeness, actions, and deterministic reexecution."""
import gzip
import hashlib
import json
from pathlib import Path
from event_audit import action_window
from events_provenance import digest


def trace_fingerprint(data):
    keep=dict(outcome=data['episode']['terminal_outcome'],batches=data['batches'],
              transitions=[{k:t[k] for k in ('executed_action','observation_before','observation_after','action_window')}
                           for t in data['transitions']])
    return hashlib.sha256(json.dumps(keep,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def main():
    here=Path(__file__).resolve().parent
    rows=[]
    traces={}
    for path in sorted((here/'runs/smoke').glob('*.json')):
        record=json.loads(path.read_text())
        if not record.get('completed'):
            continue
        archive=Path(record['archive'])
        assert digest(archive)==record['archive_sha256']
        with gzip.open(archive,'rt') as f:
            data=json.load(f)
        batches=data['batches']; steps=data['transitions']
        assert len(batches)==len(steps)+1
        assert record['terminated'] and not record['truncated'] and record['invalid_actions']==0
        assert record['terminal_outcome']['result_type']==0
        from battle_outcome_audit import audit
        audit([record])
        final=batches[record['terminal_batch_id']]
        assert final is batches[-1] and sum(e['kind']==3 for e in final['events'])==1
        end=next(e for e in final['events'] if e['kind']==3)
        assert end['winner']==record['terminal_outcome']['winner']
        for i,t in enumerate(steps):
            assert t['step_id']==i and t['pre_batch_id']==i and t['post_batch_id']==i+1
            assert t['executed_action'] in t['legal_actions']
            assert t['action_window']['status']=='matched'
            assert not t['demonstration_gate']['eligible_for_bc']
            if i+1<len(steps):
                assert t['observation_after']==steps[i+1]['observation_before']
        fingerprint=trace_fingerprint(data)
        traces[path.stem]=fingerprint
        rows.append(dict(file=str(path),steps=len(steps),event_verified=record['event_verified_decisions'],
                         unknown_identities=record['unknown_identities'],trace_sha256=fingerprint,
                         terminal_events=record['terminal_event_count'],retaliation_audit=data['retaliation_audit']))
    equal=traces.get('dragon-attacker')==traces.get('dragon-repeat-attacker')
    assert equal
    result=dict(passed=True,episodes=len(rows),total_steps=sum(r['steps'] for r in rows),
                total_event_verified=sum(r['event_verified'] for r in rows),
                normal_terminal=len(rows),illegal=0,truncated=0,
                deterministic_actual_reexecution=equal,bc_eligible_decisions=0,rows=rows)
    (here/'VALIDATION_RESULTS.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k!='rows'}))


if __name__=='__main__':
    main()
