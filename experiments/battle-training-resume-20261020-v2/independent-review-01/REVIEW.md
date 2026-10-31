# 真实战斗再训练独立复核

本次实际训练/保存成立，但候选不晋升：BattleAI为15/16→15/16，原作者公开CPU ONNX为11/16→10/16。它们是固定小DEV，不足以证明稳定达到95%，也不支持继续沿update4盲目加轮。

亲自CPU读取4个实际checkpoint并恢复Adam，逐SHA核冻结来源/模型；四轮各64次真实optimizer hook步、总256步。参数因某minibatch只含一个role而有不同Adam计数，最终实际范围253..255，不冒称所有参数都是256。攻/守最后graph层均有75个tensor变化、policy head各8个变化；相对B64，攻方graph L2=.01986、policy=.03844，守方=.02459/.03445，其他冻结层逐参数不变。保存的CPU/CUDA/Python/Numpy RNG载荷存在，实际CPU读回model/Adam成立；本次没有独立GPU重放RNG，更没有恢复live原生环境。

1024个TRAIN原始图逐rollout按原8批量CPU重算归档采样logprob/value，误差最大9.16e−5/3.43e−6；原真实CUDA同批量重算记录是0，两者分开报告。335次采样非argmax，最终模型相对B64在这些TRAIN观测上11次argmax改变，不是“没有更新/没有探索”。四轮同批的更新前后argmax变化为2/4/0/1；这些是TRAIN已存图上的反事实模型比较，不是DEV实际首差。

独立从terminal shaped reward还原真实±1，40个正常训练终局、33胜、零cut；BattleAI攻11胜2负/守13胜1负，作者攻5胜2负/守4胜2负。环境槽位平衡，但终局速度造成BattleAI27局、作者13局，原transition-uniform目标也没有自动获得episode/家族平衡。训练地图固定8个，仅覆盖6普通编制家族中的0/1/3，2/4/5完全没有梯度数据。训练33/40不能外推普通全分布能力。

64局DEV逐个核对原JSON、日志末端真实JSON与VCMI正常shutdown、normal终局与实际winner、两公开ONNX身份及来源SHA；无非法、截断或非正常终局。唯一胜负翻转是作者/场景196/攻方：B64胜→候选负，owned action步31→41，永久单位损失52→62。作者另一攻方场景199同为胜但多损24，合计作者平均单位损失93→95.125。BattleAI平均损失88.4375完全相同。7对整局public graph轨迹摘要不同，其余25对摘要相同；摘要相同不认证动作ID、隐藏世界或RNG完全一致。

重要局限：冻结evaluate-policy.py没有逐step的public obs/selected action日志，只有整局观测摘要和action_type计数；因此现raw无法还原DEV首次policy分叉，也不能证明翻转由某一具体错误造成。本次没有新跑原生补证，更没有假装看懂视频。下个独立观测epoch应保存逐step actual action、legal IDs、完整图或其可恢复快照与hash，之后才能审因果。

下一方法只用TRAIN证据注册六家族×双方role×两个真实native opponent的24格课程，从B64新Adam重新起步，保持last/lr/目标；不从此次DEV败局直接构建课程、不挑seed、不继承较差update4。12workers分两phase、每phase两update是覆盖与样本预算组合实验，必须披露1536相对1024预算变化，不能把结果全部归因于分层。phase关闭的未终局环境单列fragment abandonment，不冒充loss；已采样GAE按真terminated/truncated与bootstrap计算。若后续仍回退，再据TRAIN局部损失/动作证据设计保留约束或信用分配，不机械堆轮。

详见AUDIT.json，含四checkpoint、所有64raw文件SHA、逐对翻转/损失、TRAIN分层与CPU回放。全部独立检查已退出，0新增native、0GPU、0优化器步骤。
