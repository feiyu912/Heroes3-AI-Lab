# 原生 Ubuntu 接续结果（2026-10-25）

已在 Ubuntu 26.04.1 恢复可实际运行的独立战斗环境和完整学习器保存/恢复边界。
完整战略目标继续 active，尚未完成；本轮没有新增优化器更新或晋升模型。

新运行目录：`/home/kaicheng/Documents/Codex/2026-10-24/hello/outputs/Heroes3-Native-20261025`。
Python入口为其中 `runtime/python-heroes3.sh`；研究控制器仍须真实获取统一GPU→pool锁，
入口本身不授予资源租约。旧 `/root/...`、`/mnt/g/...` 字符串只按新epoch显式适配，
没有创建系统全局替代链接，也没有修改系统Python。

## 修复了迁移读取缺陷

本轮复现旧VHDX reader跨物理payload边界时未扣除块内偏移的错误。迁移自校验只证明
输出与同一个错误读取结果一致，不能代替研究冻结SHA。完整压缩备份重新校验后恢复临时
原磁盘字节，两套独立payload读取实现再分别核验内容；两者仍共用extfs metadata parser，
这一限制明确保留。

| 实际核验 | 结果 |
|---|---|
| 关键程序、模型21项 | 全部符合原冻结SHA |
| 主lab/events普通文件27,109份 | 全部核验，571份迁出错误另存正确副本 |
| 保留链接712条、运行依赖17库 | 原源核验通过 |
| 历史1,356,304条目，含1,141,112普通文件/硬链接 | 双reader及路径/inode核验通过 |
| 5,038项已有历史冻结SHA | 全部精确匹配 |
| 历史1,385项迁移错误 | 正确字节4,819,717,718，新delta417,549,538字节，逐成员回读通过 |

历史读取须按 `evidence-review/history-review-01/CORRECTED_MANIFEST.jsonl` 叠加新delta，
其余内容才从原归档读取。原错误迁出、旧归档、历史失败与冻结记录均保留，不重写旧证书。
完整说明：`evidence-review/RECOVERY_METHOD.md`。

本轮生成的临时196GiB磁盘在所有读取、修复及177MB工具链输入保存后清理，
实际释放209,994,121,216字节；原完整压缩备份、正确副本、新归档和证书保留。
清理证据：`migration-repair-source/CLEANUP.json`。

## 新Python环境与完整对局回归

旧恢复venv发现13包共49项内容SHA错误，另有未迁出的入口。已另建相同固定版本41包的
新环境，18,772个带哈希文件全部匹配，无缺失、内容、尺寸或RECORD结构错误。
证书：`python-integrity/PROFILE_CERTIFICATE.json`。这证明已安装RECORD覆盖的字节一致，
不把未哈希条目、外部wheel认证或整机ABI都视为已证明。

独立新profile复制27,116份源文件，输出普通文件27,148项逐项回读，使用独立inode，
保留所有旧目录。113条外部链接仍未解析；本次四格所需资源均通过冻结检查，
不能因此宣称任意旧脚本和全部外部路径都可直接使用。

固定control60、192号历史开发地图、seed2026128600，双方角色×BattleAI/公开作者MMAI
共四格，全部正常完整结束。19/18/38/27步，共102决策；完整轨迹、终局、动作类型和步数
均与旧环境相同。独立重新检查每步原生返回链并CPU重算全部102次完整网络决策，
logits/value/概率最大误差均为0。

证据：`battle-runtime-02/RESULT.json`、`battle-independent-01/AUDIT.json`。
这是四个重复历史格的技术迁移回归，不计入新独立胜率。首个入口漏加模块目录，
在启动游戏之前失败；`battle-runtime-01`及新v2派生记录保留，地图/种子/门限未变。

## 真实CUDA恢复、保存和读回

从原MC62完整边界（SHA5cd856…）实际恢复模型、命名Adam、累计7936计数与四类随机状态，
执行8个归档TRAIN图的真实CPU/CUDA推理。logits最大差7.2479e-5、value最大差3.5763e-7，
均通过原2e-4门。四类随机状态实际重复抽样精确，再恢复为原完整状态。

从live对象保存新roundtrip，读回后完整payload digest精确等于原模型，再次实际CPU/CUDA
恢复通过；原元数据与计数保持。新文件SHA可因序列化布局不同而不同，不能冒称文件字节相同。
0次optimizer.step、0新训练、0原生在途状态恢复。

证据：`learner-recovery-actual-01/RESULT.json`及`LEARNER_RECOVERY_CONTROLLER.json`。
全过程使用真实继承GPU→pool租约与inode校验，退出排空再释放，没有删除锁文件。
`learner-recovery-independent-01/AUDIT.json`已完成独立CPU审核：实际载入原与新模型，
全payload tree、194个命名Adam槽、元数据/计数/四RNG精确；独立CPU重算8TRAIN图与存档误差0。
它没有二次运行GPU，CUDA实际执行依据本轮冻结worker、controller与资源遥测。
最终 `final-protection/snapshot-01/AUDIT.json`在真实两锁下核验85项SHA全部通过，
包括active17原冻结文件与engine副本；锁原inode保留并释放，无本任务残留原生/GPU进程。
用户桌面nautilus的40MiB条目原样保留并明确区分，没有声称全机compute列表为空。

## 研究方向与剩余工作

干净新环境的TRAIN梯度复核仍确认actor/critic末层可训练参数支持集无交集；
不以“共享参数梯度冲突”为由盲加PCGrad。见`gradient-support/REPORT_CLEAN_ENV.md`。

战略16局8,793 TRAIN请求诊断发现：新招城内兵后，已承诺的探索目标可能过滤回城补兵选项。
成功Empty组也存在同类现象，尚非败局根因。已有脚本救援雇英雄与免费转兵均实际存在。
下一单因素草案保留原commit，同时保留真正合法、能接收库存的own-town补兵候选；
仅一份cpp改变，其余八份payload精确。当前source-ready，尚未CXX编译/原生资格/新PPO。
先机制对照，再固定TRAIN校准。用户目录独立工具链的177MB原源输入已经双reader保存，
实际编译工具运行、完整链接依赖及两臂隔离构建仍需资格。

旧研究结论保持：destination温度校准0/4，未进入PPO；战斗MC96 DEV是
BattleAI15/16→14/16、MMAI13/16→14/16，无净收益，不晋升。reference62与MC62来自
相同完整61恢复边界的两条128-Adam分支，不能相加；本轮恢复测试也没有新增Adam。

战略完整对局、补兵新候选机制、一般多英雄/城镇神经actor、战斗整合、稳定主动对手收益和
95%战斗目标仍未完成。新主机16/24训练worker并发尚未重新认证。final test保持封存。
