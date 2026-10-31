# TRAIN信用跨度与480固定graph诊断：2026-10-23

结论：实际TRAIN证据足以支持把episode-boundary换图列为下一个有界单因素实验。它尚不是已证明的失败根因，也没有证明改调度必定提升。MMAI轨迹比BattleAI明显更长，固定phase关闭留下更多尚未获得该episode真实终局的行；这些行的next-value bootstrap仍有效，不能报成无效数据、截断或败局。另一个实测限制是32-step rollout的GAE边界，换图调度只能处理其中一部分。

本次没有GPU操作、原生局、优化器更新或资源锁。只核原control/candidate共同global31..57，各27个真实rollout、13824行；13个完整phase逐一用真实逐步terminal重算close-fragment，并与原phase_close_events完全核对。global57位于phase13中段，两臂都记共同观测窗右删失，不虚构phase13关闭或后续结果。GAE和终局±1由保存的真实奖励、value、next-value、terminal及graph potential重算。完整分组见`actual-02/ROLLOUT_CREDIT.json`，覆盖role、opponent、family及三者联合24组；源/原始输入SHA见`actual-02/AUDIT.json`。

额外独立用逐项有限和公式重算全部54个rollout、27648行GAE，对原实现最大绝对误差2.3841e-7，小于预设1e-6；见`GAE_DIRECT_CHECK.json`。这项核对只读原始数组，不更新策略。

| 共同31..57 | control | candidate |
|---|---:|---:|
| 正常终局 / 胜 / 负 | 494 / 359 / 135 | 506 / 368 / 138 |
| 原生截断 | 0 | 0 |
| 实际phase关闭未完行 | 2659，19.23% | 2501，18.09% |
| global57共同窗口右删失行 | 238 | 213 |
| 完成episode中跨优化更新边界者 | 191 / 494 | 186 / 506 |
| 实际终局在该行后续rollout的行 | 2680，19.39% | 2698，19.52% |
| 同rollout内看到终局的行 | 8247 | 8412 |
| 完成episode平均/最大步数 | 22.12 / 61 | 21.96 / 59 |

上述关闭比例以全部13824共同观察行为分母。13个实际关闭phase共13312行；global57另512行尚未进入本次任何关闭。没有将未完成episode结果插补为输赢。

| 对手分层，每臂各6912行 | control | candidate |
|---|---:|---:|
| BattleAI正常终局 / 胜 | 315 / 240 | 318 / 249 |
| BattleAI完整episode平均步数 | 18.57 | 18.64 |
| BattleAI关闭未完行 | 982，14.21% | 928，13.43% |
| MMAI正常终局 / 胜 | 179 / 119 | 188 / 119 |
| MMAI完整episode平均步数 | 28.36 | 27.57 |
| MMAI关闭未完行 | 1677，24.26% | 1573，22.76% |
| MMAI终局出现在后续rollout的行 | 1833，26.52% | 1799，26.03% |

24个role/opponent/family组均有实际终局，不能恢复“困难组完全没反馈”的旧假说。关闭片段的归一化优势整体均值control -0.01799、candidate -0.13558，但各联合组有正有负；无法据此给所有未完轨迹贴错误强化标签。candidate有更多终局、更少关闭行，却没有在既定开发对照优于control，因此“只需多收终局”缺乏收益证明。

代码和实际数组共同确认：GAE每个32-step rollout把tail归零，保留真实next-value bootstrap。实际episode可以跨更新继续，但后续rollout中的terminal残差不会直接回传到此前已完成更新。约19.4%的共同TRAIN行在同phase后续rollout才看到真实终局，另18%—19%成为实际phase-close片段。这两类统计分开，不能把它们都归因于换图。较长MMAI行程使有限的episode-boundary换图检验有实际动机；不能声称它能修复整个信用跨度问题。

随后对历史预固定480 TRAIN graphs完成parent30/control60/candidate60三模型CPU重放，选择规则仍为最初30个rollout各前16行、60张TRAIN图。先核旧`LEARNING_MAGNITUDE.json`所列每个raw SHA及固定update/slot/scenario，未按本次结果重选观察。详见`actual-02/FIXED480_REPLAY.json`。

| 固定480状态上的变化 | argmax改变 | 平均KL | KL中位数 |
|---|---:|---:|---:|
| parent30 → control60 | 11，2.29% | 0.005201 | 0.0000781 |
| parent30 → candidate60 | 24，5.00% | 0.027376 | 0.0001281 |
| control60 → candidate60 | 20，4.17% | 0.027199 | 0.0001341 |

candidate的变化并不均匀。固定TRAIN130/attacker/MMAI、历史rollout16 slot8上，parent与control均选合法候选118，candidate选126；parent→candidate KL7.6503、总变差0.99868，而parent→control KL0.00000523。另TRAIN184/defender/BattleAI的candidate KL1.0226。它们是实际较大局部分布变化，不能由低中位KL推导全部状态只小改，也不能把大改直接称有益或有害。这里没有该状态的独立反事实终局，不能编造行动优劣标签。candidate最终包含额外native恢复边界，亦限制纯LR因果解释。

建议进入下一个单因素时：同一完整模型/Adam/RNG公共父边界，保留LR、PPO、reward、critic、冻结层和TRAIN集合，只比较原固定phase换图与达到最小暴露后在真实episode终点换图。预登记样本预算、最大等待上限、逐worker覆盖/权重及未完片段处理；先小规模机制/资源验证，再有限训练与固定独立paired评估。必须同时报告终局覆盖、MMAI长程片段、损兵与赢率，验证调度改变是否实际改善信用和能力。若片段减少但能力不增，该假说应降级，不继续追加次数。DEV仅发现失败类型，未在此次诊断读取DEV动作或创建教师标签。
