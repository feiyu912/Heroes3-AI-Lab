from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

root = Path(__file__).parent
results = json.loads((root / 'GOAL_RESULTS.json').read_text())
lookup = {r['name']: r for r in results['experiments']}
names = ['random', 'heuristic', 'BC-gnn', 'ppo-balanced-seed-20261014', 'ppo-balanced-seed-20261015', 'ppo-balanced-seed-20261016']
labels = ['随机合法', '简单启发式', 'BC起点', 'PPO种子1', 'PPO种子2', 'PPO种子3']
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
fig, ax = plt.subplots(figsize=(10, 5.4), dpi=180)
values = [100 * lookup[n]['win_rate'] for n in names]
intervals = [lookup[n]['wilson95'] for n in names]
error = [[v - 100 * ci[0] for v, ci in zip(values, intervals)],
         [100 * ci[1] - v for v, ci in zip(values, intervals)]]
bars = ax.bar(labels, values, color=['#a6a6a6', '#a6a6a6', '#72a5ce', '#3480b5', '#3480b5', '#3480b5'], yerr=error, capsize=4)
ax.axhline(50, color='#bc4d45', linestyle='--', label='BattleAI 对自身：50%')
for bar, value, ci in zip(bars, values, intervals):
    label = f'{value:.2f}%' if value < 2 else f'{value:.1f}%'
    ax.text(bar.get_x()+bar.get_width()/2, 100*ci[1]+1.5, label, ha='center', fontsize=11)
ax.set_ylim(0, 85)
ax.set_ylabel('对 BattleAI 的实际战斗胜率（%）')
ax.set_title('固定普通战斗测试：强化学习前后对照', pad=16)
ax.legend(loc='upper left')
ax.spines[['top', 'right']].set_visible(False)
ax.set_axisbelow(True)
ax.grid(axis='y', alpha=.2)
fig.text(.06, .02, '每个模型160场：10个未训练的军队场景 × 双方控制 × 8种子。误差条为Wilson 95%；同场景相关性与跨训练种子区间见报告。', fontsize=8.5)
fig.tight_layout(rect=(0, .055, 1, 1))
fig.savefig(root / 'goal-battle-results.png')
fig.savefig(root / 'goal-battle-results.svg')
print('Saved battle result figures')
