# 普通TRAIN 60图原生战斗PPO，2026-10-20预注册

前两次有限训练真实更新/保存通过，但没有独立DEV提升。最近课程仅每family一幅固定TRAIN图；梯度诊断也不支持critic压制actor，故本轮不改critic/loss、不重复原六图加轮。仅按普通TRAIN内容扩大预注册覆盖与预算，不能作单因素或广泛强度归因。

初始化为冻结B64/update64 SHA1e022707186a3c0dad7c671233b100930e870fff6c79cc703fb5b89dfb192936的权重，新Adam和全局seed2026102016。绝不继承最近较差/无收益候选。保持FullGraphPair(last)、body lr1e−6/head1e−5、gamma1、stepcost0、potential0.5、entropy.005、GAEλ.95、2epoch、microbatch8、targetKL.02和globalclip.5。

选择只用diverse-curriculum中192个TRAIN条目：按实际兵种集合划六家族，每家族固定seed无放回选10个case，共60张不同TRAIN地图。DEV结果、输局标签、旧专家、BC、专家地图与MMAI_GPU均不进入选择或更新。每case都对BattleAI/原作者公开CPU ONNX（MMAI_MODEL）并各攻守，共240个唯一case×role×opponent格。15phase，每phase同四个case供四个role/opponent组，各组4slot、共16worker；每phase2update，每update32rollout，共30update/15360真实owned transitions。家族内32个TRAIN case选10个，采样清单由curriculum.registered写入运行PLAN并冻结来源。

训练仅root统一串行调度，run.py持唯一GPU锁再pool锁。12并发已实测稳定后升16，不强上24；phase启动前MemAvailable>4GiB、swap<256MiB、磁盘余量>10GiB，逐worker staged余量>2.5GiB，更新后余量>2GiB及swap门禁保持。每phase资源读数另记phase_resource_events，不能用模型alloc冒充整GPU进程占用。CUDA确定性、旧logprob按真实采样16批量重算，atol2e−4/rtol0绝不放宽；最多约3840Adam，若KL提前停止则报告实际step。

每update记录真实post-step hook、actor heads/critic heads/last graph及双方role的参数delta，逐参数拒绝冻结层变化；原子保存模型/Adam/CPU-CUDA-Python-Numpy RNG、实际运行版本、来源SHA与该rollout SHA。CPU读回逐tensor校验model/Adam/RNG载荷和raw完整性。每次归档全量raw图/动作/logprob/value/reward/done/config；实际历史384样本rollout约96.2MB，512样本×30估约3.6GiB，加30个45.1MB checkpoint约1.3GiB，总约5GiB，按>10GiB磁盘门禁保守预留。运行中不压缩/删除/改输入；完成后如需压缩，另存原始SHA索引和可解压副本。

phase切换与最终停止逐worker记录已行动未终局fragment、零步新局；关闭事件是日志，不产生样本、reward、truncated、loss或额外终局。已采样GAE保留真实next_value bootstrap。最终checkpoint在最终close前，最终close只在最终报告；不伪称checkpoint已含未来shutdown。保存学习器状态不等于live原生环境状态，--resume明确拒绝，不承诺native中途恢复。

不进行中途DEV或选轮，只最终update30对B64做64局固定开发配对：原普通DEV192..199×双方role×两个真实native opponent×两模型，seedbase2026103400（实际seed=base+scenario_index×100），CPU argmax。confirmation-v2不碰，不重抽失败seed；无效/截断保留并拒绝评估资格。先报胜负与合法性，再报损失/轨迹摘要；已有DEV图新seed不是未见图确认。评估原入口只有整局public graph摘要/类型计数，不具备逐step首次policy差异证明；不冒充完整世界确定或人类技巧学习。

代码仅新sibling，旧v1/v2/family源码/环境/证据不动。run.py默认只写PLAN/FREEZE；root审后--execute --evaluate才产生native/GPU训练。任何失败保留真Adam步、日志和已保存checkpoint，不自动扩轮或换seed，不能把工程/梯度/训练胜负/独立能力混报。
