# 效率回报最终独立复核

最终源码与已有真实证据没有发现认证阻断。派生目标合法、两臂各有真实更新和完整保存，但本次对照没有观察到独立行为或能力收益。全程仅CPU只读；新脚本和输出仅在本子目录，未修改冻结源、TARGETS、原样本或原生输入。

## 目标与单因素闭合

亲自重跑 verify_targets：完整8局2111行的sealed admission、raw proof当前SHA、请求和typed镜像、原生server Turn/Info与client NewTurn、原生真实gameOver和全部policy day绑定通过。编译日历逻辑逐SHA与capsule manifest一致。最终TARGETS文件SHA为b5fc0fba…123ce9，源闭包要求精确完整集合，parent/arms/immutability与固定seed顺序均检查；训练入口按TARGETS canonical顺序加载两臂数据，不再依赖命令参数顺序。

四胜局首policy day均为1，原生终局day106/44/42/38，treatment目标分别0.9708333333/0.9817796610/0.9823275862/0.9834821429；四负保持−1。另亲自CPU重新认证旧TRAIN四胜原始证据，elapsed确为95/46/55/121，中位75，未取DEV拟合。缺source、假parent、假arms三个独立临时篡改反例均拒绝，真实文件未动。

亲自静态核对新旧objective_terms及ppo_update源码相同。原CPU_REPORT的当前完整源码SHA、TARGETS SHA、2111行/8局/13参数及15拒绝项核验通过；其中控制prepare、累积objective和全部参数梯度bitexact来自实现者已经实际运行的证书，本次没有重新跑完整反向。该证书不能泛称本次独立重跑了全部梯度。

## 更新与保存

亲自CPU读取两个实际checkpoint并核对完整边界、父模型d590、各132个CUDA Adam步、模型tensor SHA、reward arm及TARGETS绑定；除arm外protocol相同，保存的全局RNG及8局sampling states逐tensor相同。它们是两个各更新132步的独立模型，不是同一模型264步。

control为1cb4da8f…006f，treatment为daa2a4e0…ff15。两份原GPU恢复报告及对应auditor源码SHA通过，报告包含model/Adam/stopmoment/RNG精确恢复与5拒绝；本次没有运行GPU恢复。

亲自CPU在2111个真实TRAIN观测上复算两模型：argmax差异0，完整分布平均forward KL=1.8688294e−8。参数和概率有所变化，但其幅度尚未改变这批观测的确定性动作；不能据此称效率目标一般无效，结论只覆盖本次单更新和观测集。

## 全部DEV原始行为

16局亲自CPU重跑原严格v6审核，与原proof逐JSON一致；7364个proposal逐个用实际对应模型CPU argmax回放通过。固定seed2400..2407，4/8→4/8，8对全部胜负、移动数与自动结束回合数相同，主动结束回合0。每对完整request JSON序列、策略目标动作语义、实际所选from/next步骤序列均逐项相同，比较包含EOF，不只比较相同长度前缀。因此既无独立胜率收益，也无这些对局中的策略路径效率收益。

pair0..6的完整server movement投影顺序相同；pair7共3375条，首次差异第2324条为Krellion与Thane的NPC移动排序，完整movement多重集合仍完全相同、无增删残差。这只认证记录的移动投影和策略观测，不认证全部世界状态或RNG完全确定。

四对胜局双方trace终局day分别33/15/41/15，相同；其余均负，不将更早输局称作效率提升。本批与此前T2对照使用不同seed与不同模型，不能拿历史6/8和当前4/8横比断言强弱变化。

## 结论边界

工程准入、实际梯度更新、可恢复保存与合法派生回报已经有证据；当前固定DEV对照没有收益，不能继续将训练次数当作改进证据。此小幅稀疏回报只改变获胜局的episode目标，仍缺局部因果信用、战略候选覆盖和经济动作学习。后续方法必须另立单因素假设与新数据证据；不能回灌这批DEV标签或反复调整epsilon直到该DEV得分上升。

AUDIT.json记录本次亲自执行范围、逐对动作/移动比较和输入SHA；SUPPLEMENT.json记录tau原始证据及NPC移动多重集合。两脚本均为CPU只读，可单独复核。
