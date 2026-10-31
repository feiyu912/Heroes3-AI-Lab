# 接续动作（完整goal仍active）

先读本目录REPORT.md、新根交接与各实际证书，不重跑已完成迁移核验。
原盘临时文件已清理，正确输入和完整历史delta都保留；不要误判source.vhdx不存在为数据丢失。

1. 使用已合格profile：
   `/home/kaicheng/Documents/Codex/2026-10-24/hello/outputs/Heroes3-Native-20261025`。
   所有新控制器显式读取runtime/env.sh，统一HEROES3_RESOURCE_ROOT，两锁不另建namespace。
   旧硬编码run.py不能直接执行，旧source freeze/checkpoint元数据保持原字符串并按受控映射核SHA。
2. 保留learner-recovery-independent-01实际结果及最终保护snapshot-01；本轮0新Adam，
   MC62仍7936，不能与原其他分支相加。四格102决策是迁移回归，不计新独立胜率。
3. 工具链：toolchain-plan/PLAN.md和toolchain-inputs（4186文件/177MB+85链接metadata）。
   在用户目录新prefix建立所需链接并核验ELF闭包，GNU11.4/CMake3.31.10/Ninja实际运行资格；
   不写系统目录。现有source-ready清单不等于完整可运行工具链，缺项可先从原备份方案明确恢复，
   勿改旧依赖或假称已编译。优先用已核验的profile内CMake。
4. 战略候选：refill-candidate-draft是被冻结的source-ready草案，9payload仅cpp不同。
   新epoch为baseline/candidate各创建独立源码/构建/capsule；同工具链、flags、地图及随机设置，
   决不能修改active accepted源码、原冻结battle或旧cap。旧object/PCH的路径与ABI局限见工具链报告，
   不未经证明混用不明object。两个新构建要有完整来源manifest、源与bin SHA。
5. 依QUALIFICATION_PLAN做机制对照：真实commit远探索目标、离城后原生招募入镇库存、
   baseline过滤回城/候选保留原commit及合法refill；策略可继续旧目标一次后自由回城，
   到城后原免费转兵全军队/资源/库存守恒及真实ACK/排空均须过。负例包括满7槽不兼容、
   满槽同种可合并、空城、非己方、不可达、当前位置、重复目标。地图脚本不是专家或PPO。
6. 机制与新Ubuntu战略完整对局资格通过后，再登记固定TRAIN单因素随机校准，
   保持初始化151014、终局±1/gamma1、原PPO/LR/数据准入不变，仅候选覆盖改变。
   若仍无成功，诊断再换方法；不直接追加学习次数。校准轨迹不冒充专家或偷偷准入。
   后续新鲜有界PPO及未增强DEV仍须完整模型/Adam/四RNG恢复与独立原始/CPU评估。
7. 战斗：旧LR/终局延伸/MC对照均完成且无候选净收益；不要重做已完成预算或仅“继续多练”。
   TRAIN credit与near-tie排名诊断、头/body交叉证据和干净支持集复核都保留，
   不再以已被反证的critic共享参数冲突为依据，不把已50%采用MMAI当新课程。
   若另立方法，先固定单因素与预算、双角色/双对手独立评估；final test不动。

新主机并发训练资源尚未重新资格。默认训练16worker，24需实测；GPU学习器仅一个。
大型CPU分析只在GPU学习器退出后运行；本轮desktop nautilus40MiB已原样记录，不能杀用户桌面。
本轮没有新的dsh/MiniMax调用；历史实际会话证据仍按原索引使用，不能把内置子代理冒称MiniMax。
