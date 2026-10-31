# committed move 与补兵候选的源级复核

状态：**source-ready，未 C++ 编译、未运行原生资格、未训练、无能力结论**。本目录只保存隔离候选，历史源码、冻结引擎、模型及旧证据均未修改。

审查基准是 `experiments/strategic-learned-recruitment-native-v3/candidate/AI/DirectorAI/CDirectorAI.cpp`，SHA `2d7180f8101d2f60e83d28b84b462e82cd6534b5ce85ac4e13a76c56b7b40eb2`。`DERIVATION_REPORT.json` 实际核验父 manifest 全部九份 payload，只有本目录的 cpp 有变化，其他八份逐字节相同。其 `passed` 只表示源文件推导及哈希检查成功。

父源码 239–243 行在 committed 过滤前已经生成 own-town `kind=4`：城镇归己方、`getUpperArmy()->stacksCount()>0` 后调用 `consider()`。`consider()` 约 167–189 行拒绝当前位置，调用真实 pathfinder，要求 `getPath()` 成功、有 next node 且 `nextNode.turns==0`。这是目标有真实路径、下一步本回合可走的既有门，**并不保证最终城镇本回合抵达**，也不能替代服务端实际执行资格。

父源码 273–310 行先寻找仍然存在的同 destination、同 kind committed 目标；在 threat-replan 未生效时，308 行 `candidates.assign(1, committed)` 删除全部其他移动目标。311–312 行随后才追加建造与招募候选，因此会出现“继续向旧目标走，同时可以远程招募；新库存存在，却没有同回合回城候选”的动作支持情况。TRAIN 轨迹研究证明大量请求符合这个形态，尚未证明被删除的城镇目标在每个具体时刻都满足真实路径和容量条件，也没有证明这是败局的唯一原因。

`stacksCount()>0` 不足以承诺能补兵。父源码 `issueFreeArmyTransferV6()` 1263–1284 行还要求上方军队及访问英雄归己方、军队不同、上方军队需要保留最后一队时至少两队、转移数量正且不超过 int 上限、`hero->getSlotFor(creature).validSlot()`。迁出引擎 `lib/mapObjects/army/CCreatureSet.cpp` 66–83 行证明 `getSlotFor` 先找同种可合并槽，再找空槽；七槽满并不必然不能补兵。同目录 `CGTownInstance.cpp` 的 `getUpperArmy()` 返回驻防英雄（存在时）或城镇本身，不能把上方军队一律当成空槽不受限的城镇。

新 cpp 在原 own-town 分支记录“已经由 `consider()` 加入，而且当前存在可转移库存”的目标位置。条件镜像上述与库存/容量有关的 native 门，并额外排除别的 visiting hero，避免增加英雄交换需求。仅在 schema6 的 commitment 压缩分支，保留原 committed Candidate 第一项，并从原 candidate 数组原序加入这些 `kind=4`。不为原来不可达的目标造候选，不更改分数、路径、库存、数量、动作编码或选择结果，不把同 next tile 的不同 destination/kind 合并。

没有新 commitment 或旧目标已失效时保留原自由候选行为；threat-replan 原分支不变；非 schema6 仍执行旧 `assign(1, committed)`。新实验固定 threat-replan off。原 committed 自己是补兵候选时，只留一份同 destination/kind，避免重复概率质量。补兵候选新增后也可以继续选旧目标或选 EndTurn，生产代码不会强制返城。仅这一项动作支持变化进入未来对照，不改奖励、PPO、初始化或人工先验。

当前 schema6 请求含 owned town 的 `recruit_state.upper_army` 七槽及访问英雄（若存在）的军队，但离城英雄只有 `own_army_value`，没有单独完整七槽。当前 `strategic-active-opponent-policy-v4/encoder.py` 对 move 沿用 legacy 特征：kind one-hot、坐标、路径、启发式分数、目标城镇驻军与英雄强度比例等；招募新增特征只填 recruit 行。故 native 槽位判断可以筛掉新增的不受支持补兵选项，**现有策略不能完整辨识离城英雄的物种级接收容量**。本草案不同时扩展观测或网络；若未来研究该表示缺口，应另立因素。

候选存在只表示“此刻库存/容量满足已镜像的 native 条件，路径能提供当前一步”。远程途中库存、所有权或容量可以变化，每次请求会重建候选和标记，最终转移仍由既有执行器及全状态守恒检查决定。未来资格必须核验真实候选、server request、ACK 和状态后验，不能只验源码或成功 ACK。
