# Episode 等权自由选择 PPO：新算法协议与 CPU 复核

本模块针对已测出的两个问题调整优化目标：77%左右移动只剩一个候选，直接actor梯度为0；按transition均匀目标使长EmptyAI局占更大比重。采用独立新协议 `strategic-episode-balanced-choice-ppo-v2`。没有修改冻结v1/v2算法，未启动游戏或GPU。

实现：`episode_balanced_ppo.py`，当前SHA `05477bfef29bb4b91c107b43a514c8284fa76e7817947f6f9e276354ed1bf088`。CPU证据：`episode-balanced-cpu-03/AUDIT.json`，含准确源码快照；最初的choice-ppo-v1（SHA `be4084fd073ec6a60b9b805b4cff43209d0f05e87dd7517a855870517376be65`）证据保留在02。首次CPU检查暴露总N变化引起float32优势方差的微小变化，已将优势moments改为与N无关的episode权重、double计算，保留首轮失败目录。

## 目标定义

设批量共N条转移、E个完整有效episode，局e有T_e步，其中C_e步候选数大于1：

- actor样本权重：自由选择时 `N/(E*C_e)`，单候选为0。
- critic样本权重：`N/(E*T_e)`。
- 使用均匀随机transition minibatch；乘上述全局权重后取该minibatch均值，不能在每个minibatch内部另归一化权重，后者会重新改变各局目标质量。
- clipped PPO actor目标仍为 `-min(ratio*adv, clip(ratio,.8,1.2)*adv)`。critic为0.5倍加权MSE，整体loss为actor＋0.5×critic－0.005×entropy，与旧value/entropy系数保持可比。
- advantage=`terminal_return-old_value`，gamma=1；只在自由选择上计算mean/variance，每个有自由选择的episode等权。单候选adv最终置0，既不进入actor，也不稀释优势moments。
- entropy和近似KL与actor使用同一自由选择权重。E仍包含无自由选择局，无选择局actor/entropy贡献0；不偷偷改成只对有选择局重新定义E。
- 同时报告objective尺度的KL和条件freechoice KL，后者除以有选择局占比。每epoch结束重算完整批量条件KL，>0.05结束后续epoch，避免forced-only minibatch掩盖自由选择上的策略偏移。

没有自由选择的完整批量也可训练critic；该批量actor目标、entropy和KL均为0。第二次复核发现旧v1模块即使直接actor梯度为0，已有Adam动量仍会移动actor，因此新v2协议在每个无自由选择minibatch的backward后将所有actor参数grad设为None，使Adam/AdamW跳过actor动量/weight decay和其state.step。critic继续更新，报告同时保留总optimizer step和actor/critic分组step，不能再假定每个参数step都相等。

## 门禁与真实步数

`ppo_update(model,optimizer,rows,device,progress=None,*,episodes=完整manifest,epochs=4,minibatch_size=64)` 要求完整collector manifest；验证episode_id唯一、与rows完全一致，valid、原生completed/inputs_unchanged、native消费与步数认证通过，终局return仅允许±1且同局一致。invalid/null超时、缺局或错动作在任何step之前拒绝；collector仍有责任原子认证整个同步batch，不能把失败局从manifest删掉后伪称完整。

参数变化按本次前后分别统计actor/critic。即使异常发生在Adam实际更新之后、step()尚未返回，也从Adam state记录真实步数；caller-owned progress保留completed=false/error/delta，供trainer保存不可resume partial证据。新协议的checkpoint/独占GPU/模拟池锁/边界恢复由parallel trainer负责，本模块不启动采样或设备。

## 已执行 CPU 验证

合成3局包含不等局长、不等自由选择数及一局完全forced：

1. 向某局复制17条forced transition，actor、entropy、KL目标不变，优势moments不变；完整actor梯度误差0。
2. 将某局全部转移重复10倍，episode等权critic目标不变，完整critic梯度最大误差2.79e-8。
3. 每局critic目标质量严格1/E；有选择局actor质量1/E、无选择局0，未把其余局放大成1/E_active。
4. 合成CPU PPO执行6个实际Adam step，actor/critic均有限变化；4种invalid门禁均0步拒绝。
5. 注入第3个Adam实际step之后异常，记录真实3步、完成回调2次，completed=false。
6. 全forced批量使用无历史动量的新Adam，actor参数完全不变、critic参数改变，避免将纯critic更新误称策略学习。
7. 使用真实非零actor历史动量（max abs=0.00746678）后再运行全forced：修复前6个actor tensor变化、L2=0.01617936、actor Adam step1→2；修复后actor参数、moments、step全部精确保留（step仍1），critic正常变化。独立前后探针证据为 `forced-momentum-before-fix-01/AUDIT.json`、`forced-momentum-after-fix-01/AUDIT.json`。旧实现未被用于本次真实游戏训练，修改前已与trainer owner确认无运行并重新冻结。

复制样本不变的结论针对完整优化目标和梯度；改变批量N会改变minibatch划分/实际更新次数，不能承诺随机optimizer完整轨迹逐位不变。原生向量训练、边界恢复和独立能力提升均尚未由本CPU检查认证。
