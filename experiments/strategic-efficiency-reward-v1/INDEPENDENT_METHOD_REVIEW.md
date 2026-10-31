# 效率回报单因素独立方法复核

2026-10-20，仅CPU/只读方法审查；未运行原生、GPU或优化器。原mainline和冻结原生环境不改。

目前PLAN无方法阻断。T2初始模型d590在新完整8格上采样一次，给两个相同初始化但独立重置Adam/RNG的学习器各作一次更新，是匹配数据的单因素对照：两臂采样前策略相同，不是将已更新模型重新喂旧行为数据。完整八格均须先通过原生审核及原CUDA精确采样准入；任何无效格保留失败、零更新，不自动换seed搜索。

效率目标 R_win=1−.05*T/(T+75)、R_loss=−1：有限非负T上胜回报在(.95,1]，仍与负局充分分离；不奖励提早输局。旧TRAIN赢局elapsed为95、46、55、121，中位(55+95)/2=75，所以tau来源解释成立，但仍需实现逐原始证据绑定四局的实际day再认证，不能只接受文档的列表。epsilon固定未经搜索。该回报确实区别快慢胜，终局gamma=1/原+1无法表达的效率信号开始进入目标。

单局回报仍是稀疏全局信用：慢胜中的绕行与关键取胜步骤共享return，不能定位具体错步；actor优势标准化会重新缩放小的目标差异，不能由0.05的回报上界推断梯度变化必然很小。效率与胜率仍可能存在期望层面的取舍，不能仅凭任意胜回报高于任意负就称严格词典序胜率优先。学习结果必须先报告胜负，再看双方获胜的day；早输不是效率收益。

实现准入应将证据与学习目标分开：先原样load和验证sealed +1/−1 admission，再在新目录产生派生target/protocol。每个episode必须有唯一原生终局事件，首policy request.day与terminal native day均需当前raw SHA和strict proof绑定；T≥0且day一致，不能用末次策略day、自报elapsed、最终ownturn或request数替代。源proof、request/trace及镜像的缺失/篡改、无效/非完整/奖励或终局冲突，必须在任何梯度或优化器状态改变前拒绝。每行派生target相同且episode manifest与target一致，不可简单放宽旧±1 validator。旧admission和原始reward永不覆盖。

控制臂的新接口必须在同一真实或明确fixture batch上与原base实现一致：样本权重、actor/critic优势与统计、entropy/KL、scalar目标和各参数gradient均应检验；只比较最终scalar loss不足以说明新接口没改优化。PPO clipping、critic、episode平衡、四epoch/64minibatch/shuffle、global seed与initial state保持一致；若KL stop使实际步数不同如实报告，不能绕门禁强制相同。完成后检查两臂真实参数更新、checkpoint恢复与独立DEV，不能把training loss下降作为强度证据。

当前77%左右one-move候选瓶颈未变，该实验不解决经济、多英雄或缺少战略路线。DEV是已经用于失败分析的开发图，新seed只是新对局，不是未见地图或最终测试。不得使用DEV观测/标签回灌或据DEV拟合系数。当前固定后续DEV对照应全部列出有效性与胜负分母，保留NPC排序/隐藏世界因果限制。

本文件是方法初审，不是待实现代码或真实更新的通过证书。后续CPU实现审计必须另输出具体源码SHA、拒绝反例和真实终局绑定结果。
