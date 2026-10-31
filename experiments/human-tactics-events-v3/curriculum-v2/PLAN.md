# WAIT-bait v2：针对 v1 训练失败修正必要条件

v1 的 train16局净胜-1、主力平均少损0.125，WAIT覆盖4次但严格时序机制0，未运行dev/test。不能声称已有收益。

v2 仍用相同2训练图与锁定的2dev/2test图；后两组尚未运行，没有重新命名已使用测试。固定原两个种子、双方角色、teacher 配对。代码/计划冻结后先跑 train16局。主判据沿用v1：主力配对损失下降且净胜不降，同时有可归因时序机制，再考虑dev；否则保留失败/等价，不动test，不生成BC。

唯一新必要条件：主力 WAIT 前必须在**可见图已有的非当前单位假设行动节点**中，找到某个低价值友军到同一个敌主目标的 AMOVE，且 Unit ActsBefore TIMES=1 证明友军本轮仍会行动。只发 active_action_ids 中的合法 WAIT，绝不执行非当前友军的假设动作。

原生 state_v15.cpp AddMoveActionEdges_Unit_BecomesMeleeThreatAfter_Action 也使用其它单位 Action_By_Unit 假设行动枚举并以 ActsBefore TIMES>1 排除本轮不可行对手。因此这里复用已公开图信息，没有新增速度、隐藏路径、未来状态接口。

保留 v1 的低价值合法近战选择和 counter-bait 候选；未实测候选不能称有效反制。反击历史只用公开已执行COUNTER，跨回合批次保持未知。
