"""Summarize an archived native run without executing a game or changing inputs."""
import collections
import hashlib
import json
import pathlib
import sys

run = pathlib.Path(sys.argv[1])
output = pathlib.Path(sys.argv[2])
decisions = run / 'strategy-decisions.jsonl'
rows = [json.loads(line) for line in decisions.open() if line.strip()]
selected = lambda row: row['candidates'][row['selected_candidate']]
def summarize(part):
    kinds = collections.Counter(selected(row)['kind'] for row in part)
    destinations = collections.Counter(tuple(row['destination']) for row in part)
    origins = collections.Counter(tuple(row['from']) for row in part)
    selected_pairs = collections.Counter((selected(row)['kind'], tuple(row['destination'])) for row in part)
    return {
        'decisions': len(part),
        'first_day': part[0]['day'] if part else None,
        'last_day': part[-1]['day'] if part else None,
        'selected_kind_counts': dict(kinds),
        'unique_origins': len(origins),
        'unique_destinations': len(destinations),
        'most_common_targets': [{'kind': k, 'destination': list(pos), 'count': n}
                                for (k, pos), n in selected_pairs.most_common(12)],
        'candidate_kind_counts': dict(collections.Counter(c['kind'] for row in part for c in row['candidates'])),
    }
result = {
    'source': str(decisions),
    'sha256': hashlib.sha256(decisions.read_bytes()).hexdigest(),
    'all': summarize(rows), 'last_1000': summarize(rows[-1000:]),
    'last_12_choices': [{'day': r['day'], 'from': r['from'], 'destination': r['destination'],
                         'step': r['step'], 'selected': selected(r)} for r in rows[-12:]],
    'note': 'Observational audit only; repeated targets do not alone establish root cause.'
}
trace_file = run / 'strategy-trace.jsonl'
states = [json.loads(line) for line in trace_file.open() if line.strip()]
last_decision_day = rows[-1]['day'] if rows else None
late_states = [r for r in states if last_decision_day is not None and r.get('day', 0) > last_decision_day]
result['state_trace'] = {
    'sha256': hashlib.sha256(trace_file.read_bytes()).hexdigest(),
    'last_record': states[-1] if states else None,
    'records_after_final_decision_day': len(late_states),
    'events_after_final_decision_day': dict(collections.Counter(r.get('event') for r in late_states)),
}
log = (run / 'client.log').read_text(errors='replace')
result['log_counts'] = {needle: log.count(needle) for needle in (
    'That hero is not visible!', 'DirectorAI: no target for hero',
    'DirectorAI: no hero with movement points', 'external policy failed',
)}
output.write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
