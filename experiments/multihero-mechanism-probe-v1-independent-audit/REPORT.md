# 真实双英雄会面与转兵机制验收

本报告为机制证明，不是完整对局成绩、专家示范或模型能力提升。3个探针均不产生PPO样本/更新；winner=null。当前训练环境仍为精确恢复的server-ready-V8。

## 直接证据

独立审核器 `audit_raw.py` 不导入原runner/audit gate，逐条核对原生日志中的发送编号、收包、真实应用成功，再与C++实际PackageApplied回调的同编号ACK和状态快照交叉验证。`native-01/AUDIT.json` passed=true。日志行号和5类原始文件SHA均保留。

- close-only：courier0真实移动两步访问receiver2，query5被服务端pop；QueryReply请求5成功，EndTurn请求6实际应用并ACK，兵力未变。受控停止，非终局。
- transfer-close：两个MoveHero请求3/4；ArrangeStacks请求5真实应用并ACK，再QueryReply6、EndTurn7成功。courier原10枪兵+3弓兵变3弓兵；receiver原5枪兵变15枪兵。双方总15枪兵+3弓兵完全守恒，双方均非空；位置、资源、城内兵力/建筑/可招募量未变。
- original-unhandled：query5真实建立，C++收到ExchangeDialog，未回复查询；未见query pop、转兵或EndTurn。20秒工程超时，仍有未答查询；这不是原生拒绝，也不计输局。原runner退出码1按失败对照保留，不改写为正常成功。

删除真实ArrangeStacks应用证据、破坏兵力守恒、改错ACK编号三项独立反例全部被拒。

## 构建与身份

三capsule来自同一已验收树的受锁增量构建，并非三个独立全量构建。源码全树清单只允许Director cpp/h改动；保留三份显式server battle-ready源码。实际游戏 `/proc` 证明加载了对应capsule的libvcmi（SHA/inode/device/path均一致），以及同client进程内runServer线程。不能仅用client可执行文件SHA判别版本：它在三个版本中都可保持相同，差异位于libvcmi。

构建结束后原Director源码恢复e198e32f…，重新编译后三文件恢复精确SHA：client b94162bb…、server bbe0de38…、libvcmi d7016313…，rebuild_required=false。冻结战斗五文件不曾用于构建/改写。

## 失败与验证器修正

capsules01/02均在源码清单预检停止，尚未编译；依次核明3个固定Data/Maps/Mods运行目录链接，以及唯一根目录悬挂ONNX模型链接（不参与编译、目标不存在、无虚构SHA），03才完成真实构建。未知链接仍拒绝。

close01/02均在初始化找不到CONFIG/FILESYSTEM时退出，未进入游戏。原因是EntryPoint.cpp:166主动切换至argv[0]父目录，而capsule没有完整开发运行目录。新runner用工作目录中的client符号链接启动，保持实际加载文件来自capsule，工作目录有完整config与Mods链接；没有改动capsule。

close03真实走通QueryReply与EndTurn，但验证器等了不存在的exchange QueryResolved回调并超时；且错误地将引擎会自动持久化的运行期settings/modSettings列成不变输入。保留该失败。已只读核查MapQueries.cpp、QueriesProcessor.cpp：此会面query服务端正常pop，无需该回调。修正版06要求真实query pop、QueryReply/EndTurn成功及同请求ACK，并保存初始config独立快照；capsule、源码、fixture和快照仍逐SHA不变。close04和transfer01在新判据下重新独立运行，通过；没有把旧超时改写成成功。

## 限制与后续

这是固定陆地、两个自有英雄、一组兼容兵种的受控机制验证。尚不证明跨回合运输、雇佣第二英雄、自动角色分工、城防保留、七槽拥挤/最后一兵规则的全面覆盖，也未将探针调度器并入训练Director。下一步需基于该原生机制实现正常会面处理和运输决策，并对真实完整战略对局独立验收。schema4 typed EndTurn原生候选仍未编译，不应混称已完成。

原始Linux目录保留。G盘副本见 `../multihero-mechanism-probe-v1/native-evidence-01/`，复制器只复制普通文件并逐SHA对照，运行资产链接只保留元数据、不展开复制。
