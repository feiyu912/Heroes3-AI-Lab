# 战略 PPO 独立只读复核（2026-10-18）

审计未启动游戏、GPU或optimizer step，未修改战略代码。实际做了CPU前向重算、checkpoint安全反序列化和原生轨迹对照。证据：`experiments/human-tactics-events-v3/STRATEGIC_PPO_READONLY_EVIDENCE.json`。

主要审计基准为失败run的不可变快照 `experiments/strategic-policy-v1/ppo-pilot-01/sources/train_ppo_pilot.py`，SHA `549f0c931882d2981113df2a76b2b8d23aedf8f8ef761504fd982cbc59dd7e5e`。工作树在复核期间正在修复：CPU证据取样时为 `20b9122b1355ed7481be154d467971c5d4bf66fea4385d12dfac0a6d7cfc9ec3`；随后只读看到了 `2d60303c6631ecd5b01dcd98eb3198194f16e2394fb24abc9d7388e8552e5976` 的双角色、ACK、SHA及resume修复。以下不会把旧缺口继续算作新版本已证实缺陷，也不把读到修复代码当作恢复训练实测通过。

## 实际状态，先纠正两个事实

当前失败report已有3局：EmptyAI胜/+1/558决策；Nullkiller2负/-1/36决策；另一训练图EmptyAI超时/7660决策。第三局valid=false、reward=null，没有把超时记作负局。updates为空，update-0.pt的training_updates=0、optimizer state为空。

CPU逐tensor比较update-0与prior-initial-v2，权重完全相同；weights_only=True加载整个checkpoint成功。因此旧report的CUDA_training=true是报告字段错误，实际只有CUDA inference，没有发生参数更新。应保留原failed报告并另附勘误，不能悄悄改历史结果。

## 通过的核心检查

1. **合法mask与旧logp对应正确。** collate按各请求候选数量padding；模型把非法logit设为-inf，Categorical仅在合法候选上采样。实际两有效局594条用update-0在CPU重算：最大logp差9.54e-7，value差7.45e-8；padding概率均为0。未发现旧logp来自错误状态、候选错位或mask泄漏。
2. **确实由本策略选择并交给native。** 558/558和36/36条采样与native strategy-decisions逐序匹配：选中index、player/day/hero/from及完整候选列表一致。这证明旧两局没有“仅写出动作但native另用默认策略”的实际错配；native记录是发移动前的选择意图，不等于每次移动都成功。
3. **奖励只来自有效原生终局。** runner检查进程退出、实际AI分配、原生结束标记、胜方、无崩溃超时、输入SHA和外部policy失败。collect仅对completed且有决策的局赋±1；invalid返回None并使整个update中止，未混入PPO，也未静默补损失/胜利。
4. **gamma=1的整局Monte Carlo return合法。** 每步return同为最终±1，advantages=return-old_value，跨批标准化后用标准clipped ratio目标；这里没有GAE/bootstrapping，也没有把相邻对局接成一条折扣轨迹。4局采齐前模型不更新，旧策略logp处于同一on-policy权重版本。不能把未使用GAE当实现bug。

## 旧版本实质缺口与新版本状态

### P1：旧版本每update角色与对手混淆

旧快照第171行在odd update把Director red全部给EmptyAI、blue全部给NK；even update再交换。虽总角色各2局，但每个对手没有双角色，有限批次中return可被player feature与对手强度混淆，不能拿这种训练成绩说明双方角色都学到了。工作树2d60303c已改成每update同一训练图、EmptyAI/NK各双角色，按update交替训练图；此项读到的修复合理，尚不等于训练/泛化通过。

### P1：旧版本冻结门禁不覆盖采样和更新期间

旧快照第215行只在update开头核SHA；采4局或梯度更新期间若改trainer/encoder/model，runner自己的runtime门禁并不覆盖全部Python训练输入，可能把不同版本的样本混在一次更新里。工作树2d60303c已增加collect后、optimizer update后复核；每局/更新前后均核验是正确方向，出现变更应丢弃本批并保存失败证据。

### P1：旧checkpoint保存了恢复材料，但原CLI没有恢复路径

旧save_model已保存optimizer、CPU/CUDA/Python RNG，但main总是加载initial并创建新optimizer，没有--resume/恢复RNG/下一job跳转，所以只能称“含恢复所需材料”，不能称“已验证可恢复训练”。新工作树已实现协议SHA、optimizer/RNG恢复和完整update边界续跑；尚未执行一次save→reload→下一更新的对照，不能先标恢复实测通过。全局游戏状态未保存在该checkpoint，恢复范围应始终是完整update边界重新开局，不是回到战斗中途。

### P2：参数变化指标不能区分策略与critic，也不是本次更新量

`changed_tensors`一直与初始化state比较，且包含critic与buffer。后续某次update即便actor完全没动，只要早先critic变过，仍会显示“有参数变化”。这不证明此次策略更新，更不证明行为改善。建议分别记录actor/critic的本update前后非零delta、梯度有限性及optimizer step数；已读到的新工作树此指标仍为累计值，勿据此称actor已学习。单候选或近确定分布尤其需要这一区分。

## 需要明确但不是算术错误的取舍

- **按transition采样不等于按episode等权。** 旧两个有效局分别558与36决策，若更新会让长EmptyAI局占更多样本。该采样是常见PPO目标，不应误报为return算错；若改按episode权重，会改变优化目标，应另冻结协议。至少必须按role×opponent报告局数、长度、胜负，不把594决策当594个独立结果。当前作者已声明将保留uniform transitions并披露长度，合理。
- **只有终局奖励、4局一批，信用分配噪声很大。** return同为+1也可能因初始value误差产生正负标准化advantage；这不是虚构终局回报，但actor变化可能主要是有限样本噪声。训练loss下降或Easy对手赢不能作为策略进步证据，仍需冻结参数的同图同seed开发对照与未见测试。
- **当前训练仅选择目标。** 经济、英雄调度候选生成、招募和战斗仍委托脚本/native；当前接口没有表示skip/end-turn等全战略动作。不能把目标选择actor-critic称完整大地图策略全部已学会。
- **checkpoint是权重与优化器恢复，不自动保证逐位复现。** 同协议/同代码、完整update边界、下一job seed、CPU/CUDA/Python RNG都要核对。native完整对局的确定性仍需实际对照。

## 新版本的小补强建议

这些来自当前代码阅读，未据此否定尚未运行的新pilot：

1. 给--resume文件本身记录并复核SHA，避免模型权重和随后第二次torch.load的optimizer材料来自被替换的不同文件；在新report中保留父checkpoint SHA。
2. 当前CUDA_training在ppo_update成功返回后才设true；若函数内部已做若干optimizer.step后抛错，仍可能留下false。真实步数应在每次step后递增并进入失败报告；训练是否发生与整个update是否完整另列字段。
3. --preflight与--resume并用时，当前恢复分支仍会调用torch.cuda.set_rng_state_all，即使device为CPU。应保持CPU预检不初始化CUDA，或明确拒绝该组合。
4. 保存checkpoint采用临时文件+原子替换，再记录SHA；新恢复路径至少做一次真实完整update边界续跑对照，明确不承诺恢复未完成的partial update。

复核结论：未发现当前PPO mask/logp/终局return存在制造胜率的直接错误；实际失败run确实零更新。主要风险是旧对手/角色混淆、旧冻结门禁与恢复路径缺口，以及今后把critic变化/长轨迹/训练结果误当策略提升。新工作树已修的部分应以新版本运行证据确认，不覆盖旧失败。
