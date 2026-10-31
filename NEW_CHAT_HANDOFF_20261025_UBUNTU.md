# 原生 Ubuntu 接续索引（2026-10-25，持续工作中）

完整目标与用户授权继续有效，平台 goal 已恢复 active；完整目标尚未完成。
先保留并理解 `NEW_CHAT_HANDOFF_20261023.md` 的完整目标、原证据索引和保护约束，
再按本索引读取后续实际文件。不能使用旧 Windows/WSL 运行状态推断当前进程。

项目现位于 `/run/media/kaicheng/code/Heroes3-AI-Lab`，当前为原生 Ubuntu。
旧 WSL 已由迁移任务在用户授权、完整备份后删除。禁止再调用 `wsl`，
也不通过全局 `/root`、`/mnt/g` 链接伪装旧环境。新实验使用显式 Ubuntu profile。

## 先处理迁移完整性

入口：`experiments/ubuntu-native-takeover-20261025/PLAN.md`。

迁移归档自校验只证明输出与错误读取结果一致。本轮实际发现旧 VHDX reader
跨非连续payload边界没有扣除块内偏移，造成文件字节被错误相邻块替代。
完整压缩备份保持只读。临时恢复全部209,994,121,216原磁盘字节，SHA
`f90ad98ddbdc54aeb3d5856f6e5d6764fcfa76750e113624e40af1ede95886bc` 精确。

已用两套独立payload读实现重核并写入全新只读修复目录：

- 21项关键程序/模型全部符合原冻结SHA，含战斗server、战略server、control68。
- 17个运行依赖库全部符合原盘字节。
- 主lab+events的27,109普通文件全部双源核验，571旧迁出文件有误，已另存正确副本。
- 712保留symlink目标与原源一致。
- MC probe719原冻结输入完成718普通项+1 symlink目标严格核验；原719入口的非regular失败保留。
- MC DEV149个损坏迁出raw已恢复为原审计SHA。

证书和逐文件journal在 `evidence-review/reextract-*`，正确副本在 `verified-repair`。
旧错误迁出、旧错误归档和历史失败均未覆盖。完整历史归档现已全部通过：1,356,304条目、1,141,112普通文件/硬链接，
5,038项原冻结SHA精确，1,385项迁移错误另存417,549,538字节delta并逐成员回读验证。
证书 `evidence-review/history-review-01/AUDIT.json`；读取历史须按正确manifest叠加delta，
不能再单独使用错误旧归档。本轮还保留4,186文件/177,088,756字节工具链输入。
所有原源读取结束且确认无打开FD后，已清理本轮生成的临时196GiB磁盘，
磁盘空闲实增209,994,121,216字节；`migration-repair-source/CLEANUP.json`有完整证据。
原压缩备份、旧归档、新delta、修复副本及全部证书保留。

原迁移GPU venv的41包中13包共49项内容SHA不符；另有缺失入口，详见
`python-integrity/REPORT_OLD_VENV.md`。旧venv保留，不能继续当合格环境。
新41包同版本环境已经安装并独立RECORD全审通过，18,772个带哈希文件精确、0错误。
证书 `python-integrity/PROFILE_CERTIFICATE.json`。独立profile已经实际构造通过：
`/home/kaicheng/Documents/Codex/2026-10-24/hello/outputs/Heroes3-Native-20261025`。
完整本轮结果先读 `experiments/ubuntu-native-takeover-20261025/REPORT.md`。

## 当前研究结果与下一因素

战略学习/新种子复核与战斗终局延伸结果见
`experiments/takeover-20261023/INDEPENDENT_RESULTS_20261024.md`；该文件尚未涵盖以下新结果：

- destination T_move=.25保留操作概率的随机TRAIN校准0/4，未通过>=2/4门，未启动该PPO。
- 战斗MC probe：同完整61恢复边界先128实际Adam精确重现旧62，再重新恢复同61，
  另一分支128实际Adam生成MC62；两段不可相加为连续链。原96 DEV reference62与MC62
  BattleAI15/16→14/16、MMAI13/16→14/16，无净胜局收益，不晋升。
  reference62是旧candidate lambda .95 SHA ec26fe4b…，不是control68。
  MC62 SHA5cd856b3221342c283899df126f4c50116d7779b3e0ea3b8d90125e243310354。
  当前归档原始证据修复并不等于在Ubuntu重新执行了96局。
- `gradient-support`：在相同TRAIN图上，actor/critic可训练末层参数非零支持无交集，
  不支持以共享参数冲突为由盲加PCGrad。第一次使用旧受损venv的CPU审计保留；干净新环境actual-02已完整复现支持集，
  范数仅有3.11e-11末位差，未使用DEV或GPU进行该分析。
- `strategy-failure`：16局8,793 TRAIN请求中，有城内库存却仅保留旧commit目标的现象，
  在失败和成功组都存在，故不是已证实败局根因。已有脚本救援雇英雄和免费转兵均真实存在。
- `refill-candidate-draft`：仅在schema6保留旧committed move同时保留可接收兵力的合法
  own-town补兵候选。九份payload只有cpp改变，旧源未动；当前仅source-ready，
  尚未CXX编译/原生资格/训练。先做机制对照和固定TRAIN校准，不抄DEV当教师。

## 新主机资格仍需实际完成

新profile准备完成后，`qualify_battle.py` 使用固定control60、192号历史DEV格、
双方角色×两对手、seed2026128600做四格技术回归，保存每步实际graph/动作/原生返回。
比较完整旧轨迹，再由 `audit_battle.py` 独立逐决策CPU重放。这些重复格不能计入新独立胜率。
早期preflight因错误迁出server SHA被拒；battle-runtime-01又因模块目录缺失在原生启动前失败，
二者均保留。新v2的battle-runtime-02四格全部正常完整终局，102决策完整轨迹与旧环境精确，
battle-independent-01独立原生链及全部CPU NN重放通过，logits/value/prob误差0。

新环境已完成learner-recovery-actual-01真实CPU/CUDA恢复、live完整保存/读回、四RNG实际draw恢复，
完整payload digest与原MC62精确，原7936计数不变，0新optimizer.step；8TRAIN图CPU-CUDA最大logit
差7.2479e-5符合原2e-4门。controller正常0退出排空后放锁。独立CPU证书learner-recovery-independent-01已实际passed，完整payload逐项精确；
最终final-protection/snapshot-01持两锁核验85项SHA全过，原inode保留释放，无本任务残留原生/GPU进程。
战略完整对局、有限候选资格和下一PPO仍未完成。

所有profile共同资源锁目录固定在
`/home/kaicheng/Documents/Codex/2026-10-24/hello/outputs/WSL迁出-20261025/files/root/heroes3-ai-lab/evaluations`，
先 `.gpu-learner-lock` 后 `.pool-lock`、非阻塞、真实FD/inode继承、进程组排空再释放；不删锁。
单GPU学习器；新主机尚未重新认证16/24训练worker资源，四格串行CPU不等于并发资格。
完整目标未完成、模型未晋升、final test仍封存；历史目录内的live/paused/blocked只作历史信息。
