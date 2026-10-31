# 龙喷吐（HT01）：原生事件验证、专家与反制的实测结果

实验目录：`experiments/human-tactics-events-v2/`（隔离运行时 `/root/heroes3-ai-lab-events-v2`）。
数据：`runs/dragon-pilot-01`（32 局）、`dragon-pilot-02`（96 局）、`dragon-pilot-03`（48 局）。
场景：`lab/human-events-v2-dragon-breath-00..07.vmap`（绿龙 2-6 + 长枪 20-65 + 弓手 12-40 + 剑客 8-25，
镜像军队，四个槽位随机，紧/松阵型，双角色，两个引擎种子）。
对手固定为原生 BattleAI；同场景+角色+种子下只有**我方策略**不同 → 配对可比。

## 1. 原生事件证实的机制（这是本战术的硬证据）

从 `battle_events`（ATTACK group + SECONDARY 目标 + COUNTER flag）直接证实：

- **双格喷吐真实发生且主/副目标可区分**：ATTACK 事件含主目标（无 SECONDARY 标志）与
  附带目标（SECONDARY=2），各带原生 damage/killed。样本（teacher 冒烟局 d8）：
  龙 u2 喷吐主目标 u4 dmg=101/killed=11，副目标 u5 dmg=174/killed=4。
- **副目标伤害可以高于主目标**（上例即如此）——覆盖代理只数"敌目标个数"会完全误判收益。- **主动喷吐 vs 反击喷吐可区分**：COUNTER flag。修正标志后的 pilot-02：我方龙喷吐
  teacher 199 次 / 其中反击 78 次（~39%）；expert 177/66（~37%）。
  → "龙只会主动喷"或"喷吐都是主动行为"的说法被证伪。
- **友伤**：native 判定字段（attacker_side==defender_side）工作正常；
  dragon-breath fixture 批次中实测我方龙喷吐友伤不为 0（pilot-02：teacher 448、
  expert 341、counter-v2 590），策略相关。
- **副目标命中稀少**：多数场景我方/敌方龙的副目标伤害为 0（BattleAI 很少让龙站出双目标位）。
- 对照策略合法性：4 个策略 176 局全部正常终局（truncated=0），无非法动作。

## 2. 正向专家 breath-exchange-v1：未验证有效（保留失败）

规则：当教师未选喷吐动作、且存在主目标交换估计为正的喷吐 AMOVE 时覆盖教师。
覆盖触发 0-2 步/局（多数局面教师自己已选喷吐）。

配对结果（expert vs teacher，同场景+角色+种子，n=24，dragon-pilot-02）：
- 胜场 12 vs 12（其中 2 格 expert 由负转胜、2 格由胜转负）。
- 我方永久损失差 Δloss：均值 **-0.33**（-4,-3,-2,-1 各若干，+1,+2 若干，其余 0），正负混合。
- 我方副目标伤害 expert 2429 < teacher 2881（专家选的喷吐附带略少、更偏单目标——方向保守，
  与"不能无条件双目标优先"的纪律一致），但没有转化为终局收益。

结论：**breath-exchange-v1 相对 depth-2 教师无可区分收益，不授予"已验证专家"标签。**
教师在这些 fixture 中已覆盖主要喷吐机会；专家的估计项（主交换 + 副目标价值代理）未超过教师。

## 3. 反制：三代全部失败或无效（如实记录）

| 版本 | 逻辑 | 结果 |
|---|---|---|
| dragon-threat-counter-v1 | 打龙优先，否则教师 | **未测试**：与教师动作 0 分化（24 局全部一致，教师本身已优先打龙） |
| dragon-threat-counter-v2 | 打龙优先 + 远离龙可攻击 hex 的松散站位惩罚 | **有害**：0/24 胜，我方龙几乎不再主动攻击（喷吐几乎全是反击），损失 1968 vs 1877，敌方副伤 5288 vs 854。机制：站位惩罚压制了攻击节奏 |
| dragon-threat-counter-v3 | 仅按估计 defender HP 损失集火喷吐者，否则教师 | **无分化**：48 局与教师逐格完全一致（损失、胜场、伤害总量全部相同）。教师已执行同样的集火 |

结论：**未找到优于教师的合法反制**。fixture 中 BattleAI 的龙很少找到副目标，教师的深度2
搜索本身已在威胁出现时优先集火；两种差异化尝试分别无效和有害。反制保持"未认证"。

## 4. 失败条件与未知

- 未测试：任意初始 hex/朝向、障碍、城战、紧致阵型透传（scenario-audit 记录的 pending 项）。
- 未测试：飞龙/铠龙/骨龙/幽灵龙（GhostDragon 无喷吐，不能认证龙息；未测）、多龙组合。
- 剩余反击次数不可见：事件只能证明"已发生的反击"，不能预测龙下一次近战是否还会被反击。
- 友伤风险仅在 pilot-02 出现（66-874，按策略不同），未系统验证"零友伤喷吐选择"的收益。
- n=24 配对只能排除大效应；不能证明"专家在别的局面也无效"。

## 5. 复现

```bash
bash experiments/human-tactics-events-v2/run-events-lab.sh \
  experiments/human-tactics-events-v2/analyze_dragon_breath.py --tag dragon-pilot-02
bash experiments/human-tactics-events-v2/run-events-lab.sh \
  experiments/human-tactics-events-v2/analyze_tactic_events.py --tag dragon-pilot-03
```

原始记录：每局 `runs/*-*.json`（摘要）+ `.json.gz`（全部决策观测、合法动作、执行动作、
逐决策 battle_events、终局）；`manifest.json` 记录每局状态与耗时。
代码版本由 `events_provenance.freeze` 在局内/局末双重校验（运行中改代码会被拒绝——
该机制在 pilot-03 触发过一次并正确拦截）。
