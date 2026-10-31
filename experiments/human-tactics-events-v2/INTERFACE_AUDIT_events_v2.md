# events-v2 接口审计：原生战斗事件层（human-tactics-events-v2）

日期：2026-10-18。对象为本窗口**隔离运行时** `/root/heroes3-ai-lab-events-v2`
（引擎源 `src/gym/vcmi` 的独立副本 + 独立构建目录 + 独立 data/config/cache/workers；
共享只读资源：venv 解释器、`/root/heroes3-ai-lab/onnxruntime`、全局资源锁
`/root/heroes3-ai-lab/evaluations/.pool-lock`）。

引擎基线：与主运行时的 gym/engine 提交一致的**副本**，仅叠加本窗口补丁
（`apply_native_patch.py`、`apply_native_patch_sides.py`，全部在实验目录内、可重放）。
主运行时 `/root/heroes3-ai-lab` 及正式 Windows VCMI/原生库**零修改**（构建路径重定向 +
仅在本副本内 ninja；已核对原 libmlclient.so 时间戳未变）。

## 1. 新增内容：battle_events（纯审计，非模型输入）

v15 观测字典新增一个附加键 `battle_events`（list[dict]）。**任何策略不得把它当作观测**
（本窗口专家/反制只依赖 nodes/edges/active_action_ids；模型输入完全不变，旧 checkpoint 兼容）。

每条事件字段（Python 侧为纯 JSON 类型）：

| kind | 值 | 说明 |
|---|---|---|
| ACTION_STARTED / ACTION_FINISHED | 0 / 1 | `BattleAction` 请求经 `StartAction`/`EndAction` pack 包裹；含 action_type（EActionType 枚举整数）、side、stack_number（CStack::unitId()，-1/-2 为英雄）、target_hexes / target_unit_value |
| ATTACK | 2 | 一次 `BattleAttack` group：attacker_id/attacker_side/attacker_node（图 Unit 节点下标，-1=当前图无此单位）、attack_flags（SHOT\=1, COUNTER\=2, LUCKY\=4, UNLUCKY\=8, BALLISTA\=16, DEATH_BLOW\=32, SPELL_LIKE\=64）、attack_spell_id、attack_tile，及 targets[] |
| BATTLE_END | 3 | result_type / winner（与 terminal_outcome 冗余但显式） |

targets[] 每项：defender_id/defender_side/defender_node、attacker_id/attacker_side/attacker_node、
damage（int64 原生伤害）、killed（击杀数量）、flags（KILLED\=1, **SECONDARY\=2**,
CLONE_KILLED\=8, SPELL_EFFECT\=16）、spell_id。

native 字段含义映射：
- `SECONDARY` = 非主目标（龙双格喷吐/死亡云等范围伤害的附带目标）→ **主/副目标可区分**。
- `COUNTER`（attack_flags&2）= 自动反击执行的攻击 → **主动攻击与自动反击可区分**；
  反击喷吐 = 二者同时成立。
- `SPELL_LIKE` + target `SPELL_EFFECT`+spell_id = 尸巫死亡云（spell_id 对应 SpellID 编号）。
- `attacker_side == defender_side` = 友伤（native 判定，不靠推断）。
- `attacker_node/defender_node` 与观测图 Unit 节点行下标对应（已死单位为 -1），
  实现方式：`IGraph::getUnitNodeIndexByUnitId()`（v15 schema 新增方法，本窗口实现）。

## 2. 信息流（可追溯链）

引擎 BattleActionProcessor::makeAttack → `BattleAttack`/`StartAction`/`EndAction` pack
→ NetPacksClient 回调 `battleAttack`/`actionStarted`/`actionFinished`
→ BAI_v15 override（本窗口新增）→ `State::onBattleAttack/onActionStarted/onActionFinished`
→ `State::battleEvents`（按 BAI 侧累积，随每次 `onActiveStack` 打入 SupplementaryData 后清空）
→ `ISupplementaryData::getBattleEvents()`（schema v15 新增纯虚，仅一个实现类）
→ connector `buildObsDict` 序列化为 obs["battle_events"]。

每个学习器/对手侧各自持有事件流（双 env 时两侧独立）。事件在**下一次该侧决策时**随观测
交付，语义为“自上一次该侧决策以来发生的原生事件”，与攻击日志 attackLogs 同一节律。

## 3. 已验证与已验证边界

已实测（冒烟 + 32 局 pilot，见 runs/smoke、runs/dragon-pilot-01）：
- 龙双格喷吐：ATTACK group 含主目标 + SECONDARY 副目标，原生 damage/killed 与之一致。
- 自动反击：COUNTER flag 事件流完整；反击喷吐（龙被近战后反击喷吐）可识别（pilot 中占比 ~42%）。
- SHOOT 远程、WAIT/DEFEND 等 ACTION 包裹完整。
- 图节点映射可用（已死单位记 -1）。
- 友伤 native 判定字段存在（本批次 dragon-breath fixture 中实测为 0，见结果文档）。

仍未实现/缺口（不得声称支持）：
- **主动英雄魔法**：无施法动作、无法术事件（仍仅 WAIT/DEFEND/MOVE/AMOVE/SHOOT）。
- **主动拒绝反击**：引擎无此动作；`counterAttacks.canUse` 剩余次数仍不可见
  （事件只记录“已发生的反击”，不预测未来反击）。
- 持久单位 ID 已暴露（attacker_id 等为 CStack::unitId()，battle 内稳定），
  但**图观测仍未直接给绝对数量/反击次数**（仅事件层有原生数量）。
- 复活/召唤的永久战损审计沿用 v15 terminal_outcome（本窗口 fixture 未含）。
- 任意初始 hex/朝向、障碍、城战、紧凑阵型透传等仍未实现（scenario-audit.json 记录）。
- 事件不包含隐藏信息：全部来自玩家可见对象与原生结果；**不含未来 RNG**。
- 双 env（OTHER_ENV）下事件同样按侧分流，但本窗口 pilot 暂只用单 env + BattleAI 对手。

## 4. 复现

```bash
# 从原始引擎副本重建本窗口补丁（幂等脚本，仅作用于隔离运行时副本）
python3 experiments/human-tactics-events-v2/apply_native_patch.py        # 需在未打补丁的副本上
python3 experiments/human-tactics-events-v2/apply_native_patch_sides.py  # 侧别增量补丁
# 本副本实际构建方式（路径重定向后增量 ninja）：
#   bash experiments/human-tactics-events-v2/remap_build.sh
#   bash experiments/human-tactics-events-v2/remap_and_build_connector.sh
# 冒烟：
bash experiments/human-tactics-events-v2/run-events-lab.sh \
  experiments/human-tactics-events-v2/run_episode_events.py \
  --scenario 0 --role attacker --seed 2026102801 --policy teacher \
  --checkpoint none --output runs/smoke/x.json
python3 experiments/human-tactics-events-v2/inspect_events.py runs/smoke/x.json.gz
```

验证命令输出：`runs/smoke/*.json`（29 步、49 attacks、15 counter、2 secondary）。
事件内容样本见 `runs/smoke/teacher-dragon-0-attacker.json.gz` 与
`inspect_events.py` 输出（d8：龙 u2 喷吐主目标 u4 dmg101/kill11 + 副目标 u5 dmg174/kill4）。

## 5. 与 v15 模型输入的兼容性

nodes/edges/active_action_ids 的编码零变化；`battle_events` 为纯附加键。
旧模型（B64 等）与旧 connector 构建的输入张量形状一致；
本窗口 runner 只在审计字段上新增读取，不用作任何策略输入。
