# 正交换门禁：独立原始证据审计，不晋升

新候选的16局已由root串行执行。独立审核全部16份原始json.gz、340个真实动作，
候选3/8胜，teacher4/8胜；净胜差-1，永久主力/总体伤亡差各+4，预注册收益门槛失败。
本轮0训练/optimizer，专家与BC资格继续0。不要加种子筛掉失败或重称人类专家课程。

|场景/角色|1801胜差/主伤亡差|1802胜差/主伤亡差|候选改选次数|
|---|---|---|---:|
|fixture0/attacker|0 / 0|0 / 0|0|
|fixture0/defender|0 / 0|0 / 0|0|
|fixture1/attacker|0 / 0|0 / 0|0|
|fixture1/defender|-1 / +3|0 / +1|2|

AUDIT_01.json由本目录audit.py直接重算，不import新候选selector或其assess。
审核器自行解码公开graph的actor/primary/secondary/ordinary-melee/期望净值，
重实现>0与改进>1阈值，全部真实候选选择一致。全事件的target.killed按阵营合计，
与原生terminal永久总伤亡全部相等；同时检查normal winner/loser军队守恒。
每个真实请求窗口自行寻找唯一START/FINISH，核对actor/type和归档batch索引；
正常终局、archive SHA、冻结工件SHA、0非法/截断/BC均通过。

## 两个失败改选发生在精确相同前缀

两个改选都在fixture1/defender step11：baseline实际action211，候选记录的teacher
也为211，实际改为210。两arm从reset直到step11前的全部原生事件批次和实际动作
精确一致；包括step11在内的全部公开图也精确一致。其他6对无改选、前缀亦一致。
这支持首次分叉来自脚本选择，不能认证完整隐藏世界或RNG状态都一致。

重要修正：新失败中当前actor是我方**主力stableID5**，不是单兵！正净值把它
从攻击敌主力ID2改去杀单兵ID0。graph中原主力目标相对价值491，改选目标仅5。

|seed|teacher step11|candidate step11|candidate后续真实事件|
|---|---|---|---|
|2026111801|打主力ID2，122伤杀3；受108反击死3|打单兵ID0，9伤杀1，无反击|step12主力再打单兵ID1，10伤杀1；step13敌主力先普通攻击我主力139伤杀3|
|2026111802|打主力ID2，128伤杀3；受112反击死3|打单兵ID0，9伤杀1，无反击|step12主力再打单兵ID1，10伤杀1；step13敌主力先普通攻击我主力133伤杀3|

candidate step12没有再覆盖teacher，它是第一次覆盖后产生的真实后继状态中
teacher自己的新选择。所有事件与后续行动保存在TRACE_EFFECTS_01.json，不能将
该后继决策伪装成新脚本额外覆盖或此前具备的反事实知识。

这些证据反驳“只要求即时正交换就足以提高总体收益”的小机制假设。避开一次反击
却让主力连续花行动清理价值很低的单兵，延后对高威胁主力的压制，正是一步净值
未计入的机会成本/行动次序问题。后续随机数消费与占位也变化，不能仅凭这两局
把最终+4永久损失全部单因归给首次攻击，也不能称已证明通用最优修复。
不建议继续加阈值或挑守方旧有利种子；下一可review方向应统一比较主力压制、
行动次序与后续敌方回应，先做公开期望状态影子验证，再注册真实终局评价。

## launcher收尾缺口与结果有效性的区别

root实际执行launch.py --execute后，16个游戏进程均正常终局并生成PILOT_RESULTS。
父launcher自动导入audit_native时缺runtime PYTHONPATH，退出1；这是收尾审核入口
缺陷，不是native对局超时或虚构终局。root随后用正确runtime环境只读重跑同一冻结
audit_native，得到AUDIT.json；本目录再独立核对原始数据，未因报告gate布尔而采信。
原运行源码/错误日志保留，不在运行后修改冻结launcher掩盖失败。后续版本应把
原生审计放入显式runtime环境的独立子进程，默认plan测试也要覆盖该依赖入口。

局限：native teacher动作目前只在quality里归档，审核器无法从packed graph独立
再运行BattleAI来证明该fallback；但首次分叉时它与baseline实际动作相符。
特定creature6伤亡仍来自原生terminal字段；总永久伤亡另有逐真实kill事件交叉核验。
这是2张已用TRAIN图的新种子开发反证，不是独立能力测试，也不是人类高手轨迹。

本审核全程只读旧/新游戏输入，仅写本独立审核目录，无native游戏/GPU/编译/资源锁。

ARCHIVE_INVENTORY_01.json另实核G盘现有97文件、5,892,806 bytes：16份summary、
16份gzip原始轨迹、21份内容SHA命名源码快照及31项冻结输入全部通过，31项与
PREPARE_CHECK_01中的执行前计划完全一致。清单逐文件记录SHA，没有复制大文件，
没有把完整性通过写成收益通过。该数字是清单生成时快照；后续另加的收尾诊断记录
需独立列出，不改写本次清单假装它们当时就存在。
