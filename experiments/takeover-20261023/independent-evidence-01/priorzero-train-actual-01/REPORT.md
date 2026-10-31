# prior0 实际 TRAIN 独立审核

亲自 CPU 重跑全部8个完整原生 raw auditor，所有完整 AUDIT.json 与原始证书完全相等。8份sealed admission、实际raw/source/input/output、每条sample→proposal→native绑定通过；新epoch源和原生/cat身份一致。实际CUDA Generator动作/logp/value/初末RNG精确重放证书已读并核hash，本审核没有重复GPU执行。

进一步对全部3326个原始请求实际重算CPU完整神经网络及已选动作的logp/value，与保存CUDA值最大误差分别4.77e-7和3.58e-7。CPU与CUDA存在浮点差异，故不声称CPU按位重现CUDA采样Generator。实际源CPU重算与读取旧GPU证书两种证据分开记录。

| 同八TRAIN地图/角色/对手、seed3900、同PPO一次更新 | 原-4先验 | 新0先验 |
|---|---:|---:|
|完整episode采样行 |3952|3326|
|实际Adam steps |248|208|
|真实招募事务 / 兵量 |658 / 5311|795 / 4131|
|免费交兵 |70|66|
|EmptyAI胜 / NK胜 |4/4 / 0/4|4/4 / 0/4|

两条分支保留同算法/epochs/批大小的一次更新，episode长度随初始先验和轨迹变化，因此208与248不是相同优化步预算。事务变多而总招募兵量下降，也说明招募次数本身不能代替质量或取胜。

最终模型 `1d1618bf6dd535e1e7d158ed6d194848eeaba4e8260e9e1cb5467f0db27cc81c` 已实际CPU完整加载，Adam载荷/累计208计步一致。相对新0初始化，新recruit_actor L2变化0.0509022，recruit_critic0.0884023；recruit_bias0→-0.00778017，均有真实更新。root已另行实际CUDA恢复及12拒绝负例，独立审核只读该资格而不另起GPU。

本审核0 native/GPU/optimizer。前一轮未升级；本轮必须等待32唯一四臂配对DEV，分别判断手工先验变化和其下学习效果。所有NK TRAIN仍败，不宣称失败根因已证明，更不把DEV抄成教师。
