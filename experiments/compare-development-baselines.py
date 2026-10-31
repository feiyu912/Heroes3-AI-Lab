"""Matched development diagnostics; never an independent confirmation test."""
import hashlib
import json
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parent


def main():
    results = []
    for opponent in ['BattleAI','MMAI_MODEL']:
        a_path = ROOT/'conservative-ppo-v1'/f'public-original-{opponent}-development.json'
        b_path = ROOT/'expert-retention-v1'/f'b64-baseline-{opponent}-development.json'
        a,b = [json.loads(path.read_text()) for path in [a_path,b_path]]
        assert a['opponent']==b['opponent']==opponent
        assert a['scenario_ids']==b['scenario_ids']==list(range(192,240))
        assert a['scenario_file']==b['scenario_file']
        shared = set(a['frozen_artifacts']) & set(b['frozen_artifacts'])
        for path in shared:
            assert a['frozen_artifacts'][path]==b['frozen_artifacts'][path], path
        def key(row): return row['scenario'],row['role'],row['seed']
        index = {key(row):row for row in a['battles']}
        pairs = []
        for row in b['battles']:
            original = index[key(row)]
            assert original['terminated'] and row['terminated']
            assert not original['truncated'] and not row['truncated']
            pairs.append((original,row))
        assert len(pairs)==96 and len({key(y) for x,y in pairs})==96
        groups = {}
        for original,row in pairs:
            groups.setdefault(row['scenario'],[]).append(int(row['success'])-int(original['success']))
        effects = [sum(values)/len(values) for values in groups.values()]
        assert len(effects)==48
        rng = random.Random(2026101609)
        boot = sorted(sum(rng.choices(effects,k=48))/48 for _ in range(20000))
        results.append(dict(opponent=opponent, matched_battles=96,
            public_wins=sum(x['success'] for x,y in pairs),b64_wins=sum(y['success'] for x,y in pairs),
            improved=sum(not x['success'] and y['success'] for x,y in pairs),
            regressed=sum(x['success'] and not y['success'] for x,y in pairs),
            scenario_cluster95_win_rate_difference=[boot[500],boot[19499]],
            source_hashes={str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in [a_path,b_path]},
            shared_artifact_hashes_equal=len(shared)))
    report = dict(scope='Matched development seed subset only; model selection diagnostics, not fresh confirmation.',
        results=results,goal_achieved=False)
    (ROOT/'matched-development-baselines.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
