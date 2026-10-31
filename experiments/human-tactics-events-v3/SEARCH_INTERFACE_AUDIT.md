# 战斗反事实与选择性搜索接口实况（2026-10-18）

本次先只读核查源码/编译绑定，随后按主窗口授权仅新增2局真实前缀干预实验。没有启动编译、BC、PPO、CUDA学习器，也没有获得有效新专家。B64现文件实测SHA仍为 `1e022707186a3c0dad7c671233b100930e870fff6c79cc703fb5b89dfb192936`。

## 1. 现有接口，分别能做什么

| 层 | 实际能力 | 不能据此声称 |
|---|---|---|
| v15 Python env/编译connector | start、reset、connect、step、render、shutdown、getLogs | 没有clone/snapshot/save/load或每候选评分绑定 |
| 新进程+固定构造seed+动作前缀 | 真实重建到某个中途决策，再换一个合法动作完整续跑；本轮已实证 | 不是O(1)快照；不是独立未来采样；不能用已知实际seed做公平在线oracle |
| CGameState saveToMemory/loadFromMemory、普通save/load | 大地图状态与录制日志的内存/文件序列化 | 不保存正在进行的battle，不能直接用于战斗节点分叉 |
| BattleInfo::serialize | 原生战斗数据有序列化原语（单位、round、activeStack、障碍、城防等） | 没有接入gym的snapshot/restore协议；没有同时恢复server查询、客户端connector、模型状态和独立RNG |
| HypotheticBattle | 基于真实可见战斗callback的copy-on-write状态代理，可改单位、位置、等待、round/turn | 不是完整引擎step(BattleAction)，随机能力、伤害等有近似 |
| PotentialTargets、AttackPossibility、BattleExchangeEvaluator | C++公开候选攻击集合/状态结果、单次交换和有限轮次评分 | Python不可直接调用；不是所有合法MOVE/WAIT/DEFEND的统一真实反事实接口 |

实际导入 `connector_v15.ThreadConnector` 类而未实例化/启动游戏，public methods仅7个，详见 COMPILED_SEARCH_BINDING.json。不是只凭grep无命中判断。

## 2. 源码定位与重要限制

运行时基准均为 `/root/heroes3-ai-lab-events-v2/src/gym/`，旧源码只读。

- `vcmi_gym/connectors/v15/connector.cpp` pybind只注册上述7个方法；`envs/v15/pyconnector.py:114-134` 明确禁止同进程shutdown后再次启动，因引擎全局状态没有完整清理。每个分支使用新进程，不在运行着的C++/SDL线程上fork。
- `envs/v15/vcmi_env.py:474-477` 的 reset(seed=...) 只传给Gym的super.reset；native connector.reset没有seed参数。不能用它假装重新播种/回滚原生状态。`threadconnector.cpp:429` reset发的是ACTION_RESET而不是恢复某个中途快照。
- `vcmi/lib/gameState/CGameState.cpp:1779-1799` 有内存序列化，但1796明确注释 battles不在serialize中，随后清空currentBattles。`CGameState.h:213-237` 没有序列化currentBattles，`server/battles/BattleProcessor.h:98` serialize为空。普通大地图恢复成功不能替代战斗快照验收。
- 不能反向夸大为“VCMI根本不能序列化战斗”：`lib/battle/BattleInfo.h:52-72` 确有BattleInfo.serialize和postDeserialize。只是现有game snapshot流程不包含它，gym也未暴露完整恢复事务。
- `AI/BattleAI/StackWithBonuses.h:121` 的HypotheticBattle继承BattleProxy，`StackWithBonuses.cpp:271` 以稳定unit ID延迟复制单位状态；有moveUnit、nextTurn、nextRound、makeWait等。没有通用step(action)调用入口。
- 同文件 `RNGStub` 返回区间中点，`StackWithBonuses.cpp:449` 用伤害区间均值，`:515` 将随机能力简化成chance>=50。比如20%触发不是20%概率分支，而是始终不触发。此路径不偷看actual RNG，但不是无偏随机rollout或完全准确规则模拟。
- `AttackPossibility.h:60` 的evaluate返回attackerState、affectedUnits、主/反击/友伤等评分；`.cpp:325` 后显式处理反击、范围受击者与平均伤害。可用于构建更一致的联合短程估计，但必须验收特殊机制和行动次序，不能把它当真实引擎事件。
- `PotentialTargets.h:16` 有possibleAttacks；`BattleExchangeVariant.h:187` 有公开evaluateExchange。它们目前没有Python绑定，C++ public也不代表共享库中有稳定C ABI可供ctypes直接调用。`BattleEvaluator` 私有持有scoreEvaluator，没有现成scoreEveryGymAction方法。
- `server/battles/BattleActionProcessor.h:166` 真实makePlayerBattleAction/makeAutomaticBattleAction依赖BattleProcessor+CGameHandler，会改变真实server状态并发送事件；不能把一个HypotheticBattle指针替换进去就获得无副作用仿真。

horizon2/4/10只控制交换估计的模拟turn队列，不是minimax深度。horizon4实测更差已单独报告，不能继续把增大horizon当更强搜索。

## 3. 已真正执行的中途干预

`replay-branch-probe-v1/`：只使用旧训练图0、defender、seed2026101811，参考planner-pilot的horizon2归档；2局均从全新进程起跑。

1. 固定前缀对照：重放step0..12的13个决策，逐完整图SHA和完整合法动作集合相同；step12执行原动作，之后teacher2续跑。最终完整图/动作/native events/终局物理trace与旧参考完全一致。
2. 真正干预：再次重放同前缀至同一个step12可见状态和合法集合，把action168（native WALK_AND_ATTACK=8）替换成action197（WAIT=6）。下一观测真实分叉，22步完整原生终局；严格动作窗口及BATTLE_END均保存。没有把仅重放原轨迹算成反事实。

两局均输，伤亡同为2枪兵+12剑士，没有收益证明。`PROBE_RESULTS.json`绑定来源、对照、干预三个archive SHA与核验结果。两局记录的env运行wall约2.36/2.27秒；包括独立启动器的工具调用约3–5秒，随机器负载变化。

## 4. 公平性边界：为什么这还不是更强teacher

固定构造seed+相同前缀会重现真实对局隐藏RNG历史；换动作又会改变未来RNG消耗。若在部署决策时用同一个实际seed试完所有动作，再挑这条未来路径上最好动作，就间接使用了真实未来随机性。这里严格不做这种选优，不认证专家，也不产BC标签。

改成其它初始seed再重放同前缀，也不自动解决问题：战斗途中伤害/士气不同会使当前state不相同，不能当作“同一state的独立未来样本”。只有保存可见state后为模拟器分配独立未来RNG，或使用不读取实际RNG的可验证规则期望模型，才能支撑公平的当前状态规划。评估最终冻结策略时必须用未见场景/seed，而非同seed hindsight结果。

## 5. 下一可执行方法及最小成本

### A. 已具备，零编译：前缀反事实用于诊断

可针对B64/teacher已失败训练局的一个决策，重放前缀并改一个合法动作，检查“是否可能改变结局/代价”，同时定位阻挡、让先手、目标选择错误。这是研究诊断工具，不是部署时oracle。当前2局probe实际证明该路径可执行，扩一个候选通常需一整次新进程+前缀+续跑，当前小图约3–5秒；不能把估计当大图性能承诺。

先选1–2个训练state、最多3候选并包括原动作；诊断结果保持sample-path/counterfactual标签，0BC。不要先给452旧轨迹全量做数万分支。

### B. 推荐的最小部署规划实现：原生C++期望状态短程beam

新隔离adapter首先复用HypotheticBattle和AttackPossibility的单位状态结果，统一应用攻击、移动、等待/防御后的状态和队列，**实际比较动作次序**，而不是对主力/诱饵追加独立优先级。候选包含现teacher、B64 top-k合法动作、WAIT及少量不同攻击位；最多宽度3、两次行动窗口，包含对手最佳应对和下一己方行动。评价永久单位价值损失及剩余战斗价值，明确不是胜率。

第一版限制为无主动法术、无随机特殊触发的普通近战夹具；源state只能来自玩家可见的战斗callback及可公开重建历史，不读原生剩余反击次数等当前接口未声明的隐藏字段。实际候选必须通过当前合法集映射；模型/规划输出不读取actual seed。

需要新增隔离C++桥和绑定，当前并不存在。先在独立构建树做ninja dry-run确认影响范围，不能承诺只编1个文件，更不能重编冻结库。预计首先验收5–10个普通动作的一步影子变化与真实执行是否一致；再验收WAIT队列和有限反击。没有这些检查不启用beam结果。现teacher每决策约1ms只是成本参考，不能直接乘成新搜索的实测性能。

更强与否最后由新train/dev配对真实终局决定；shadow score高不等于Q3。与B64和teacher都比较，而非换随机弱对手。通过后先普通保留集再独立test，然后才考虑DAgger：只收真实合法/事件核验且teacher标签收益经过多变体验证的样本，保留普通策略锚点，避免再次局部BC损害普通能力。

### C. 长期准确分叉：BattleInfo snapshot + 独立模拟RNG + 真实动作resolver

BattleInfo.serialize可作为起点，但还需处理回调对象、server查询、待处理事件、阶段队列、模型状态和RNG独立性。不能直接沿用CGameState.saveToMemory；也不能将actual server RNG的状态暴露给策略。对原生动作处理器做无网络副作用的独立执行环境需要进一步工程，当前不宣称已完成或有可靠工期。

## 6. 当前交付状态

工程/搜索累计75场新真实游戏（73场既有接手实验+此2场probe），无有效新专家，原B64未变。旧v2所谓62条Q3的**认证资格撤销**，原数据/失败模型只读保留为探索性事后筛选；其余143条旧Q2不因旧标签名自动有效。修复后仍需逐动作重新核验，且末尾批次无法恢复。当前所有新数据BC资格为0，原锁定development/test未消耗。
