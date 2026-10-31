"""Paired battle comparisons and confidence intervals clustered by scenario."""
from collections import defaultdict
import json
from pathlib import Path
import numpy as np

root = Path('/mnt/g/Heroes3-AI-Lab/research')


def read(name):
    return json.loads((root / name).read_text(encoding='utf-8-sig'))


def cluster_interval(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[row['scenario']].append(float(row['success']))
    means = np.array([np.mean(v) for v in groups.values()])
    rng = np.random.default_rng(20261014)
    sampled = means[rng.integers(len(means), size=(20000, len(means)))].mean(1)
    return np.percentile(sampled, [2.5, 97.5]).tolist()


baselines = read('balanced-classical-baselines.json')
results = []
for policy in ['teacher', 'heuristic', 'random']:
    rows = [r for r in baselines['battles'] if r['policy'] == policy]
    summary = next(r for r in baselines['summary'] if r['policy'] == policy)
    results.append(dict(name=policy, **summary, scenario_cluster95=cluster_interval(rows)))
for architecture in ['mlp', 'attention', 'gnn']:
    data = read(f'balanced-bc-{architecture}-test.json')
    results.append(dict(name='BC-' + architecture, **data['summary'][0],
                        scenario_cluster95=cluster_interval(data['battles'])))
bc_rows = read('balanced-bc-gnn-test.json')['battles']
bc_lookup = {(r['scenario'], r['role'], r['seed']): r for r in bc_rows}
suite = read('ppo-research-suite.json')
for experiment in suite:
    data = json.loads(Path(experiment['test_report']).read_text())
    rows = data['battles']
    base_architecture = 'mlp' if experiment['name'] == 'ppo-balanced-mlp' else ('attention' if experiment['name'] == 'ppo-balanced-attention' else 'gnn')
    comparison_rows = read(f'balanced-bc-{base_architecture}-test.json')['battles']
    comparison_lookup = {(r['scenario'], r['role'], r['seed']): r for r in comparison_rows}
    differences = defaultdict(list)
    improvements = regressions = 0
    for row in rows:
        key = (row['scenario'], row['role'], row['seed'])
        baseline = comparison_lookup[key]
        difference = float(row['success']) - float(baseline['success'])
        improvements += difference > 0
        regressions += difference < 0
        differences[row['scenario']].append(difference)
    means = np.array([np.mean(v) for v in differences.values()])
    rng = np.random.default_rng(20261014)
    sampled = means[rng.integers(len(means), size=(20000, len(means)))].mean(1)
    result = dict(name=experiment['name'], **data['summary'][0],
                  paired_base_architecture=base_architecture,
                  scenario_cluster95=cluster_interval(rows), paired_improved=int(improvements),
                  paired_regressed=int(regressions), paired_delta_vs_BC=float(np.mean(means)),
                  paired_delta_scenario_cluster95=np.percentile(sampled, [2.5, 97.5]).tolist())
    results.append(result)
seeds = [r for r in results if r['name'].startswith('ppo-balanced-seed-')]
seed_experiments = [e for e in suite if e['name'].startswith('ppo-balanced-seed-')]
scenario_names = sorted({r['scenario'] for r in bc_rows})
seed_case_rates = []
for experiment in seed_experiments:
    rows = json.loads(Path(experiment['test_report']).read_text())['battles']
    seed_case_rates.append([np.mean([r['success'] for r in rows if r['scenario'] == name]) for name in scenario_names])
matrix = np.asarray(seed_case_rates)
rng = np.random.default_rng(20261014)
seed_indices = rng.integers(len(matrix), size=(20000, len(matrix)))
case_indices = rng.integers(len(scenario_names), size=(20000, len(scenario_names)))
joint_samples = matrix[seed_indices[:, :, None], case_indices[:, None, :]].mean((1, 2))
bc_case_rates = np.array([np.mean([r['success'] for r in bc_rows if r['scenario'] == name]) for name in scenario_names])
paired_samples = joint_samples - bc_case_rates[case_indices].mean(1)
output = dict(experiments=results, ppo_training_seeds=len(seeds),
               ppo_mean_two_level_bootstrap95=np.percentile(joint_samples, [2.5, 97.5]).tolist(),
               ppo_mean_delta_vs_BC_two_level_bootstrap95=np.percentile(paired_samples, [2.5, 97.5]).tolist(),
               ppo_seed_mean_win_rate=float(np.mean([r['win_rate'] for r in seeds])),
               ppo_seed_min_win_rate=min(r['win_rate'] for r in seeds),
               ppo_seed_max_win_rate=max(r['win_rate'] for r in seeds),
               scope='Fixed held-out10scenarios;8 independent engine seeds per side. Scenario-cluster bootstrap accounts for within-scenario correlation;3 training seeds reported individually; no population claim beyond suite')
(root / 'GOAL_RESULTS.json').write_text(json.dumps(output, indent=2))
print(json.dumps(output), flush=True)
