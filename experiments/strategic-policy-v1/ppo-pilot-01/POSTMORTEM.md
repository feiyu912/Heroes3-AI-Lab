# 首次试点未发生参数更新

保留原报告与源码快照。原 training.json 中 CUDA_training=true 是过早设置的状态字段：本次只完成了 CUDA 推理与采样，updates=[]，没有执行 PPO 反向更新，没有新训练权重。

前两局分别真实战胜 EmptyAI、输给 Nullkiller2。第三局在发展图对 EmptyAI 90 秒超时，拒绝作为胜负或训练样本；整个试点在首次更新前失败，已保存 update-0 初始化检查点。

排查实际接口确认：原生 yes/no 对话 1=yes、0=no，组件选择编号为 1..N。旧 DirectorAI 一律回 0，会取消访问/交战，出现重复回合而不解决目标。修复仅在隔离战略代码，后续用新输出目录验证，不修改本轮原始证据。

之后版本只在真正执行优化器更新后设置 CUDA_training=true，并区分 CUDA_inference。不能将本次初始化/前向计算说成已训练。
