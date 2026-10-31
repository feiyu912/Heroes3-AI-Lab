# 普通TRAIN六家族分层原生PPO，2026-10-20

上次B64 lastgraph有限训练实际4更新/256Adam/1024transition完成，但固定8个TRAIN case只覆盖6家族中的3类，作者DEV11/16→10/16，不晋升。新实验从原B64 SHA1e022707186a3c0dad7c671233b100930e870fff6c79cc703fb5b89dfb192936重新载权重、新Adam，不继承较差131e7c候选。当前变更为覆盖与预算组合实验，不声称单一分层因素归因。

仅普通diverse-curriculum TRAIN192条：按实际兵种集合归为六家族，固定seed2026102012每家族选一幅TRAIN图，双方军队必须严格镜像；同图分别攻/守且对BattleAI及原作者公开CPU ONNX（MMAI_MODEL）各一次，共24格。没有读取/使用DEV输局选case、未认证专家/旧示范、BC或MMAI_GPU。实际课程由curriculum.registered确定并写入PLAN，两个phase同一六图，phase1交换各家族对手，随机重排slot但完整格集合严格一次覆盖。

12workers×32rollout×4updates=1536真实owned transitions；每phase12worker×2updates，然后关闭旧环境换另12格。各phase每对手攻/守各3worker；所有case共各4次角色/对手曝光，不宣称episode终局数会自动平衡。8→12先测资源，不强上24。启动phase前MemAvailable>4GiB、swap<256MiB；每worker沿用原staged boot>2.5GiB余量门禁，禁止为凑规模放宽。

其他学习机制保持上轮：FullGraphPair(last)、body lr1e−6/head1e−5、gamma1、stepcost0、potential0.5、entropy.005、2epoch、microbatch8、旧targetKL .02；CUDA deterministic，按原采样12批量重算，atol2e−4/rtol0不变。最多预计384Adam实际step，若KL停止则按实际记录。每update原子全状态保存、实际optimizer hook step、CPU model/Adam/RNG载荷读回与冻结层参数检查；live环境不提供恢复，不能宣称切分原生训练等价。

每步按实际terminated/truncated重置live_steps，phase切换与最后预算停止前记录unfinished_fragments及各slot已行动步数，零步auto-reset局另列；关闭没有新reward、不计terminal/truncated/loss。此前已采样32步GAE使用真实next_value作bootstrap，不抹掉或编造done。最终checkpoint发生在最后更新边界，最终close事件记在training报告；不能误以为该checkpoint包含尚未发生的shutdown。

保存全部实际rollout图、动作、logprob/value/reward/done/config，原生5文件/ONNX/B64/完整源码/地图SHA全冻结。唯一GPU与pool锁由run.py统一持有，root只在资源闲时执行；agent只CPU准备，不独自启动原生/GPU。旧v1/v2根目录/证据全保留。

固定update4与B64做64局DEV（192..199×双方role×两个native opponent×两个模型），新seed2026102600+scenario_index*100；CPU argmax，confirmation-v2不碰，不挑轮/挑seed。当前DEV runner仍只存整局public图摘要、动作类型计数与终局，没有逐step action/obs；不具备首次策略分叉归因资格，不能冒称能还原。开发报告保留胜率/损失/非法/截断/正常退出与数据分层，不能外推已稳胜作者或BattleAI95%。

默认run.py仅写PLAN/FREEZE，root审后--execute --evaluate才训练。失败保留真正Adam步与已保存checkpoint，源冻结后不热改。
