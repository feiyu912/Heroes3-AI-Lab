# 训练与独立测试结果（events-v2 BC-01）

对应任务书第六/八节。数据门禁：只有"事件验证 + 配对对照有效"的示范进入 BC；
本窗口三条战术专家均未通过冻结测试（见各 RESULTS.md），因此**没有任何战术获得
Q3 全网球认证**；Q3 示范仅来自"配对损失改善 + 机制同向"双通过的 2 个单元格
（retaliation-bait 冻结测试集的 bait-retaliation-bait-14-attacker-s2026102802 与
bait-retaliation-bait-15-defender-s2026102801），其余为 Q2 能力事件验证示范
（合法轨迹+正常终局+所选能力攻击被原生事件确认命中），明确标注探索性。

## 1. 示范集（demonstrations-v1.jsonl，205 决策）

| 层级 | 数量 | 来源 | 门禁 |
|---|---|---|---|
| Q3-paired-verified | 62 | bait 冻结测试 2 单元格 | vs teacher 损失降 AND 主力反击伤害降（机制同向） |
| Q2-ability-verified | 143 | dragon-pilot-02 + cloud-pilot-01 的 expert 局 | 正常终局 + 所选 breath/cloud 攻击被原生事件确认造成伤害 |

双侧角色均有；动作 ID 仅在对应观测内合法（指数为合法列表下标）。

## 2. BC 训练（events-v2-bc-01）

- 初始化：B64（`models/graph-finetune/1792068859379237126/update-64.pt`，SHA 已冻结）。
- CPU 预检先行：205 样本、codec 维度恢复、双侧、标签直方图正常（无 GPU）。
- CUDA BC：仅 policy_head__ 参数（16 个）可训；Adam lr1e-4、batch16、60 步、
  seed 2026102901；graph/value 权重零变化（逐参数断言）。
- NLL：10.4734 → 7.6410（训练集内拟合；**不证明战斗改善**）。
- 资源：单 GPU 学习器检查 + 共享池锁；未启动 24worker。
- 产物：`/root/heroes3-ai-lab-events-v2/models/events-v2-bc-01.pt` +
  `runs/bc-preflight.json` + `runs/events-v2-bc-01.json`（report）。

## 3. 独立测试（BC vs B64，龙喷吐冻结测试场景 6/7，BC 未见过）

n=8 配对单元格（2 场景 × 2 角色 × 2 种子）：

| 单元格 | B64 | BC |
|---|---|---|
| 06 attacker s801/s802 | L/107u, L/107u | L/107u, L/107u |
| 06 defender s801/s802 | W/75u, W/73u | W/98u, W/105u |
| 07 attacker s801/s802 | W/65u, W/51u | L/75u, W/34u |
| 07 defender s801/s802 | W/53u, L/75u | W/70u, L/75u |

**mean Δloss(BC-B64) = +8.12**（BC 更差），1 个胜场翻负（07-attacker-s801），
1 个大优（07-attacker-s802 51→34）。效应方向以负为主但 n=8 方差大。

结论：**探索性 BC 未能在未见场景上产生战斗收益，不建议晋升为候选模型。**
与工程史上两次脚本 BC（185 标签、63 标签）结论一致：覆盖/标签拟合 ≠ 战斗能力。
BC 模型保留在隔离运行时作为失败证据，不进入任何正式评估。

## 4. 未执行项与原因

- 主协议 48 场景普通战斗保留集评估：未执行（需要主协议开发集评估入口；本窗口只在
  战术 fixture 上配对，见 STRATEGY_INTERFACE_CONTRACT.md 第 4 节）。
- 云/诱反击 test 场景上的 BC 评估：cloud Q2 示范来自全部 8 个云场景（含 test 22/23），
  在这些场景上评估不独立；bait test 单元格被 Q3 选出并进入 BC 数据，同样不独立。
  仅龙喷吐 test（6/7）对 BC 完全未见，故只在该拆分上做独立测试。
- 混合 PPO（专项/普通/反制/历史对手）：**未启动**——前置条件（至少一条验证有效的
  战术专家/反制以形成专项训练信号）未满足；按任务书纪律不以次数堆叠冒充能力。

## 5. 复现

```bash
bash experiments/human-tactics-events-v2/run-events-lab.sh \
  experiments/human-tactics-events-v2/bc_train_events.py --preflight \
  --output runs/bc-preflight.json
bash experiments/human-tactics-events-v2/run-bc-cuda.sh \
  --output /root/heroes3-ai-lab-events-v2/models/events-v2-bc-01.pt
# 独立测试：
python3 experiments/human-tactics-events-v2/run_pilot_events.py --tactic dragon-eval \
  --policies model --roles attacker defender --scenarios 6 7 \
  --seeds 2026102801 2026102802 --tag bc-eval-bc \
  --checkpoint /root/heroes3-ai-lab-events-v2/models/events-v2-bc-01.pt
```
