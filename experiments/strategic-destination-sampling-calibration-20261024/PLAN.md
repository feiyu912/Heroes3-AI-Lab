# TRAIN内move条件采样温度校准（零PPO）

尚待根代理审查、封存和执行。本目录不创建SOURCE_FREEZE，不启动native/GPU/优化，不自动获取锁。

唯一因素：同initial1510149e、同schema6 capsule02，将多个原始move候选的条件温度改为T_move=.25。对M中候选使用 L'_m=L_m/T+logsumexp(L_M)-logsumexp(L_M/T)，非move原logits不变。0或1个move及T=1直接返回原tensor。保留所有destination/kind承诺，绝不把next相同但goal不同的动作合并。critic/value不变，实际每请求仍仅一次原私有CUDA generator的torch.multinomial。数学上每操作总mass保持；浮点硬门预登记float32 rtol3e-6/atol3e-7、float64 rtol3e-13/atol3e-14。失败保留，不通过事后放宽容差或重试纠正结果。

固定4格：矿图role0/1、seed2026104402/3；发展图role0/1、seed2026104406/7。对手均Nullkiller2，己方起始兵量×4，规范原TRAIN map名参与相同private sampling_seed/logical_update0。对照为已有原T1 CUDA随机四败，不重跑T1、不加seed/格，不更改模型/兵量/奖励/引擎。initial SHA `1510149ef1c2c896e3125e6468e9e58234a8bfc9e4278ad239f9d6840e1c62a1`。

本轮原始请求、effective oldlogprob/oldvalue、原始/变换logits及概率、原始/变换操作mass必须逐条保存，核验真实单次CUDA采样与完整generator状态。普通actor loss/PPO准入与专家标签永远拒绝本epoch；manual setting明确不是learning。未来若做PPO，须新分布codec并让同一变换用于采样和优化，不能用原T1 logp计算ratio。DEV保持原始argmax且不能把手工温度收益称为学习收益。

每局必须完整正常终局，原全门catalog/角色/库存/军队/真实request→ACK和资源守恒审计不放宽；本epoch固定4格完整性独立检查，不套用原PPO精确8格准入。不能借诊断身份跳过原生资格门。4格全部正常有效才汇总：>=2/4胜仅称“这四个固定TRAIN格暂可采得成功”，不是强度证书/泛化/因果胜率估计，也不自动启动PPO。低于2胜、非法、不完整、超时均保留；工程失败与正常失败分开，禁止追加seed追求阈值。

资源继承真实GPU锁→pool锁（非阻塞）、fd/inode校验、单实例collector与独立会话清理；前后RAM>2GiB、swap<256MiB。root先复核源码并封存，然后才执行；prepare/--prepare-only不申请锁、不起GPU/native。所有历史冻结包字节保持，finaltest封存。本次所有校准轨迹不准入PPO/专家。
