# 前缀重建与中途干预已实际通过

2场新游戏，同一旧训练图、角色和seed；step0..12共13个决策逐完整graph SHA/合法集核验一致。control沿原动作续跑，完整物理trace与旧参考一致；intervention在step12把原action168/native8近战换成合法action197/native6 WAIT，下一状态分叉，22步正常终局。

两局均输、伤亡均为2枪兵+12剑士；这里没有比teacher更强的结论。原生终局事件完整、无非法/截断，归档SHA与逐步前后状态保留。详见 PROBE_RESULTS.json。

这证明新进程前缀重放可以实施中途反事实干预，不证明具备snapshot API或公平在线MCTS。同seed会重现隐藏RNG，改动作改变后续RNG消耗，不能试出某实际未来最好的动作后称为公平teacher。当前0BC、0认证、0模型晋升；下一接口方案与成本见上级 SEARCH_INTERFACE_AUDIT.md。
