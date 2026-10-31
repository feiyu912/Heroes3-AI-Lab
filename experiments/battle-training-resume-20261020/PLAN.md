# B64普通原生战斗有限PPO再训练，2026-10-20

起点B64/update64 SHA1e022707186a3c0dad7c671233b100930e870fff6c79cc703fb5b89dfb192936，只载权重、新Adam。旧graph B64/B128有攻守与对手取舍；conservative heads16/32未整体解决目标，mixed16无提升、mixed32退步（BattleAI172→164/192、作者114→109/192且有截断）。旧mixed包含弱脚本/未获整体收益认证的专家；本次绝不读这些标签、轨迹、专家地图或BC。不是旧mixed32复跑。

方法：继承已跑过的FullGraphPair(last)与原masked PPO，开放最后graph层和heads；body lr1e-6/head1e-5，gamma1、stepcost0、army potential0.5、entropy.005、2epoch、microbatch8、旧KLstop.02。不是新reference KL实验；与旧mixed相比是有限组合方法，无单因素归因。8worker×32rollout×4update=1024真实owned transitions预算；8worker每个对手各4、各攻守2。只普通diverse-curriculum train索引0..191，case从TRAIN固定seed2026102008随机选；同8环境持续4轮，允许跨rollout局片段，绝不把片段计作胜局。该小样本不宣称覆盖所有地图/兵种×角色。

对手为真实原生BattleAI与原作者公开CPU ONNX（MMAI_MODEL、固定lab-upstream-{role}.onnx），禁止MMAI_GPU/弱脚本/教师动作。冻结原生5文件、ONNX两文件、B64、全研究依赖及TRAIN/DEV地图SHA；运行前/每更新/完成后校验。GPU学习器唯一并取得.gpu-learner-lock和.pool-lock；root统一调用，本agent只做CPU准备。

保持确定性CUDA、严格2e-4/rtol0且按原rollout8批量重算，不放松旧概率门禁。真实optimizer post-step hook记录Adam步，更新前后记录参数delta并拒绝冻结层变化，每update原子保存model/Adam/CPU-CUDA-Python-Numpy RNG和来源SHA，CPU读回逐tensor核对。保存全量rollout原始图、动作/logprob/value/reward/done与worker配置。rollout文件含可信本次生成的NumPy pickle内容，仅作本地研究材料，不当外来安全格式。

这仅认证学习器更新边界与模型/优化器全状态载荷，不保存live原生环境；--resume明确拒绝，不能称原生边界恢复或连续vs切分完全等价。若失败，保留原log、已完成checkpoint/rollout并RESULT.failed，不伪造CUDA更新/胜负。

DEV固定普通192..199八图×攻守×BattleAI/原作者×B64/update4=64局，1新seed/格（2026102500+scenario_index*100），CPU argmax，预先固定最终update4而非挑最好轮。是已见DEV图的新seed配对，不是未见图/final confirmation；confirmation-v2完全不碰。报告逐对翻转、角色和对手分层、截断/非法/实际退出及损失，不夸小样本达95%。4轮完成后不自动追加更新或换seed。

运行入口run.py默认仅写PLAN/FREEZE；root审阅后--execute --evaluate才真实训练与配对。旧冻结环境、旧脚本与证据均不写。
