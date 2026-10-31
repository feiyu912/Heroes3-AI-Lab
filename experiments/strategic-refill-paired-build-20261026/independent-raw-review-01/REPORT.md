# 八局补兵机制原始证据独立复核

独立复核通过。直接读取8局原始request/action、selector、typed、client log、trace和终局drain，同时重新执行冻结8局/4对审计；没有读取旧AUDIT的passed标志代替复核。另以新代码独立重建每条request SHA、真实发送/ACK次序、移动坐标、兵力差值、两臂请求差异及源码/二进制对应。原始3952个文件的SHA列于RAW_SHA256.json。

| 既有原生局 | 决策 | 成功实际移动 | 招募ACK状态 | 免费转兵ACK |
|---|---:|---:|---:|---:|
| baseline-positive | 5 | 1 | 1 | 0 |
| baseline-empty | 4 | 1 | 0 | 0 |
| baseline-full-incompatible | 5 | 1 | 1 | 0 |
| baseline-full-merge | 5 | 1 | 1 | 0 |
| candidate-positive | 8 | 4 | 1 | 1 |
| candidate-empty | 4 | 1 | 0 | 0 |
| candidate-full-incompatible | 5 | 1 | 1 | 0 |
| candidate-full-merge | 8 | 4 | 1 | 1 |

合计44条实际决策：14次move、6次recruit、24次EndTurn；44个typed action ACK全部成功，另有2个真实free transfer ACK。八局均实际3个own turn、正常完成calendar game_over并通过原子registry drain。这些固定日历终局是诊断停止条件，**不能计作战略胜率**。

正例与满七槽可合并例：两臂首两条实际请求/响应完全一致。在第三条请求，除candidate恰好多出一个home kind4移动候选，其他字段及候选逐项相同；原commit排在首位且真实继续执行一次，没有被强制回城。candidate每局实际4次位移：29,8→28,9（离城），28,9→27,9（继续原kind5），27,9→28,9→29,8（两步kind4返城）；不是四步返城。每一步都有真实TryMoveHero成功结果、package ACK、下一request及callback trace的新坐标。

candidate-positive招募的creature0 amount1先进入town19，返城后what=2真实转到hero3，英雄creature0从20到21，creature2保持10，城镇军队清空。candidate-full-merge真实初始七槽，creature0从1到2，其余六物种各1，前后仍七槽；同样what=2。两笔转兵的gold/所有资源、招募库存、来源/目标双方总数守恒均核证；服务端应用log与侧录逐项一致。baseline对应两例都只提供原commit，没有转兵。

empty两臂首序列相同且完全没有招募/转兵。full-incompatible两臂均实际满七槽、招募species不在英雄army，首序列相同且没有新增refill候选或转兵。预注册六项deferred boundaries仍未构造/运行，不算覆盖。

完整source manifests比较只有AI/DirectorAI/CDirectorAI.cpp改变，值与原合同两臂SHA一致。两臂client相同SHA692fc134…01c235，server相同SHA9ebd3851…a51dc3；baseline libvcmi为880df6ab…193ad5，candidate为25de2bde…f1bb32。每局实际加载观测与对应capsule二进制SHA、路径、inode及thread-server证据由重跑冻结审计再次核验；完整SHA在AUDIT.json。

本复核使用原canonical GPU→pool两锁且已释放，没有新namespace、没有native/Torch/GPU调用、没有新游戏或Adam更新。能力结论限于本固定seed、四机制条件的原生候选保留与合法回城转兵成立；尚不代表策略学会补兵或胜率提高，不晋升模型，final test未触碰。
