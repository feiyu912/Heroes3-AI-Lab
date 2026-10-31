# Recruitment policy 草稿，未冻结、不可训练

此目录仅含 schema6 encoder/model 与 CPU 检查，不含 runner、admit、PPO、模型保存或原生执行入口。原 schema5 encoder/model/loader 未修改。

基线固定为 `83319be8bde5d94eea839b1a889821449a7c1492c65da7ca6cde2deb63aab25a` weights-only。新架构保留原 35 个 state 特征、前 43 个 candidate 特征和原网络参数；新特征使用独立零权重 residual。招募为独立第 4 个 op，含数量、库存/资源上限比例、quantity bucket、实际 upper army 目的角色/槽位、原生 stock level 类别（超范围 UNK）、实际己方军队摘要、物种类别。总成本及成本/现有资源比例复用原成本列。town/hero/creature ID 不作为连续 ordinal 输入。

新增 `recruit_bias=-4` 是保守手工初始化，未经训练或收益校准，不是专家标签，不覆盖策略选择。无 recruit 候选时，旧动作 logits/critic/softmax 的迁移目标是完全相等；新增 recruit 候选后总概率分布会变化，不承诺等价。军队摘要描述真实 upper army 和实际 visitor；visitor 可属盟友，不假装都是可转兵对象。该草稿不学习免费转兵或多英雄 actor 调度。

`load_catalog(path, expected_sha256)` 严格读取已绑定字节的 runtime CreatureID→canonical key 表，以独立类别列加 UNK 编码。此函数不能认证 catalog 来源于哪个 capsule。当前没有真实认证 catalog；默认空词表仅为 CPU 草稿接口，不能冻结作实际训练。真实 catalog 须由 root 的 mechanism-only 原生资格采集并绑定 capsule/source/binaries/runtime 后另行接入。`require_training_catalog` 当前无条件拒绝，包括伪造的 passed 标记；不存在词表/模型相互依赖的资格入口。公开生物规则表不是隐藏敌情。

CPU 最终草稿证据在 `cpu-review-04/AUDIT.json`：4 条实际 TRAIN 旧观察附加明确人工 recruit_state，旧投影及输出逐位相等；人工 recruit 候选的新 bias/actor/critic 特征梯度非零，16 个负例拒绝。新增 town/stock/army 与合成 catalog 均不是原生机制证据。只创建空 Adam 以检查状态为零，没有 step、保存模型、GPU 或原生对局。第一次 CPU 检查的动态 import 选择错误已修正，保留 `cpu-review-01` 空目录；02 首次通过，03 增加 catalog 负例，04 绑定定稿草案契约后复核。

接口依据 `strategic-learned-recruitment-native-v1/CONTRACT_DRAFT.md`，草稿 SHA256 `c3f432419bea862bfa1dcce051bd896ddcb9a5520963e161d3a6a864906c4af7`：request v6，response v3，recruit 13 个 exact keys，recruit_state 8 个 exact keys，整 ownturn 经济窗口保持开启（Move 不关闭，End 关闭，保留原 movement cap128 边界）。response 仍是原 9 个 flat keys，仅 schema 升级；本目录没有 broker 或 response 执行代码。实际 source/catalog 资格尚未获得，此处不是最终训练协议冻结。
