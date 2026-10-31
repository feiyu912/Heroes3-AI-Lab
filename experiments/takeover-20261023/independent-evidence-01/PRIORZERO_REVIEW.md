# 单因素 prior0 分支：独立执行前审核

内部质量门禁通过。最终 SOURCE_FREEZE `6c882b314cd69b526644e4730691f4b3e7979780ff3b6f6efce96abb68cbe827` 所列26文件及独立 CPU 实测时源快照均逐字节一致；旧 freeze9919及全部旧冻结文件未变。没有改旧输入、源或证据。

实际 CPU 读取新初始化151014...和旧b9ede：所有 state tensor 中只有 actor.recruit_bias 不同，-4→0；架构 forward 与 PPO prepare_batch/objective_terms/ppo_update AST 完全相同，encoder 字节相同，catalog/227维架构相同。新旧初始化都明确833 weights-only、新Adam/RNG，migration seed同3900。17份真实机制请求重复 forward 逐位一致；没有使用DEV动作或标签选择新参数。

旧init/旧update被新codec实际拒绝，新init被旧strictcodec实际拒绝。旧control DEV明确固定旧b9ede/85c5并调用旧strict broker，新零先验调用新broker，未放宽codec。新TRAIN仅登记init02，保留的旧seed4100设计稿由runner固定SHA门禁排除。

新TRAIN、新DEV、旧controlDEV三条真实collector准备路径各冻结936项输入后，独立审核硬停在 owned_resources 之前。新TRAIN3900的采样Generator seed与旧实际cell00 PLAN精确相同；源码中的八TRAIN job/learner reset seed及采样seed推导与旧3900实验相同。旧新sourceclosure同时锁定。此次未拿锁、0 native、0GPU、0optimizer。

最终源码确认：仅新零先验分支运行8TRAIN和1次有限更新；旧-4两模型不重训。4200..4207的8个DEV map/role/opponent cell各有旧-4 init/update及新0 init/update四臂，总32唯一原生局。相同native/catalog/架构/奖励/LR/PPO保持不变。该设计分别比较手工先验及该先验下学习效果，不能把prior0叫学得收益，也不能从尚未运行结果预告提升。

证书：PRIORZERO_CPU_AUDIT.json、PRIORZERO_FINAL_FREEZE_AUDIT.json。真实新采样、更新、CUDA恢复及32DEV独立重算仍须后续实际执行；CPU准备证书不替代这些边界。
