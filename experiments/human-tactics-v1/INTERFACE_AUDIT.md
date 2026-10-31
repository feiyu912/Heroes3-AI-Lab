# Human Tactics v1：编码前接口与规则审计

审计对象为实际运行的 gym 11241d496db95541766498373e23245a67847a97 / engine e956242503f465ae6ec0a62a3aeb2c4ea179db5c。独立目录开发，不修改 research 正式训练参数、动作协议或原生库。

| 能力 | 实际证据 | 支持程度与边界 |
|---|---|---|
| 合法动作 | schema/v15/graph.h、envs/v15/vcmi_env.py | WAIT、DEFEND、MOVE、AMOVE、SHOOT；只能选 active_action_ids，不能自创拒绝反击、施法或战前拆兵动作 |
| 龙喷吐 | state_v15.cpp:1852–1872；CBattleInfoCallback.cpp:1937 | 每个合法 AMOVE 的主目标与附带目标均有 IsMeleedBy 边；原生 TWO_HEX_ATTACK_BREATH 的后续格可伤友军，不可只计敌方目标 |
| 尸巫范围 | state_v15.cpp:1912–1948；config/spells/ability.json:300 | IsShotBy 包含 SPELL_LIKE_ATTACK 附带目标；死亡之云范围0–1，排除非生命、机械、攻城、亡灵、石像鬼。主目标物理射击仍须另计；不能把所有相邻单位一概当可伤目标 |
| 自动反击 | lib/battle/CUnitState.cpp:491 | alive && counterAttacks.canUse；没有主动拒绝反击动作。图未直接给出反击次数，持久单位ID/数量也未直接编码；只有相对价值、攻击伤害估计、行动顺序关系等。不能仅靠图状态差认证骗反击成功 |
| 行动顺序 | Unit_ActsBefore_Unit.TIMES；WAIT合法动作 | 可执行/观测；等待本身不是战术成功标签 |
| 位置与方向 | Unit_Occupies_Hex、Action_EndsAt_Hex、Hex坐标 | 合法落点包含双格朝向约束；不是任意指定初始坐标/方向的接口。先随机化军队槽位、阵型与攻守，不能宣称任意布局已实现 |
| 障碍/阵型/英雄 | VcmiEnv参数；server/ML/ServerPlugin.cpp:1230 | random_obstacles、tight_formation_chance、random_primary_skills等存在；新实验独立设置，原普通战斗基准不变。必须逐项实测，不把参数存在当作完整场景支持 |
| 法术/大地图 | 五种动作类型与 mana=0 | 主动英雄魔法、大地图行动未接入；列后续缺口，不混入普通战斗 |

策略只使用玩家可见的图观测与原合法动作。引擎教师可用于示范和搜索对照，但其动作不是策略输入。单个学习器观测之间包含对方行动，不能把全部状态变化归因于己方动作。

代码核对与运行检查分别记录。规则参考：[VCMI bonus说明](https://vcmi.eu/modders/Bonus/Bonus_Types/)、[作者v15说明](https://smanolloff.github.io/projects/vcmi-gym/)。本地固定版本源码优先于网站最新版本；不是HotA全部规则的认证。
