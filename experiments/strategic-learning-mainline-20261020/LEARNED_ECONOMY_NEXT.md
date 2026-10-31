# 下一能力覆盖 epoch：模型选择一次真实建造

状态：2026-10-20，仅 CPU 源码检查与实施建议；没有改运行代码，没有编译、运行 native 或 GPU。运输 v4 继续搁置。本文不是已取得建造学习资格的声明。

建议下一独立能力覆盖 epoch 只增加 **BuildStructure**，暂不增加招募动作。不改变现有终局奖励、PPO、地图、对手或战斗代理；不与另一个效率 reward 对照合并。root 提供的当前结果为 T2 八格 2742 rows / 172 CUDA steps、DEV 6/8→6/8；这些结果没有说明模型能学经济，因为当前经济根本不是它可选的动作。

## 实际源码证明的边界

以下路径均已实际读取。`src/vcmi-adv` 指 **WSL `/root/heroes3-ai-lab/src/vcmi-adv`**，不是 G 盘另一棵 vcmi 树；实验文件位于 `G:/Heroes3-AI-Lab/experiments/`。行号是本次检查的冻结文件行号。

| 源码位置 | 当前行为及含义 |
| --- | --- |
| WSL `AI/DirectorAI/CDirectorAI.cpp:387`、`:392`、`:511` | accepted 工作树 `advanceTurn()` 在移动前调用 `issueEconomy()`；固定优先级建造、自动整栈转移、最大可支付数量招募。 |
| `strategic-director-terminal-drain-v3/candidate/AI/DirectorAI/CDirectorAI.cpp:414`、`:419`、`:557` | 已资格 capsule03 候选同样先执行经济脚本；应以这份冻结候选作为新候选的起点，不能把恢复后的 accepted 工作树旧控制时序当成 capsule03。 |
| 同文件 `:575`、`:584`、`:591`、`:603` | 固定 building priorities；真实 `canBuildStructure()==ALLOWED`，dwelling 可解析缺失前置；调用 `cb->buildBuilding()`。不是模型选择。 |
| 同文件 `:625`、`:636`、`:644` | 招募按等级降序，以实际库存及全资源支付能力确定 amount，再直接 `recruitCreatures()`。 |
| 同文件 `:457`、`:460`、`:492`、`:495` | 经济请求绑定独立 `pendingEconomyRequest`；经济 ACK 清脚本等待后继续，不构成 policy decision 的 PPO 事务。 |
| 同文件 `:738`、`:749`、`:753`、`:763`、`:774` | schema4 明确只生成 move/end_turn；只有 gold/wood/ore，own_towns 只有位置与军力，没有 town ID、建筑或成本。真实 roster 必须恰好一名英雄。 |
| `strategic-policy-v3/encoder.py:89`、`:103`、`:110` | 严格验证 schema4；任何其他 op 被拒绝。`model.py:45` 起的 forward 也约束末尾两种操作位，并保留 movement prior / stop bias。 |
| `strategic-typed-training-v1/admit_episode_v5.py:24`、`:27`、`:39` | 接纳真实 policy 决策，奖励为终局胜负；逐行重放 action/logprob/value/RNG。脚本经济不能事后伪造成模型样本。 |

增加旧 schema4 训练次数不会扩大其 action space，也不会使经济脚本的选择产生 policy 梯度。只在 observation 加建筑信息同样不够：必须同时生成候选、由模型选择、发送真实请求并将这笔事务接到训练样本。

## 最小行为改动

1. 新建隔离候选、新 capsule/manifest 和显式新 schema/epoch；旧 capsule03、schema4、模型、optimizer、审计及已跑数据完全冻结。继续仅支持真实 exactly-one-hero，建造 actor 的语义是 player/town，hero 字段仅保留真实决策上下文，不能伪称英雄执行建造。
2. 每 own turn 开一个建造选择窗口，在任何可选经济花费之前，请模型从 **真实合法 build + 原有 move + 真实 end_turn** 中选择。最多一次 policy build/turn，作为首版明确限制。build 只包含己方 town、普通 building、即时 `ALLOWED` 的去重 `(town_id, building_id)`；复用现有有限优先级集合及其合法前置建筑，但不按优先级替模型选一个。首版排除 Grail、SPECIAL/AUTO 请求等特殊路径；没有合法 build 就不生成。
3. 选择 build：发送一次真实 BuildStructure，等待实际 ACK 和状态证据后关闭本轮建造窗口。选择 move：执行这次真实移动，并关闭本轮建造窗口。选择 end_turn：仍是真正的 EndTurn。没有额外“跳过经济”虚拟动作、假移动或假 ACK。
4. 窗口关闭后才恢复原有脚本招募/转兵/必要救援 hire，**删除该模式中脚本自动建造的回退**。后续移动决策不再提供 build。本轮预算与窗口在 own-turn 真正启动时初始化，保留 capsule03 的晚 EndTurn ACK、query/termination 屏障。零英雄的救援 hire 保持脚本性质，不伪造 count=1 样本。
5. 将当前移动候选构造与最终动作 dispatch 做最小分离：候选添加 build 后，不能落入“非 end_turn 必为 move”的索引/寻路分支，也不能为 build 提前提交移动 goal。原移动承诺过滤保留；经济候选不应被移动目标过滤误删。

这是有意改变花费顺序的研究协议：否则旧脚本先花光资源，build 候选会消失。比较中的固定脚本控制臂也必须采用相同窗口和花费顺序，不能声称与旧 native 行为完全相同。

## 观察与模型的必要最小扩展

新 request 加实际七种资源、own town ID/faction/已建建筑及本轮建造状态；build candidate 带实际 town_id、building_id、七资源成本与可解释建筑类别（收入/基础兵营/前置）。使用 `town->getBuildingCost()`，不得猜价格；类别来自配置，不来自未来或敌方隐藏信息。ID 用于请求绑定，不能把任意 ID 当作连续数值战略特征。move/end_turn 保留现有事实输入；build 不伪造目的坐标或路径。无需先加入招募库存、物流或多英雄调度。

新 encoder/model 明确三种 op；movement prior 只作用 move，stop bias 只作用 end_turn。以已有权重按命名特征列显式迁移，新增列初始化单独记录，reset Adam/rollout/RNG 并声明新 epoch；不能 strict-load 旧维度后冒称连续训练。CPU 验证在 build 被屏蔽时原动作相对 logits/critic 保持映射预期。训练前记录 build 概率、候选出现率和 movement prior 大小：新候选概率近零时先处理预注册初始化，不能靠盲目多跑更新，更不能用 DEV 结果反复调初始化。

## 真实执行与审核接入

WSL `lib/callback/CCallback.cpp:222`–`:232`：`buildBuilding()` 校验 owner/ALLOWED，发送 `BuildStructure(townID, buildingID)`；返回 true 仅表示发送，不表示服务器执行。实际 payload 定义在 `lib/networkPacks/PacksForServer.h:253`，服务器 `server/NetPacksServer.cpp:143` 验证 owner/active player 后调用 `gh.buildStructure()`。

WSL `server/CGameHandler.cpp:2358` 起实际建造；`:2482`–`:2496` 按 requested building 的完整资源成本扣费，并 `sendAndApply(NewStructures)`。`:2453`–`:2475` 可能连带加入自动建筑，所以审核要求 requested building 已建并核对真实集合，不能错误要求只有一个新增 ID。`:2403` 起兵营还会更新库存，`:2499` 后可能授予法术、开雾、触发访问和胜负检查，不能收到一个建筑回调就提前开始下一策略动作。

客户端 `client/NetPacksClient.cpp:164`、`:602`、`:628` 分别转发资源、buildChanged、库存变化；这些回调自身没有 native request ID，不能单独冒充 ACK。新 policy build 必须进入原来 policy 的唯一 immutable pending tuple：decision/request SHA、实际 player、真实 hero context、own_turn、op、town/building 与 request ID。`requestSent` 核对真实 pack 类型/完整 payload 并绑定 ID；不能同时被旧 pendingEconomy 消费。capsule03 的 `candidate/client/Client.cpp:522` 起 Director 注册逻辑和 `candidate/client/NetPacksClient.cpp:993` 起真实 requestRealized/统一 ACK 日志次序保留：回调先于统一 ACK 打印，不能人为反转或制造第二次 ACK。

新 raw/auditor 分支须交叉核对：精确模型候选与 response → 实际 `BuildStructure` send(id/player/tid/bid) → 对应服务器执行/成功 apply → 实际资源和 requested building 前后事实 → 同一真实 ID 的成功 ACK；全程保留 query/battle/terminal 处理。ALLOWED 在发送前失效、发送失败、拒绝/缺失 ACK 或证据有歧义，均不得接纳为成功建造样本。统一选择窗口中没有其他并行花费，便于严格归因；有地图触发的额外资源变化需独立解释，否则该局不资格。

`strategic-policy-v3/audit_typed_execution.py:65` 起只承认 MoveHero/EndTurn；`strategic-typed-native-v1/raw_events_v4.py` 也不能直接证明新动作。下一 epoch 需要其最小新版本 build 分支，以及新候选绑定的 whole-game 审计配置；`strategic-director-terminal-drain-v4/audit_game_v6.py` 的原 capsule/source/epoch 绑定不得放宽。保留现有逐行 CUDA action/logprob/value/RNG 精确重放和全局终局 registry 门禁，只扩真实第三操作和 source bindings，不写另一套训练框架。

## 最小资格与比较

- CPU：三 op 严格编码；town/建筑/成本/owner 和 op 不匹配拒绝；无资源/已建/当日上限候选为空；选择 build 不调用移动、不提交移动 goal、不触发脚本重复建造；假/错/重复/晚 ACK 与 query 插入仍拒绝或正确排空。验证新参数可得到 build 样本梯度，不把自动招募计入 policy。
- root 后续单独执行少量 native 机制资格：一次真正选 build 并扣费/新增建筑；一次有 build 却选 move；一次无合法 build。要求精确 ID、服务器 apply、ACK、最终 whole-game 审计；这些机制局不算胜率。未取得此资格不采 PPO 批次。
- 资格后再冻结一次八完整 Training cells（既有 maps×roles×Empty/NK，全部同一初始化 parent）并作一次原 PPO 更新。保留原奖励/超参；初始化迁移与 AdamReset 另记 epoch，不混入效率 reward 实验。记录真实 policy-build 数量、候选/概率/选择率、花费及建筑结果；零 build 样本说明接入或探索不足，不是训练已学会经济。
- 在相同新 capsule、相同窗口与脚本招募顺序下，预注册固定优先级建造控制臂和学习建造臂；使用既有配对 DEV 16 局规格，报告终局胜负和天数，并列真实经济动作证据。若 shared actor 训练也改变移动，只能称联合策略结果，不能把胜率差全部归因经济。旧 T2 可作历史参照，不能替代同 capsule 对照；不动最终测试集，不据 DEV 反复改 reward。

交付界线：下一步最短实施链为 **native build candidate/dispatch → 新 schema/model 编码 → raw/audit build 证据 → 旧 collect/admit/PPO 的新 source/epoch 绑定**。先让一个经济动作确实可学习，再讨论招募数量或更广经济能力；本报告不申请也不启动这些后续运行。
