# 六家族真实训练复核与actor/critic梯度诊断

本轮实际4更新/384次Adam/1536个原生owned transitions、60个正常终局46胜零cut成立；24个family×role×opponent格各出现一次。四checkpoint逐SHA和完整来源通过，CPU真实恢复Adam，最后各参数step为382..383（global hook为384）；非last冻结参数无变化，攻守last graph和policy head确有变化。CPU读回不等于原生环境恢复，未作GPU诊断或新游戏。

12并发由真实rollout的12配置/状态、两组各12个独立已初始化worker目录和冻结VectorEnv等待全部worker再推理/批量发动作的实现共同支持；训练后没有live PID快照，child启动stdout被原worker抑制，不伪称直接数过运行时12个PID。记录最低MemAvailable8279MiB，模型GPU峰值334.2MiB；源码完成了phase前4GiB、逐worker2.5GiB、swap<256MiB门禁，但没有完整历史swap曲线。

亲自从四个raw rollout逐worker重建live_steps，phase切换11个已行动未终局fragment（另1个零步新局），最终预算停止10个fragment（另2个零步局），与实际phase_close_events逐JSON相等。这21个fragment没有额外reward/terminal/loss；已采样GAE的每轮末项与真实next_value bootstrap逐项相等。最后checkpoint早于最终close，checkpoint只带此前phase0关闭事件，最终报告另带最终关闭事件，时序一致。

64局原始结果JSON、日志shutdown、冻结工件SHA和终局合法性CPU重核：BattleAI14/16→14/16，作者11/16→11/16，逐对没有胜负翻转；作者平均永久损失95.125→96，BattleAI90.0625不变，不能晋升。13对观测轨迹摘要不同，不是“策略完全没变”。旧DEV仅存整局图摘要/类型计数，无法重建首次policy差异；本次不补跑或杜撰该证据。

## 预固定真实TRAIN梯度拆分

从首rollout的384个原始图/真实old values、next values、reward和done重算gamma1/GAEλ.95；优势严格按全384行标准化。冻结pre-update B64，固定四组索引0..7、96..103、192..199、288..295，分别autograd计算actor clipped surrogate−.005entropy与.5value MSE。没有optimizer、参数改变、GPU或native。以下仅32行/四批机制样本，不是全训练分布统计。

|索引起点|released last graph actor范数|critic范数（已×.5）|critic/actor|cosine|全参clip缩放|
|---|---:|---:|---:|---:|---:|
|0|4.468|1.428|.320|0|.09731|
|96|5.825|.754|.129|0|.08392|
|192|27.058|1.347|.0498|0|.01841|
|288|5.012|.252|.0503|0|.09707|

关键反证不是单纯cosine恰好正交：四批actor与critic共同非零的tensor数、非零坐标交集均为0。`full_graph_policy.py`将encoded Action送policy head、encoded Global送value head；`recovered-graph.py`最后层按关系目标节点分别累加并按节点类型归一化，先前层冻结。当前last模式的这组可训练参数聚合不能机械称为“同一共享主干”。完整JSON的shared_last_graph字段只是历史聚合名称，已明确不预设权重真正共享；all模式不在本诊断范围。

全参数actor范数4.51/5.83/27.11/5.14，也大于critic2.47/1.24/1.68/.362。原globalclip0.5确实缩放双方，但不支持“critic主导共享层，把actor压弱”的假设；不应据此降低critic权重或改共享层。global clipping是共同缩放，Adam坐标预条件和动量又会改变实际步长，不能将缩放数直接解释成actor学习弱多少倍。该假设分支到此停止。

## 下一方法边界

本轮六家族已补齐，但每家族仍只有一幅TRAIN固定case，合计仅6/192张TRAIN图，且两phase重复同图换对手；不能将60个终局误当60个独立地图。下一研究重点应是TRAIN内每家族的兵量、slot/deployment变化：预先无放回分层抽取多个case，明确地图覆盖、每case transition预算、phase丢弃量和实际终局分布；保持角色/对手覆盖，系数与超参不从DEV败局拟合。扩大case覆盖与预算若同时改变应如实称组合实验，并有固定预算原课程对照。不要直接重跑同六图、追加轮数或以这批DEV选训练case。本次仅提出下一假设，不自行准备/启动新训练。

AUDIT.json为当前独立实际证据，GRADIENT_DIAGNOSTIC.json为四预固定batch全部梯度分组/支持交集/clip值，分别绑定当前脚本与raw SHA。全部CPU检查已退出，0新增游戏/0GPU/0optimizer。
