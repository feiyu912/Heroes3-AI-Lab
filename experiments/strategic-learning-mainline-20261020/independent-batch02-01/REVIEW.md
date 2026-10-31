# 新完整TRAIN批次独立复核

独立CPU审核通过：8格原生只读审核重跑，其输出逐JSON与各原证书一致；原始输入链、准入输入/输出链、模型SHA、pipeline/native epoch、固定seed2200..2207及训练完整覆盖均一致。本次没有运行native、GPU或优化器。

2742个真实on-policy决策；训练成绩是4个EmptyAI胜、4个Nullkiller2负。它们是更新前T2采样行为的成绩，不能称更新后模型成绩，更不能称独立提升。旧batch01失败、6格准入但0更新的事实单独保留，未混入本批。

实际更新不只是程序跑通：完整checkpoint bb341762…803cc 保存1个完整更新、172个CUDA Adam步；CPU逐状态检查所有Adam步为172、stop偏置moment非零、actor/critic参数均真实变化。actor参数L2变化0.830989、critic为0.894603。检查原GPU恢复报告及其审核源码SHA：报告证明model/Adam/stopmoment和CPU/CUDA/Python RNG精确恢复、5项非法恢复拒绝。本次独立审核仅CPU读回上述实际序列化状态，没有冒称独立重跑GPU恢复；这仍不是native连续训练与切分恢复后完全等价的实验。

真实采样有743次非argmax选择（27.1%），其中173次主动结束回合全部发生在one-move状态；619个multi-move状态中570次非argmax但零次stop。2123/2742（77.4%）决策仍只有一个move加stop，缺少可选战略目的地的瓶颈依旧存在。所有173次stop时仍有移动力，所以确实消耗回合机会，但当前终局奖励不能单独判断这些等待是否值得。

独立CPU在2742个原训练观测上比较更新前后：13次argmax变化全部是multi-move的移动改选；one-move无argmax变化，前后argmax stop均为0。完整分布平均forward KL=0.000513799，与root报告一致。实际梯度使策略变化成立；训练状态上的概率/动作变化不是独立收益证据。没有T1同预算对照，后续即使DEV变好也不能归因于温度本身。

本目录AUDIT.json保存8格计数、逐格终局day、更新状态、原始链与独立输出SHA。独立配对DEV尚待完整审核；目前不作强度结论。
