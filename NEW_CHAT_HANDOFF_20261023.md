# Heroes III AI Lab 新 chat 交接（2026-10-23）

本文件覆盖旧交接中的运行状态与下一步指令；历史证据不覆盖、不删除。不要依赖聊天历史，也不要机械接受本文件的解释，应按以下索引核验原始记录。

## 1. 用户目标、授权与当前状态

完整目标：完成能够进行《英雄无敌3》完整战略对局的 AI，包括探索、经济、招募、兵力调度和整体取胜；同时推进真实原生机制验证的人类战术学习与反制。局部战斗研究目标为稳定战胜公开作者 MMAI、对 BattleAI 至少95%并接近100%，但不是战略开发的前置条件。交付可恢复模型、可复现实验和独立评估，不承诺所有局面必胜。

用户授权隔离代码修改、编译、实验、训练和子智能体分工；仅一个 GPU 学习器；共享原生模拟资源遵守锁；24并发允许在稳定性/资源测量后逐步实现。原冻结战斗环境、运行中冻结输入与历史证据必须保留。不得伪造专家示范、视频理解或胜率。

**现在 goal 为 paused，未完成。** 用户10月20日要求停止，已停止；10月23日仅清理 WSL、分析失败与准备交接，没有恢复训练。新 chat 收到明确继续指令后再恢复。不能因读到旧日志的 active/live 自动启动。

10月20日已实际关闭学习器及 worker，取得再释放两个锁；10月23日本次交接又查看 WSL ps 与 nvidia-smi，未见相关训练/游戏进程或 GPU compute 应用。未在本次交接重新取得资源锁；新启动前仍须实际核对。

## 2. 工作区与优先阅读索引

- Windows：`G:\Heroes3-AI-Lab`；WSL Ubuntu-22.04：`/root/heroes3-ai-lab`；Windows挂载：`/mnt/g/Heroes3-AI-Lab`。
- `PAUSE_HANDOFF_20261020_FINAL.md`：停止过程、模型与未完成工作。
- `experiments/strategic-learned-free-transfer-run-v1/independent-dev-01/REPORT.md` 及 `review-01/REVIEW.json`、`PAIR06_EVIDENCE.json`、`PROBABILITY_COMPARISON.json`：最新战略独立结果与决策漂移。
- 同 run 的 `independent-train-01/REPORT.md`；policy 的 `recovery-audit-01/native-cuda-update1-01/AUDIT.json`：训练及真实 GPU 边界恢复。
- `experiments/battle-diverse-curriculum-20261020/final-independent-01/REVIEW.md`、`actual-review-02/AUDIT.json`、`SLOT_TERMINALS.json`、`LEARNING_MAGNITUDE.json`、`RESUME_READINESS.md`：已完成战斗批次。后者描述旧入口限制，随后 continuation 已实现部分恢复，不要当作当前所有入口均未恢复。
- `experiments/battle-training-continuation-20261020/monitor-independent-01/user-pause-01/PAUSE.json`，同级 `two-arm-restoration-01/AUDIT.json`；该实验 `cuda-restore-parent-01/AUDIT.json`、PLAN及实际代码：待完成学习率对照。
- `experiments/strategic-learning-mainline-20261020/GOAL_GAPS.md`：完整目标尚缺能力。
- 招募新源 `experiments/strategic-learned-recruitment-native-v2` 的合同、manifest、build_capsule.py、qualification/PLAN.md；政策草稿 `experiments/strategic-learned-recruitment-policy-v1/REVIEW.md`。
- `maintenance/wsl-cleanup-20261023/README.md`、`SUMMARY.json`、保护SHA前后清单：已完成清理及重编译注意。
- `CURRENT_PROGRESS_20261018_TAKEOVER.md` 是倒序历史，旧 live/active 与中间假说已被后续记录覆盖。`NEW_CHAT_HANDOFF_20261018.md` 仅供早期背景。

## 3. 当前能做什么，不能宣称什么

战略真实合法执行、完整对局、采样、建造策略及模型/Adam/RNG恢复均有实际证据。合格版本仍为**单英雄神经策略，招募脚本化，免费转兵为原生辅助，战斗委托原生 BattleAI**。独立图战斗模型尚未整合进战略控制器。多英雄调度、无英雄时完整城镇经济决策、真正学会招募仍缺失。

人类战术支线只有原生事件/机制验证，没有整体收益认证的专家课程。撤销的示范质量标签不得重新当专家数据使用。

工程跑通、真实梯度、TRAIN成绩、独立提升是四件事。目前前两项成立，最近几批没有独立能力提升，模型没有升级。

## 4. 战略：真实结果与失败诊断

较早的建造探索链完成4次同优化器更新、504 Adam、8012行、130次真实建造（其中6收入），最终配对DEV仍4/8→4/8。最终模型 SHA `24b8c3f3d5ddacd61e48bd87a526c1fd59b2a83eafbdacfe44bd5ddcfb5d3e6d`。

已确认并修复一个执行缺陷：旧经济窗跳过支出时也跳过城内现成兵免费交给来访英雄，英雄可能空着大量城防库存离城。native-v2/capsule02 的实际机制专用地图证明：新雇10枪兵→接收城内20枪兵与10弓手→首次策略请求，资源/军队守恒、真实ACK、整局489 owned requests排空通过。此机制地图不是训练/专家/胜率样本。原生ACK可能在handler失败时仍给成功码，因此资格必须结合实际库存、军队和资源状态，不看ACK单独通过。

修复后最新训练：

- `strategic-learned-free-transfer-policy-v1` 初始化833，weights-only继承24b8，**新 Adam/RNG**，不是504+132同一优化器链。
- 初始化SHA `83319be8bde5d94eea839b1a889821449a7c1492c65da7ca6cde2deb63aab25a`。
- 原8TRAIN格，2089行、41真实建造（3收入）、132实际CUDA Adam；对EmptyAI四胜，对Nullkiller2四负。
- 更新模型SHA `6dd26e29b55364c293d9874c36a743e4636bcd0208daf5e61042e1f8b506ea00`，Linux `evaluations/strategic-learned-free-transfer-train-01/update-01/update-1.pt`。
- 实际GPU完整恢复与6项拒绝负例通过。独立审核重算8TRAIN原始局、16DEV原始局及5090完整CPU proposal。
- 同capsule配对16DEV：初始化5/8，更新4/8；建造95→70，收入建造16→11；**未提升，不升级**。

已定位的行为问题：唯一负翻转pair06，前4个完整请求相同，q4首次动作不同。原策略day1回城补兵，兵力2860→5114；新策略去矿，day4才首次补兵。q4是自由选择，非强制旧目标，不是先前免费交兵缺陷。后续局面已分叉，不能认定单步造成最终失败。新模型在全部2089旧TRAIN观察上回城argmax247→229，10次城→矿、没有反向进城改变；支持“这次更新降低了所观察状态的补兵倾向”，不代表所有局面均如此。

所有4局NK训练均败，没有这批NK成功轨迹可强化。终局奖惩对早期补兵/经济抉择的归因、对手难度和训练/开发地图分布可能影响方向，**都是需实验的解释，不是已证明根因**。算法按episode平衡，不能用Empty1738行/NK351行直接断言梯度按该比例失衡。不能把DEV q4抄成教师标签。

战略完整证据归档 `strategic-learned-free-transfer-run-v1/independent-dev-01/delivery-01/ARCHIVE_MANIFEST.json`，SHA `13a2f96e7f7a9bb80cef040c3361a588b092998610296320184e9e55b8cc2ef9`，29317普通文件、108链接、733736527字节，已实际复制并双次校验；外部Data/Mods是链接，不冒称整树已复制。

## 5. 战斗：完成批次与待续批次

基线B64：`/root/heroes3-ai-lab/models/graph-finetune/1792068859379237126/update-64.pt`，SHA `1e022707186a3c0dad7c671233b100930e870fff6c79cc703fb5b89dfb192936`。

已完成60TRAIN地图×角色×对手240格、16worker批次：30更新、15360行、3840真实CUDA Adam、551正常终局370胜、0截断；最终parent30 SHA `dcaab92162b9c5b4cb9e5d9773067a320fe9b81fe91c1907449d4a7f8374cdaa`。固定64DEV：BattleAI12/16→12/16，公开原作者MMAI11/16→10/16，平均损兵亦未改善。这些小样本不代表总体胜率，更未达95%目标。

真实参数发生变化，不是没有梯度。480预固定TRAIN代表状态只有12个argmax改变（2.5%）；各轮KL小，但没有普遍KL提前停止或PPO clip阻断。240格全有至少一次正常终局，不能再声称难格完全没反馈。critic压倒actor假说已被实际梯度支持集研究反证，不据此乱降critic系数。phase关闭后未完片段3313行占21.57%，有真实next-value bootstrap；可以研究episode-boundary调度，但不能直接说这些行无效或被算败。

后续仅改body LR的配对实验目前未完：parent30全模型/Adam/四RNG/累计步3840恢复已真实验证；control body1e-6、candidate3e-6，heads均1e-5。

- control 完成global60：30新增更新、15360新增行、3840新增Adam，累计7680。SHA `443863dd26ea0daaed17cd01ab3dd44a6a16544efac73c96a89839f5b72c0e20`。
- candidate停于global57：27新增更新、13824新增行、3456新增Adam，累计7296。SHA `8d3169e85d51b0bf7d7247cc2d4bdc6949410d5262793f1729a6463dbd3976bf`。
- 两者完整G副本位于 `experiments/battle-training-continuation-20261020/monitor-independent-01/user-pause-01/{control-update-60.pt,candidate-update-57.pt}`，原Linux保存仍在 `evaluations/battle-continuation-lr-paired-01/{control,candidate}/models/`。
- 两条优化器分支不可相加。用户SIGINT导致controller exit1/RESULT失败标志，**不是训练自行崩溃或游戏失败**；未完rollout没变成更新或败局。
- **预定96DEV没跑，学习率方向无能力结论。**

**不能直接运行原run.py --execute续训**：会从固定parent30重做两臂。应在新隔离版本明确从candidate57恢复全部状态、累计计数与余下3更新，处理课程phase13半阶段与新原生episode边界；不用原生在途状态假装无缝恢复。控制臂不重跑。完成预登记global60后再跑96DEV（共享parent32局+control32+candidate32），保留每步实际graph/动作/概率/native返回。现有final auditor尚未对完整结果运行。

## 6. 招募主线真正停在哪里（本次已核文件）

`strategic-learned-recruitment-native-v2` 是source-ready，**未C++编译、未真实原生资格**。manifest `865988a27bc8de8f257b767ac5b10927e76da96fe974e37414fe7519f38e7830`，contract `1f3a9d3c0777e31787df5e8cd2a2af1614d326a04f9b0f85ac0e83c3e42d15a3`。旧v1草稿保留。目标schema6：真实城镇招募候选、数量桶、七资源成本、目的军队/库存/槽位；实际绑定提交与全状态后验；同种兵新增库存免费移交；整回合经济窗Move后仍开，仅End关。旧模式不变。

`strategic-learned-recruitment-policy-v1` 目前只有encoder.py、model.py、check_cpu.py、creature_vocabulary.json、REVIEW.md及CPU报告。没有完整loader、broker/admit/PPO/保存流程，**没有实际招募训练模型**。真实runtime creature catalog尚未捕获；synthetic catalog和人工recruit_state CPU梯度检查不能当资格；默认全UNK不可训练，手工recruit_bias=-4不是学习或专家。

**本次实际核验 `experiments/strategic-learned-recruitment-run-v1` 不存在。** 旧任务描述中的计划和代理分配不是已写好的运行包，下一chat必须实际完成，不可直接调用想象入口。

native-v2/qualification已有selector.py、prepare_fixture.py、pipeline_common.py、collect_mechanism.py、derive_collector.py、DERIVATION.json、FIXTURE_MANIFEST.json、PLAN.md等，均视为待审核/未执行草稿。目标真实同turn Build→Recruit1→Move出城→Recruit1同物种→Move回城→真实免费转兵ACK→End。先ready后起native、收到真实请求后绑定catalog，避免启动死锁。机制脚本非NN、非PPO、非专家；无阶段覆盖就不合格。

恢复后build入口（先核源/锁，不能现在执行）：

`/usr/bin/python3 /mnt/g/Heroes3-AI-Lab/experiments/strategic-learned-recruitment-native-v2/build_capsule.py --out /root/heroes3-ai-lab/evaluations/strategic-learned-recruitment-capsule-01 --execute`

新资格成功后再冻结catalog、实现完整策略接线并开始有限真实PPO。此前固定8TRAIN seeds3900及16DEV4000仅是未执行计划，须核对并明确登记，不能报告已跑。

## 7. 下一步研究顺序：以学到有效决策为准

1. 重新核进程、GPU、GPU锁→pool锁、冻结SHA和实际文件；恢复goal后执行。只做必要恢复验证，不重演所有已通过历史审计。
2. 战略优先完成招募实际机制资格和完整策略/PPO接线，随后有预算的真实训练、保存加载与同运行时配对评估。进一步接入多英雄/城镇actor调度，别把单英雄工程成功等同完整目标。
3. 对学习方向做TRAIN诊断：按对手/动作类型检查优势值及补兵、经济、失城的关联；设计能产生真实主动对手成功经验的分级课程。对稀疏信用分配、难度或奖励只做单因素实验；不能同时改奖励/LR/课程后归因。避免只刷EmptyAI胜率。
4. 战斗完成剩余有界LR对照及独立评估再决定方法；若无收益，依据逐步轨迹研究时序/episode调度或更新幅度。不能靠追加训练轮数、盲目解冻全网或降低critic系数替代诊断。
5. 多地图、多种子、双角色与两类对手的配对评估，胜率与损失/补兵时机/失城分开报告；DEV不直接变专家教材，另保留最终测试集。人类课程须同时满足原生机制和整体收益认证才入训练。

目标是实际能力提升，不是无限增加验证框架。但涉及新动作、恢复边界和公平评估的必要资格仍要完成。

## 8. 冻结保护、资源与清理

锁路径 `/root/heroes3-ai-lab/evaluations/.gpu-learner-lock` 然后 `.pool-lock`；不要删除锁文件“解锁”。单GPU学习器，16战斗worker有实测资源余量，24战斗GPU训练尚未认证。实际采样曾有1MiB swap，不报零。

冻结战斗build `/root/heroes3-ai-lab/src/gym/vcmi/rel/bin` 不动。accepted战略源 `/root/heroes3-ai-lab/src/vcmi-adv`，build `src/vcmi-adv-build`。使用隔离capsule，driver应精确还原accepted源和3bins。

accepted client SHA `b94162bb0d20566ae88512457bdb33266415d338fe92e50c4a6aa6dbd578dd78`；server `bbe0de38b7791c7900b2393d1809b38f5f1856ac8922f30d742095759cd43fac`；lib `d7016313e9f0e0dfc36d46a9e24d718fb2e7552e6433b5dcd0ca6a26cdaa285a`。source epoch/runtime hash应以对应manifest逐项核对，不跨版本套用。

10月23日已清理42份可重建PCH及npm/NVIDIA/Triton/apt缓存；WSL实际空闲增加11379351552字节（约10.60GiB/11.38GB）。保护的冻结程序、库和模型SHA前后一致，源码/模型/worker raw/eval证据未删。**下次编译会重建PCH，首次稍慢正常。** fstrim报告865.9GiB是全部空闲extent，不是本次释放量或Windows VHDX缩小证明。不重复执行已完成清理脚本，不清其他项目。

本文件写作期间未训练、未编译、未修改研究输入。全部历史模型、原始失败与中间证据继续保留。
