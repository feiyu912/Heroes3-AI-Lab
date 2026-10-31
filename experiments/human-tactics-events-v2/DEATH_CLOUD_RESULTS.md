# 尸巫死亡云（HT02）：原生事件验证、专家与反制实测结果

实验目录：`experiments/human-tactics-events-v2/`（隔离运行时）。
数据：`runs/cloud-pilot-01`（场景 16-23 × 双角色 × 2 种子 × 4 策略 = 128 局）。
场景：`lab/human-events-v2-death-cloud-16..23.vmap`（尸巫 10-25 + 长枪 20-60 +
弓手 15-40 + 骷髅 25-70；镜像军队；含亡灵用于排除规则验证）。
对手固定原生 BattleAI，配对可比。分析用每决策节点标志（节点索引不跨决策稳定，
详见 RETALIATION_BAIT_RESULTS.md 修订记录）。

## 1. 原生事件证实的机制（成立）

`battle_events` + 图节点标志直接证实（128 局、1643 个云攻击组、200 个含溅射的组）：

- **主目标物理伤害与范围云效果可区分**：SPELL_LIKE(64) 攻击组 + 目标
  SPELL_EFFECT(16) + spell_id；主目标（无 SECONDARY）与溅射目标（SECONDARY）
  各带原生 damage/killed。
- **亡灵/非生命排除规则原生证实**：
  - 非生命单位被云**溅射**：**0 次**（200 个含溅射组全部检查，PASS）。
  - 20 例"相邻但未受伤的亡灵"证明排除真实发生（ eligible 站位 + 免疫 = 无伤害事件）。
  - 87 例非生命（尸巫互射）作为**主目标**受伤：主目标吃的是攻击本身
    （与 INTERFACE_AUDIT "主目标物理射击仍须另计"一致），不是云效果。
- **友伤真实且频繁**：我方云对自己人的溅射 teacher 1725 / expert 1491 / random 0；
  敌方云对我方 1987（teacher）。云站位选择直接决定友伤——这是该战术的核心权衡。
- 副目标命中稀少（多数组 secondary=0）：BattleAI 很少让敌人站在云溅射位上。

## 2. cloud-exchange-v1（尸巫选位）：未验证有效（保留失败）

规则与 breath-exchange-v1 同一"能力攻击覆盖"逻辑：教师未选云射击、且存在主目标
交换估计为正的云射击时覆盖教师。 expert 局共覆盖 14 次（32 局），每次覆盖都是云射击。

配对结果（expert vs teacher，n=32 配对单元格）：
- 多数单元格差为 0（专家很少覆盖）；mean Δloss=**-1.59**，net Δwin=**0**，
  mean Δ友伤=**-7.3**。
- 机制指标方向：expert 副目标伤害 1011 > teacher 801（略高），
  **友伤 1491 < teacher 1725（更低）**——专家确实更倾向于低友伤的云位。
- 没有形成稳定的终局收益；n=32、效应小、方向不一致。

结论：**cloud-exchange-v1 相对 depth-2 教师无可区分收益，不授予已验证专家标签。**
可记录的次级发现：覆盖决策的友伤代理方向上有效（1491 vs 1725），但样本太小。

## 3. 反制：三代全部无效或无分化（同龙喷吐，如实记录）

| 版本 | 逻辑 | 结果 |
|---|---|---|
| dragon-threat-counter-v1 | 打龙/打尸巫优先 | **未测试**：与教师 0 分化 |
| dragon-threat-counter-v2 | 优先打 + 松散站位惩罚 | **有害**（龙喷吐试点 0/24 胜） |
| dragon-threat-counter-v3 | 仅按估计集火喷吐者/尸巫 | **无分化**：cloud pilot 48 局与教师逐格完全一致（251 云射击、18553 主伤、801 副伤、1725 友伤、3605 损失全部相同） |

结论：**未找到优于教师的合法反制**。教师已优先处理威胁；差异化尝试无效或有害。
反制保持"未认证"。

## 4. 失败条件与未知

- 未测试：Power Lich（更强云）、多尸巫、亡灵大军混合、非生命主力（排除规则的另一面）。
- 骷髅免疫只在本 fixture（骷髅 25-70）验证；未测石像鬼/机械/攻城单位排除。
- 云的精确范围参数（半径 0-1）未与规则文本逐像素核对，只验证了事件层的排除行为。
- 专家估计项（MeleeDmg 边）不含云溅射估计，副目标只用价值代理——机制上不可能最优，
  实验结果与之一致（无收益）。

## 5. 复现

```bash
bash experiments/human-tactics-events-v2/run-events-lab.sh \
  experiments/human-tactics-events-v2/analyze_death_cloud.py --tag cloud-pilot-01
bash experiments/human-tactics-events-v2/run-events-lab.sh \
  experiments/human-tactics-events-v2/audit_cloud_exclusion.py --tag cloud-pilot-01
```
