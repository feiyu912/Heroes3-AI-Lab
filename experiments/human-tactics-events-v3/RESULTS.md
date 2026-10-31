# events-v3 修复与真实验证（2026-10-18）

本轮完成事件记录/归因修复及最小反击机制验证，未完成有效专家、反制与模型能力提升。没有启动 BC 或 PPO，没有晋升模型。

## 真实执行

三条战术各选一个已使用场景，以 teacher 对 BattleAI、同 seed 2026101807、双方角色执行，共 6 局；另把龙喷吐攻方实际重新执行 1 次。7 局均原生正常终局、0 非法、0 截断，206/206 动作有唯一匹配的 ACTION_STARTED/FINISHED，115 次选中行动内确有正伤害。WAIT/DEFEND、后续对手攻击、自动反击不冒充主动伤害标签。

每局最后一次 env.step 返回的事件单独批次存档；7/7 最终批次均含 BATTLE_END，winner 与 terminal_outcome 一致。原生终局 casualties 审计通过。重复龙局的完整图前后状态、合法动作、实际动作、原生事件和终局结果合并 trace SHA 相同，不只是相同胜方/步数。详见 VALIDATION_RESULTS.json；每个 summary 指向完整 json.gz 及 SHA。

这 7 局是工程验证，场景均已被历史实验使用，不能称独立性能测试，也不提供胜率提升结论。

## 有限反击：真正的最小局面与无限反击对照

新建 2 张非镜像、无主动魔法、无英雄技能的机制夹具，置于 `/root/heroes3-ai-lab-events-v3/data/vcmi/Maps/events-v3-probes/`。我方为 6 个单兵枪兵 + 160 枪兵；对方为单堆 40 swordsman 或单堆 30 royalGriffin。两场均通过共享锁、串行真实执行，0 非法/截断、完整原生终局。它们用于机制实验，不用于公平胜率或教师优劣比较。

普通 swordsman：round 3 稳定单位 ID 7 依次受到枪兵 ID 1/2/3/4 的普通主目标近战，分别受到 1/2/1/2 伤害、始终存活。它对 ID 1 发出 COUNTER，对 ID 2/3/4 均未发出 COUNTER；round 4/5/6 再次观察到同轮首次反击、随后不再反击。

无限反击 royalGriffin：round 2 稳定单位 ID 7 受到枪兵 ID 2/3/4/5 的 4 次普通近战，4 次均发出 COUNTER，且每次攻击后存活。原生配置 `vcmi/config/creatures/castle.json` 的 royalGriffin 明确是 UNLIMITED_RETALIATIONS；普通 griffin 只有额外一次，不能拿普通 griffin 充当无限反击对照。

逐攻击的 batch/index/round/双方稳定 ID、伤害、是否死亡和匹配 COUNTER 位置记录于 RETALIATION_PROBE_RESULTS.json。COUNTER 的预算主体是其 attacker_id，不是受到反击的 defender_id。跨 round 的事件批次由于没有每事件 round，全部保留 unknown，不强行归入 round_before。

以上证明当前引擎中有限反击与无限反击的差异。尚未证明单兵诱饵使主力永久战损下降，也没有专家/反制认证。

## 代码边界与数据纪律

- 旧 events-v2 实验文件只读。复用已有 ML-on 事件运行时，不重建、不替换任何旧二进制；新增 worker 目录不等于旧运行时目录完全无写入。
- 新 worker 将原 Data/Mods 和地图链接为只读复用；新的机制地图来自单独 v3 路径。没有写入旧地图目录。战略 ML-off 运行时不混用这些动态库。
- observation_before/action/observation_after 与一次返回的 events batch 分离存储；reset 批次只存一次，终局批次包含在最后一步，不重复计数。
- 单个 env 每 step 只发一个请求；唯一我方 native action、类型、已知 actor ID、匹配 finish 构成严格窗口。缺失/多余窗口失败关闭。初次缺稳定 actor 映射时，明确记录 single_env_request_protocol，不谎称已独立按 ID 匹配。
- 单位身份按返回批次的图索引映射稳定 ID。死后节点 -1 且历史未知时仍为 unknown，不把相对价值置零归入诱饵；相对 VALUE_REL 不作为恒定身份属性。
- 审计 events 与 terminal_outcome 从策略输入显式剔除。所有选择仅来自合法动作集合。
- 每局冻结新代码、依赖库、连接器、地图、英雄配置，局中/局末复核 SHA。代码与配置快照按内容 SHA 保存，避免后来修复代码使早期 run 无法复核。
- 115 条动作事件对应最多为 Q2-event-correspondence；当前 BC 资格全部为 0。没有配对净收益与独立战术认证，不自动升级 Q3。
- v2 事后筛选的 bait test 14/15 与 cloud test 22/23 保持已使用状态，不重新包装成未见测试。

## 复现

在 WSL 中运行，所有输出路径必须是新路径，不能覆盖已有局：

```bash
/root/heroes3-ai-lab/venv/bin/python /mnt/g/Heroes3-AI-Lab/experiments/human-tactics-events-v3/check_event_audit.py
bash /mnt/g/Heroes3-AI-Lab/experiments/human-tactics-events-v3/run-events-lab.sh /mnt/g/Heroes3-AI-Lab/experiments/human-tactics-events-v3/run_episode.py --scenario 0 --role attacker --seed 2026101807 --policy teacher --output /mnt/g/Heroes3-AI-Lab/experiments/human-tactics-events-v3/runs/new-reproduction/dragon.json
bash /mnt/g/Heroes3-AI-Lab/experiments/human-tactics-events-v3/run-events-lab.sh /mnt/g/Heroes3-AI-Lab/experiments/human-tactics-events-v3/validate_runs.py
/root/heroes3-ai-lab/venv/bin/python /mnt/g/Heroes3-AI-Lab/experiments/human-tactics-events-v3/analyze_probes.py
```

生成机制地图只在尚不存在时执行 generate_retaliation_probes.py；默认拒绝覆盖。已有地图通过 retaliation-probes.json 内 SHA 核验。

后续重点是利用已证实的动作顺序规律，实现与基线不同且能减少主力战损的 WAIT/诱饵策略，并预先划分全新变体与双方角色验证。机制成立不等于这一步已经实现。

## 旧 v2 只读恢复

实际扫描 453 份 json.gz：452 份为旧 v2 schema，另 1 份为旧窗口后加的 v3 smoke（跳过）。452 份共 12915 个决策；把下一决策携带的事件重新关联前一个动作后，可恢复 12463 个严格动作窗口。每份最后动作的返回事件均未归档，合计 452 个末尾批次不可恢复。此计数是归档文件数，未当作独立统计样本或去重胜率。

V2_RECOVERY_AUDIT.json 保存每份原始 SHA、决策→事件索引、匹配窗口和永久缺失状态。它是恢复索引而非认证示范集，BC 资格全部保持 0；没有改写旧文件，也没有补造终局事件。
