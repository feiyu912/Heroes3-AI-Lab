# Human Expert Learning支线：实物证据审计

日期：2026-10-16。对应聊天 `codex://threads/01a14038-9268-7ff0-989d-ce1cafe46b35`；本地工作树 `G:/Heroes3-AI-Lab-worktrees/human-expert-learning-v1`，实际HEAD为 `5e3a7152d3ea8d3cc4626f4802480c3e50ac1fbf`。

**审计结论：支线确有完整的小规模脚本BC与配对评测实物，但未证明能力提升。8组测试条件的胜率维持4/8，平均损失由87.875增加到93.125。其可靠轨迹记录、逐步回放和数组形状协议值得复用，权重不应因“课程已接入”而直接替代现有候选。**

本次只读读取原始报告、模型及代码，未启动游戏、GPU或训练，未修改工作树源码、主线源码或来源BC快照，未复制大数据。[机器审计结果](G:/Heroes3-AI-Lab/experiments/SIDEBRANCH_EVIDENCE_AUDIT.json) 保存逐局SHA、结算、样本数、模型归属及检查范围。

## 实物及模型归属

核对 [manifest.json](G:/Heroes3-AI-Lab-worktrees/human-expert-learning-v1/tools/human_expert/evidence/manifest.json)、[comparison.json](G:/Heroes3-AI-Lab-worktrees/human-expert-learning-v1/tools/human_expert/evidence/comparison.json)、[policy-freeze.json](G:/Heroes3-AI-Lab-worktrees/human-expert-learning-v1/tools/human_expert/evidence/policy-freeze.json)、[protocol.json](G:/Heroes3-AI-Lab-worktrees/human-expert-learning-v1/tools/human_expert/evidence/protocol.json)、[split-audit.json](G:/Heroes3-AI-Lab-worktrees/human-expert-learning-v1/tools/human_expert/evidence/split-audit.json) 与忽略目录runs/pilot-04中的真实文件。

- 21个完整episode报告、401条transition实际存在，全部原始文件SHA与manifest一致；其中4局训练示范、1局重复回放、16局前后模型测试。
- 21局均为正常终局，无截断；逐局胜负、阵营、永久单位损失和失败方全灭均与原始outcome一致，非仅信任汇总success。
- 所有before报告的实际权重SHA为 `1e022707186a3c0dad7c671233b100930e870fff6c79cc703fb5b89dfb192936`，与B64初始模型、protocol及freeze相符。
- 所有after报告的实际权重SHA为 `8a31f7aa8fc71bb65cd4cde4b8bd0fd67238596a97d82425b1a08d891ddf8b03`，与保存的script-bc.pt、训练报告、manifest及freeze相符。
- 只读CPU加载两份实际权重并比较：642个图编码/价值头张量逐位相同，16个策略头张量变化，角色metadata一致。
- 脚本BC使用4局训练报告中的63个样本、CPU执行40步；训练报告NLL为23.5181→16.1328。训练样本文件SHA已逐一核验；这不构成测试改善证据。
- 逐局frozen_artifacts合并45个不同实物，当前44个SHA仍完全匹配，覆盖模型、原生库、连接器、ONNX运行库、原作者对手模型、地图及相关脚本。唯一当前源码差异是audit_split.py的后处理修订；其原冻结版本在evidence/frozen-code中准确匹配。19份冻结源码全部核验通过，应按冻结快照解释实验，不能称当前所有源码与执行时完全相同。

freeze中`test_results_exist=false`及experiment.py的顺序支持“先冻结、后测试”的执行约定；这些本地文件不是独立外部时间认证。本次核验了实际使用权重及协议的一致性，没有凭该布尔值单独证明全部研究过程。

## 前后配对结果

测试条件为2张课程测试地图×2个攻守角色×BattleAI/MMAI_MODEL两个对手，共8个条件，前后各运行一次。这里的“独立测试”指本地训练集之外的既定条件，不代表8个独立场景家族或总体代表性。

|指标|训练前|训练后|
|---|---:|---:|
|正常终局|8/8|8/8|
|胜利|4/8|4/8|
|平均永久单位损失|87.875|93.125|
|截断|0|0|
|可认证战术成功率|null|null|

配对总损失增加42单位，即每条件平均增加5.25。一局对作者模型由负转胜、少损1单位，另一局由胜转负、多损42单位；另有一局多损1单位，其余无变化。总胜场不变，不能以某一局获胜或多目标动作数10→13宣称整体增强。损失指标按单位数量求和，没有换算成不同兵种的经济或AI价值。

精确观测SHA去重后，训练状态63个，测试状态237个，交集0；这些数值已从全部401条记录重新计算。它证明当前观察到的完整图没有精确重复，不能证明来源、机制或语义层面的普遍泛化；原作者预训练是否见过这些兵种仍未知。

## 逐步回放及协议可复用点

已有真实`replay.json`对应`train-0-attacker.json`，两者12步的前状态SHA、后状态SHA、合法动作、实际动作及最终outcome逐一相同。replay报告确实标记通过；冻结episode.py也包含逐步状态及最终结算检查。本次**离线核验已有真实回放证据，没有重新运行游戏**。

全部401条记录重新核对了record SHA、前后哈希链、步骤编号、合法动作、图SHA、相邻转移连续性，以及终局与链尾的绑定。压缩样本的压缩SHA、解压SHA均与manifest相符，解压内容逐字节对应原train-0-attacker报告。

可以在下一版隔离接口复用：

1. `array_layout`为每个node、edge index、edge attrs和action数组保存shape/dtype。尤其保留`[0,D]`、`[N,0]`和`[2,0]`，避免JSON空列表丢失形状；当前4条来源BC的运行代码及快照保持不动。
2. 记录`observation`、`legal_actions`、`executed_action`与`state_after`，而非只有最终胜负或预测动作。终局只在episode外层，不进入策略特征。
3. 明确`state_after_boundary`是“同一玩家下一次决策”，期间可能发生多次对手操作；不能当成原生引擎单事件前后帧。
4. 用record哈希链、完整公共图SHA及outcome_binding把动作、状态和终局联系起来；固定地图、对手、角色、种子和权重后重放。
5. 用`actor_origin`区分model/script/consenting_human，真人输入要求来源与同意ID。当前401条记录的human_action全部为null，实际真人动作数为0。

未来接入外部数据时仍需补充严格schema与身份/同意校验；哈希链只能证明文件内部一致，不能独自认证动作确为真人产生。数组布局还应检查字段白名单、dtype、关系数量及索引范围，不能无条件相信外部shape元数据。

## 限制及接入判断

所有记录的native_events均为null，战术成功率也保留null。关系图覆盖多个目标只是代理指标，没有提供龙息实际伤害、反击友伤或旧AI发呆的事件级证明。当前原始轨迹与脚本标签均不属于高手实录，也没有因为文件名human_expert而获得专家授权。

建议复用记录协议、形状恢复、固定条件回放与证据打包方式；保留脚本BC权重和本次负面结果供对照。接入主线应在新版本、隔离目录中进行，禁止修改已经冻结或正在运行的来源BC代码。是否采用新模型仍由冻结后的普通战斗、作者模型及专项正反测试决定，不能由训练NLL降低决定。

此审计没有复跑PPO smoke、保留能力实验或全部支线测试，也没有把这8个条件升级为大样本结论。21局及401条转移的证据可确认，95%以上BattleAI胜率、通用人类战术学习和有效反制能力仍未由该支线证明。
