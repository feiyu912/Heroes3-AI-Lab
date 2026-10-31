# MiniMax 独立只读审核

实际模型：mini / MiniMax-M3.1-Flash；dsh session：session-8f6e4376-5c91-44fa-9087-a987f3256799。这是针对实施代理提供观察的独立方法审核；未读取/验证原生日志，不能代替独立原始证据审计。

1. **v2归因成立（仅据报告）**：hero0/hero2触发未处理exchange并超时，故工程失败；成功ACK只表示命令被接受/返回，不等于移动成功。“ACK成功但位置不变”应归为**控制臂未产生实际位移**，不能等同“调度过滤有效”。filtered臂排除hero3还需证明未对其发起move请求/ACK，或明确记录候选拒绝事件；仅无后续位置变化不足以识别。

2. **v3可作下一轮工程对照，但须补预注册识别门**：独立fixture/hash、源码/二进制哈希、随机种子、初始状态与预期转移表；预注册唯一筛选变量为`!hero->isGarrisoned()`，固定两臂其余输入；明确负例必须为“hero3被scheduler_selected且实际控制仍尝试move并ACK”，正例必须为“hero3在发令前被排除且无move请求”。记录selected identity、request id、ACK结果、前后坐标、每回合净位移、回合数、超时及未处理回调。

3. **结论必须限域**：v3即使通过，也只能声明在隔离fixture内满足了garrison候选过滤及位移等门；不得外推为完整多英雄战略、互动、exchange处理或训练通过。旧v2不可改写或追认passed。
