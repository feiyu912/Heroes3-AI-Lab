"""Read-only arithmetic/family audit of the completed external v2 experiment."""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
RUN=HERE/'expert-mixed-b64-run-v2'
SCENARIOS=HERE.parent/'research/diverse-curriculum.json'


def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    cases={case['id']:case for case in read(SCENARIOS)}
    paths={name:RUN/(name+'-BattleAI-development.json') for name in ['b64-baseline','public-original']}
    reports={name:read(path) for name,path in paths.items()}
    baseline=reports['b64-baseline']['battles']
    def key(row):return row['scenario'],row['role'],row['seed']
    public={key(row):row for row in reports['public-original']['battles']}
    assert len(baseline)==len(public)==192
    roles={}
    families={}
    groups={}
    for row in baseline:
        assert row['terminated'] and not row['truncated'] and row['invalid_actions']==0
        case=cases[row['scenario']]
        types={stack['type'].split(':')[-1] for stack in case['armies'][0] if stack}
        family='+'.join(sorted(types))
        ranged=bool(types & {'archer','woodElf','monk'})
        flying=bool(types & {'griffin','pegasus'})
        mounted=bool(types & {'cavalier','unicorn'})
        category='ranged_and_flying' if ranged and flying else 'ranged_and_ground_mounted' if ranged and mounted else 'other'
        for table,label in [(roles,row['role']),(families,family+'|'+row['role']),(groups,category+'|'+row['role'])]:
            bucket=table.setdefault(label,dict(games=0,wins=0,losses=0,scenarios=set()))
            bucket['games']+=1;bucket['wins']+=int(row['success']);bucket['losses']+=int(not row['success']);bucket['scenarios'].add(row['scenario'])
    for table in [roles,families,groups]:
        for bucket in table.values():bucket['scenarios']=len(bucket['scenarios'])
    loss_count=sum(not row['success'] for row in baseline)
    both_lose=sum(not row['success'] and not public[key(row)]['success'] for row in baseline)
    teacher_only=sum(not row['success'] and public[key(row)]['success'] for row in baseline)
    oracle_union=sum(row['success'] or public[key(row)]['success'] for row in baseline)
    result=dict(scope='Completed development reports only. No training, evaluation, or process changes.',
        baseline_roles=roles,family_role=families,mechanism_groups=groups,baseline_losses=loss_count,
        losses_also_lost_by_public=both_lose,public_only_recoveries=teacher_only,
        retrospective_oracle_union=dict(wins=oracle_union,games=192,
            meaning='Per-completed-battle oracle union of two fixed policies; not an upper bound on imitation, PPO, or action-level search.'),
        source_sha256={str(path):sha(path) for path in [*paths.values(),SCENARIOS]})
    destination=HERE/'V2_REVIEW_FROM_CODEX_20261017.json'
    destination.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
