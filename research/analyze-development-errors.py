"""Compare validation candidates by army, side and matched seed; never read holdout."""
import json
from collections import defaultdict
from pathlib import Path
from lab_io import atomic_json


def main():
    root = Path(__file__).resolve().parent
    rows = json.loads((root / 'goal-v5-validation.json').read_text())
    scenarios = {case['id']: case for case in json.loads((root / 'diverse-curriculum.json').read_text())}
    results = []
    for opponent, key in [('BattleAI', 'development_validation_report'),
                          ('MMAI_MODEL', 'development_upstream_validation_report')]:
        baseline = None
        for row in rows:
            report = json.loads(Path(row[key]).read_text())
            records = report['battles']
            assert all(record['scenario'] in scenarios and
                       scenarios[record['scenario']]['split'] == 'development' for record in records)
            indexed = {(record['scenario'], record['role'], record['seed']): record for record in records}
            assert len(indexed) == len(records), 'Duplicate condition'
            if row['name'] == 'v5-public-original':
                baseline = indexed
            assert baseline is not None and set(indexed) == set(baseline)
            groups = defaultdict(list)
            for condition, record in indexed.items():
                case = scenarios[record['scenario']]
                composition = ','.join(sorted(stack['type'] for stack in case['armies'][0] if stack))
                for name in ['all', 'role:' + record['role'], 'composition:' + composition,
                             'composition-role:' + composition + ':' + record['role'],
                             'case:' + record['scenario']]:
                    groups[name].append((record, baseline[condition]))
            summaries = {}
            for name, pairs in groups.items():
                summaries[name] = dict(battles=len(pairs), wins=sum(a['success'] for a, b in pairs),
                    original_wins=sum(b['success'] for a, b in pairs),
                    gained=sum(a['success'] and not b['success'] for a, b in pairs),
                    regressed=sum(b['success'] and not a['success'] for a, b in pairs),
                    both_lost=sum(not a['success'] and not b['success'] for a, b in pairs),
                    truncated=sum(a['truncated'] for a, b in pairs),
                    invalid_actions=sum(a['invalid_actions'] for a, b in pairs))
                summaries[name]['win_rate'] = summaries[name]['wins'] / len(pairs)
            results.append(dict(name=row['name'], opponent=opponent, groups=summaries))
    output = dict(scope='Existing development validation only; no final holdout files read',
                  results=results,
                  interpretation='Counts are matched conditions, not independent-case confidence bounds. Group diagnostics can guide later training, but cannot be reported as final independent success.')
    atomic_json(root / 'development-error-analysis.json', output)
    for row in results:
        if row['name'] == 'v5-diverse-heads-128':
            print(row['name'], row['opponent'], row['groups']['all'])
            for name, value in sorted(row['groups'].items()):
                if name.startswith('composition:'):
                    print(name, value)


if __name__ == '__main__':
    main()
