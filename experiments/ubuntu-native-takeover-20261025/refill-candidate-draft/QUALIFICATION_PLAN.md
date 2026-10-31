# 单因素原生机制资格设计（尚未执行）

本计划是后续新隔离 capsule 的准入设计。当前没有编译或 native run；fixture、种子、capsule SHA、source manifest、选择器与独立审计器必须在启动前冻结。用户已授权研究实施，本目录 `build_allowed=false/native_run_allowed=false` 表示尚无经复核的本 epoch Ubuntu 构建/资格入口，不是再次向用户申请授权。

两组仅比较原 schema6 源与本目录补兵保留源。使用同一地图字节、同一 registered seed、同一运行资源、threat-replan off、同一确定性机制选择器；不加载神经模型、不做 PPO、不制造专家标签、不使用 DEV/final-test 地图。所有请求回应 `diagnostic_only`。默认单英雄、单 native 局顺序运行；取得真实 GPU 锁后再 pool 锁，继承 lease fd，退出前确认无 pending 请求/查询，再释放锁。

正例地图必须有一个己方英雄、一个可由真实陆路返回的己方城镇，初始上方军队为空，真实招募 offer 及资源足够；起点可以在城镇。必须真实观察一个仍需至少三步的 fog/frontier 目标，第一步离开城镇；若 loader/pathfinder 未产生这些条件，记覆盖失败，禁止静默改图或重播种。

1. 选择真实远目标并成功完成第一步，记录目标 destination/kind、真实坐标和 request/ACK。下一请求该目标仍应作为 committed move 存在。
2. 从离城后的真实 schema6 候选选择 Recruit amount1，记录 native offer/catalog、上方军队 ID、七资源和全 level 招募库存。真实应用后，城镇库存由空变正，英雄军队保持不变；整个过程仍在同 own-turn 内。
3. 在相同原生前缀之后的请求，基线应只提供原 committed move 作为移动项；候选应提供原 committed move 与该城镇 kind4。必须绑定全部原候选字段，证明原 commitment 未改变且没有额外非补兵移动项。独立审计不能仅从“库存存在”推测路径；新候选的真实 next、后续实际动作才是必要证据。
4. 候选组先选择原 committed move 一次并取得真实位移，证明补兵存在不会强制回城。该次后原目标还须合法，下一请求仍同时提供补兵选择；然后选择真实 town kind4，按其重新计算的实际步骤回城。不得伪造“已到城”或跳步传送。
5. 到城后等待既有免费转兵：真实 source/target army、slot、creature/count、server request ID、ACK 及状态后验全部绑定；库存减一、英雄同物种加一，其他物种、资源及 recruit stock 保持守恒。仅成功码不构成通过。若返城路上 stock/ownership 变化，不能沿用旧候选资格。
6. 到城后 kind4 不因零长度移动而重复出现；库存清空后不保留空城补兵。机制选择器后续仅选择合法 EndTurn 或预登记终局动作，直到实际终局及正常 drain。超时、pending ACK 截断、transport error 都是工程停止，不当败局、成功或可计分样本。

负例/边界使用各自事前冻结的单条件 fixture，同样须有可保留的合法 committed move；没有条件覆盖就不能声称该负例通过：

| 条件 | 必须观察的结果 |
|---|---|
| 城镇上方军队为空 | 不新增 kind4 commitment 例外 |
| 英雄七槽满，库存物种均不匹配 | 不新增例外；原 committed move 仍在 |
| 英雄七槽满，但库存与某槽同种 | 必须允许该真实补兵候选；回城后验证 merge，不把七槽满一律拒绝 |
| 库存正，但城镇由地形/障碍隔绝 | pathfinder 不生成补兵目标，不能绕过 `consider()` 强插候选 |
| 该城镇不是己方 | 不把敌方 town 动作标为 own-town refill 例外 |
| 英雄已在城镇 | 不新增零距离回城动作；已有免费转兵边界正常处理 |
| 原 committed 自身为 kind4，尚未抵达 | 相同 destination/kind 只出现一次，后续真实步骤不被取消 |
| 原 committed 不再 admissible | 使用原来的自由重选分支，不保留幽灵目标 |
| 非 schema6 legacy/build-only 模式 | commitment 压缩数组保持原行为，不引入补兵例外 |

source garrison-hero 保留最后一队及另一个 visiting hero 的条件应镜像执行器，已在草案中做保守检查；但当前 schema6 单英雄入口会先拒绝两个己方英雄，不能用不可能通过该入口的多英雄 fixture 声称这些条件已获运行资格。未来多英雄 actor 接入时必须另行覆盖。

独立审计还应拒绝缺失原 commit、新增重复目标、错误 owner、错误 slot/count、实际未移位、只 ACK 没有库存变化、七资源/非目标军队变化、提前停止、源或 capsule 变动，以及机制轨迹进入 PPO 数据集。既有 frozen hash/资源门保持原值，禁止为了通过而放宽。

只有工程资格成立后，才另行登记有限的战略训练比较。新的动作支持会改变行为分布，不能把旧 rollout 假装为新 native 的 on-policy 样本；不重标历史动作或 DEV 教师。即使资格通过，也只有机制结论，没有全局胜率或学会补兵的结论。
