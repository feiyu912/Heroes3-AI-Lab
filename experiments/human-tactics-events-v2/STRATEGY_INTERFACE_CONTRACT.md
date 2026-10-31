# 战术窗口 → 战略层接入契约（events-v2）

本文件定义 `human-tactics-events-v2` 向战略窗口提供的**可复用战斗策略接口与评估记录**
（对应任务书第七节）。战略层负责大地图路径/经济/招募/目标/完整胜负；本窗口负责战术事件、
专家/反制、示范与局部能力验证。两窗口不得同时重写同一接口。

## 1. 当前可供战略层的能力（如实）

| 能力 | 状态 | 证据 |
|---|---|---|
| 原生战斗事件记录 | **可用**（审计数据） | `battle_events`（攻击组/主副目标/反击/友伤/法术效果/动作包裹），INTERFACE_AUDIT_events_v2.md |
| 对局可重放记录 | **可用** | 每局 json+gz：观测、合法动作、执行动作、逐决策事件、原生终局；events_provenance 冻结+双验 |
| 已验证战术专家 | **无**（三条均未通过冻结测试） | DRAGON_BREATH / RETALIATION_BAIT / DEATH_CLOUD _RESULTS.md |
| BC 模型（events-v2-bc-01） | **探索性，未验证有效** | NLL 10.47→7.64（205 决策），配对评估见下文第 4 节 |
| 价值头/胜率估计 | **不可用**：未校准，不得把 value 或动作概率当获胜概率 | 同主窗口立场 |

## 2. 战斗策略接口（供战略层调用）

```python
# 运行一局并取原生结果（isolated runtime；单局单进程）
run-events-lab.sh run_episode_events.py \
  --scenario <idx> --role attacker|defender --seed <int> \
  --policy expert|counter|bait|bait-counter|teacher|model|random \
  --checkpoint <pt> --output <path.json>
# 输出: completed/terminated/truncated/success/invalid_actions/
#      permanent_army_loss_by_creature/permanent_army_loss_units/
#      terminal_outcome(result_type/winner/casualties/initial_armies)/
#      native_attacks/native_counter_attacks/native_secondary_hits
```

战略层用于"是否打、用什么兵、预计永久损失和不确定性"的接口约束：
- **返回未知时不编造**：当前无可靠胜率/永久损失预测器；BC 模型未验证。
  战术层只提供"已发生对局的原生结果"与"专家/教师/随机基线的配对对照"。
- 永久战损按生物种类记录（`permanent_army_loss_by_creature`），**不要把不同兵种
  阵亡数当等价值军力**（与主窗口一致）。
- 非法动作/截断/非正常终局单列，不计胜负。

## 3. 事件数据结构（摘要）

```
battle_events: [
  {kind:0|1 ACTION_STARTED|ACTION_FINISHED, action_type, side, stack_number,
   stack_node, target_hexes, target_unit_value},
  {kind:2 ATTACK, attacker_id/side/node, attack_flags(SHOT1/COUNTER2/SPELL_LIKE64...),
   attack_spell_id, attack_tile,
   targets:[{defender_id/side/node, attacker_id/side/node, damage, killed,
             flags(KILLED1/SECONDARY2/SPELL_EFFECT16), spell_id}]},
  {kind:3 BATTLE_END, result_type, winner}
]
```
单位 id 为 CStack::unitId()（battle 内稳定）；`*_node` 为图 Unit 节点下标（-1=已死/不在当前图）。
`SECONDARY`+`SPELL_EFFECT`+spell_id 标识死亡云溅射；`COUNTER` 标识自动反击。

## 4. 训练与独立测试现状（events-v2-bc-01）

- 数据：205 决策（62 Q3 配对验证 + 143 Q2 能力事件验证）；Q3 来自冻结测试集
  机制+损失双通过的 2 个单元格；Q2 标注为探索性，不默认高质量。
- BC：policy-head only，60 步，lr 1e-4，NLL 10.47→7.64；graph/value 权重零变化。
- **独立测试**：在 BC 未见过的龙喷吐冻结测试场景（6/7）上与 B64 基线配对；
  结果见 `runs/bc-eval-b64/` 与 `runs/bc-eval-bc/` 及 TRAINING_RESULTS.md。
- 未执行：主协议 48 场景×双角色×双子花的普通战斗保留集评估（需要主协议开发集
  评估入口，建议后续窗口按主协议执行——本窗口只在战术 fixture 上配对）。

## 5. 资源与并行约束（再次确认）

- 本窗口实验只写 `experiments/human-tactics-events-v2/` 与隔离运行时
  `/root/heroes3-ai-lab-events-v2/`；未触碰 `/root/heroes3-ai-lab` 任何文件
  （原 libmlclient.so 时间戳未变，已核）。
- 所有游戏模拟经共享锁 `/root/heroes3-ai-lab/evaluations/.pool-lock`；
  本窗口未启动任何 24-worker 训练；未与战略窗口的 GPU 学习器并行。
- 24 并发上限为两窗口共享，不是每窗口各 24。
