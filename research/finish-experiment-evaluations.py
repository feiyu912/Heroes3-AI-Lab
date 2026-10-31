"""Complete ablation battles, independent opponents and native teacher timing."""
from pathlib import Path
import json
import subprocess

root = Path('/mnt/g/Heroes3-AI-Lab/research')
records = []


def evaluate(name, checkpoint, policies, opponent='BattleAI', teacher_turns=2, cases=range(26, 36), seeds=8):
    output = root / f'{name}.json'
    subprocess.run(['python3', str(root / 'evaluate-battles.py'), '--checkpoint', checkpoint,
                    '--scenario-file', str(root / 'scenarios-v2.json'), '--scenarios', *map(str, cases),
                    '--policies', *policies, '--seeds', str(seeds), '--workers', '12',
                    '--opponent', opponent, '--teacher-turns', str(teacher_turns), '--output', str(output)], check=True)
    result = json.loads(output.read_text())
    record = dict(name=name, checkpoint=checkpoint, opponent=opponent, output=str(output), summary=result['summary'])
    records.append(record)
    (root / 'supplemental-evaluations.json').write_text(json.dumps(records, indent=2))


for variant in ['mlp64', 'mlp-no-value']:
    evaluate('balanced-bc-' + variant + '-test',
             f'/root/heroes3-ai-lab/models/bc-balanced-ablation-v1/{variant}.pt', ['model'])
suite = json.loads((root / 'ppo-research-suite.json').read_text())
ranking = []
for experiment in suite:
    result = json.loads(Path(experiment['validation_report']).read_text())
    summary = result['summary'][0]
    if summary['truncated'] == 0 and summary['invalid_actions'] == 0:
        ranking.append((summary['win_rate'], -summary['mean_permanent_units_lost'], experiment))
best = max(ranking, key=lambda v: v[:2])[2]
(root / 'selected-trained-model.json').write_text(json.dumps(dict(
    **best, selection='Highest validation win rate, then lowest validation unit casualties; held-out test excluded from selection'), indent=2))
for opponent in ['StupidAI', 'MMAI_RANDOM']:
    evaluate('independent-' + opponent, best['checkpoint'], ['teacher', 'model'], opponent=opponent, seeds=4)
for horizon in [2, 4]:
    evaluate(f'teacher-timing-{horizon}', best['checkpoint'], ['teacher'],
             teacher_turns=horizon, cases=[26, 28, 31, 35], seeds=2)
print('Supplemental battle evaluations complete')
