# 原生 Ubuntu：TRAIN 梯度参数支持集核验

本次核验通过。actor 与 critic 的末层 body 梯度分别落在完全分开的参数张量，旧诊断中的零点积不是正负项抵消。现有证据不支持按“critic 与 actor 在共享参数上冲突”的假设使用梯度投影。

在原生 Ubuntu CPU 上，从已迁出归档恢复并核验的同一 theta61 检查点与 phase0 的 512 行真实 TRAIN 记录计算梯度。检查点 SHA 为 `4725dab0332ad93f3806084ce1fc01803e77f5e5ee6ca861d452b63892062840`；TRAIN batch SHA 为 `fd86a735a7e8597fd3329c999169dfb538cb484743b952bbced04f39751b0d16`。reference λ=.95 与 MC λ=1 各按 32 组连续 16 行分别计算，没有新优化器更新。

| 每个角色 | 张量数 |
|---|---:|
| 可训练末层 body | 81 |
| 源码拓扑中通向 Action 的 body | 66 |
| 源码拓扑中通向 Global 的 body | 15 |
| 全部 64 组 actor 非零张量的并集 | 60 |
| 全部 64 组 critic 非零张量的并集 | 15 |
| 两种梯度非零张量并集的交集 | 0 |

attacker 和 defender 均得到上述结果。每组的张量支持交集、标量元素支持交集及点积均严格为零，使用 `!= 0` 检查，没有人为阈值。逐组 actor 非零张量数为 51–60；critic 均为 15。六个 Action 路径的 softmax 温度参数在本批记录中始终零梯度，这不等于它们在所有可能状态下都不学习。

源码解释与数值结果一致：`full_graph_policy.py` 的 `last` 模式冻结前两层及节点编码器，actor 读取最后一层 `Action`，critic 读取最后一层 `Global`。`recovered-graph.py` 为每个关系及目标节点保留独立参数，最后一层没有后续跨节点消息传递。最后一层的 `Global→Action` 读取的是上一层已冻结的 Global 表示，因此不会把 critic 的末层 Global 参数接入 actor 梯度。

本次 CPU 对历史 CUDA behavior logp 的最大绝对误差为 **0.00005340576171875**，通过原诊断的 `<0.0002` 门限；不是位级相等。输入图网络源码 SHA 与检查点所记录冻结值相等。模型、CPU RNG 均未变化，所有参数 `.grad` 仍为 None；GPU 未初始化，原生新对局、优化器步数及 DEV 输入均为零。

完整逐参数名字、关系/目标节点、形状、非零次数、梯度范数及逐组结果见 `actual-01/AUDIT.json`；入口为 `diagnose.py`，补充源绑定见 `SOURCE_BINDING.json`。本次没有重算真实 shuffled PPO 更新的全过程，没有证明最终胜负原因。全局梯度范数裁剪仍可耦合两种损失的更新尺度，目标和优势值也可影响策略方向；本结果没有排除这些不同机制。
