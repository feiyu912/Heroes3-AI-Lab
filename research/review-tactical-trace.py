"""Extract grounded action facts; do not infer mastery from action counts."""
import gzip
import json
from pathlib import Path
from collections import Counter
from lab_io import atomic_json


def main():
    research = Path(__file__).resolve().parent
    path = research / 'tactical-traces/b64-retaliation-attacker-v2.jsonl.gz'
    with gzip.open(path, 'rt') as stream:
        rows = [json.loads(line) for line in stream]
    first_path = path.with_name('b64-retaliation-attacker.jsonl.gz')
    with gzip.open(first_path, 'rt') as stream:
        first = [json.loads(line) for line in stream]
    assert first == rows, 'Repeated diagnostic trajectory differs'
    decisions = []
    for row in rows[:-1]:
        action = row['action_id']
        assert action in row['legal_action_ids']
        actor_edges = [edge for edge in row['selected_edges']
                       if edge['relation'] == ['Action', 'By', 'Unit']]
        assert len(actor_edges) == 1
        actor = actor_edges[0]['endpoints'][1]
        assert row['units'][actor]['IS_ACTIVE'] == 1
        assert row['units'][actor]['IS_ENEMY'] == 0
        targets = []
        for edge in row['selected_edges']:
            if edge['relation'][1] in ['IsMeleedBy', 'IsShotBy']:
                index = edge['endpoints'][0]
                # An all-around/breath attack may hit allies; keep every real
                # target instead of silently assuming all are enemies.
                targets.append(dict(unit_row=index, unit=row['units'][index],
                                    relationship=edge['relation'][1],
                                    attributes=edge['attributes']))
        decisions.append(dict(step=row['step'], round=row['global_state']['BATTLE_ROUND'],
            action_type=row['action_type'], actor_row=actor, actor=row['units'][actor],
            targets=targets))
    report = dict(trace=str(path), repeated_full_records_equal=True,
        decisions=decisions, action_counts=dict(Counter(row['action_type'] for row in decisions)),
        final=rows[-1],
        limitations=['Unit row IDs are local to each observation.',
                    'Observations skip intervening opponent actions.',
                    'Counts and selected targets alone do not prove baiting, guarding or focus-fire skill.',
                    'Current observation does not expose persistent creature IDs or explicit retaliation counts.'])
    atomic_json(research / 'tactical-trace-review.json', report)
    print(json.dumps(dict(decisions=len(decisions), repeated_full_records_equal=True,
        action_counts=report['action_counts'], final=report['final'])), flush=True)


if __name__ == '__main__':
    main()
