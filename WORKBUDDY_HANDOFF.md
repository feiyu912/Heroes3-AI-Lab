# Heroes III AI 完整上下文交接入口

2026-10-18 DirectorAI 移动补充：WORKBUDDY_DIRECTORAI_PATH_REVIEW_20261018.md。pos/visitablePos 存在引擎明确转换，不能将偏移直接判为过期；harness 当前仅打印分配，尚未强制校验与传播游戏退出状态。

2026-10-18 战术 events-v2 交付复核：请先读 WORKBUDDY_EVENTS_V2_REVIEW_20261018.md。发现动作与事件错位、终局事件漏存、反击主体统计错误及未知单位默认诱饵；现有动作级示范认证须冻结复核。未修改实施窗口代码或启动训练。

2026-10-18 M1/M2补充：原生完整对局已报告跑通；DirectorAI当前代码的cbc初始化、敌方对象枚举、异步移动、AI环境变量映射及日志覆盖问题见 `WORKBUDDY_DIRECTORAI_REVIEW_20261018.md`。这是只读定位建议，未改其活动代码，具体崩溃仍须调用栈和修复后实测。

2026-10-18冒险构建补充：`WORKBUDDY_ADVENTURE_BUILD_REVIEW_20261018.md` 已实核ENABLE_ML开关及动态依赖，建议独立非ML构建完整配套客户端/服务端/库，不能与旧ML构建混搭，不因常规隔离编译再次等待确认。

**用户最新优先级（2026-10-17）：请先读 `WORKBUDDY_NEXT_TASK_STRATEGY.md`。推进小地图完整对局和战略决策，保留战斗层；单场BattleAI 95%不再是启动战略研发的前置门槛。用户已要求WorkBuddy按此继续。以下内容保留为历史与技术交接，不要把历史单场目标覆盖最新方向。**

用户准备新增一个窗口；按当前上下文将人类战术验证/反制交给新窗口，任务书为 `NEW_WINDOW_HUMAN_TACTICS_TASK.md`。现有WorkBuddy继续战略层；并行代码/算力边界见 `PARALLEL_WINDOW_COORDINATION.md`，不要重复启动两套24worker任务。

交接日期：2026-10-17，Asia/Shanghai。交接给正在运行本工程的 WorkBuddy。本文及 `handoff/2026-10-17/` 补充已有工作，不要求停止、回滚或重新启动现有任务。交接时只读核查了当前进程和文件，没有改变活动训练/评估代码、参数或模型。

后续更新：v2六套结果已落盘后，新增只读复核 `WORKBUDDY_REVIEW_20261017.md`，修正“守方16败”“飞行兵分类”“蒸馏93.75%理论上限”等影响v3设计的推论。它不替换冻结原报告，当前进度继续以活进程和最新文件为准。

## 0. 先识别当前运行，旧暂停状态已经不是最新进度

2026-10-17 约23:00的实际核查：

- 新编排为 `experiments/run-mixed-v2.py`，输出目录 `experiments/expert-mixed-b64-run-v2/`。
- 控制进程当时为 WSL PID 2401，命令 `python experiments/run-mixed-v2.py --eval-only`。子评估当时 PID 23817，正在评估 mixed-16 对原公开作者 MMAI。这些PID只是交接瞬时证据，后续必须重新查进程，不能硬编码恢复。
- 训练实际已完成32次更新，`CUDA_training=true`、`all_workers_exit_zero=true`。报告：`experiments/expert-mixed-ppo-v1/b64-anchor-plan-v2/training.json`。
- 当前计划：`experiments/expert-mixed-ppo-v1/b64-anchor-plan-v2.json`；其内容SHA为 `0b51ff49e7dc32203a5362f83c99a024a9ce74be235e0f86931ec2d980223ff1`。
- update-16：`/root/heroes3-ai-lab/models/expert-mixed-ppo-v1/1792248247434187598/update-16.pt`，实际文件SHA `326d0721739d470c126e6c2dde76364d6d98747eb78a57dc6e5893b0f8aba633`。
- update-32：同目录 `update-32.pt`，实际文件SHA `4eb5fa7af5800025644f708f007e0ca3f5e88eae59825b5a0d2cf55b26bbe65a`。
- 已完成开发报告：B64对BattleAI172/192、对作者114/192；mixed-16对BattleAI172/192。mixed-16作者及mixed-32结果在本次核查时未全部完成，不能提前推断。以当前最终报告为准。
- 训练报告记录45个轮换/结束时被关闭的已采样未终局片段。这与环境truncation不同，不得把它们算输赢，也不能把“环境截断0”写成“从未关闭未完成战斗”。

旧 `PAUSED_HANDOFF_20261016.md`、`expert-mixed-b64-run-v1/paused-state.json` 记录的是上次暂停：7次更新未到16保存点、没有新权重。WorkBuddy已使用新v2重新从B64开始并完成训练，因此**不要再按旧记录重启一遍，不要删除v2，也不要恢复旧PID**。本Codex聊天的goal仍暂停；正在推进任务的是WorkBuddy，本次仅交接文件和上下文。

## 1. 用户的完整目标与授权

近期明确目标：公平地、可复现地证明模型稳定战胜作者公开MMAI，对BattleAI至少95%、尽量接近100%。用户要求直接做工程、持续训练及失败分析，不能只给待办；支持子智能体处理资料、规则、代码和审计。训练并发明确选过24；不应擅自改成48或再开一个争用资源的学习器。

长期主目标并没有缩小成普通兵堆战：结构化Decision Model、教师数据、BC、PPO、搜索互补、战术和主动魔法、战略决策，最终公平的超大地图1v7（自研AI独立对抗包括人类在内的7人联盟）。当前普通战斗胜率达标也不能冒充已经完成长期目标。

原始主指令完整副本见 `handoff/2026-10-17/original_requests/01_master_v2.txt`；人类战术课程原文见 `02_human_tactics_curriculum.txt`；专家知识管线补充见 `03_expert_pipeline_request.md`。原文中的“正在第71/128轮”等是当时状态，不能覆盖当前运行事实。

## 2. 环境、引擎与运行约束

- Windows共享工程 `G:\Heroes3-AI-Lab`；WSL为Ubuntu-22.04，工程Linux路径 `/mnt/g/Heroes3-AI-Lab`；运行库根目录 `/root/heroes3-ai-lab`。
- i7-14700KF，20核/28线程；RTX5070Ti16GB；主机32GB。此前WSL约16GiB RAM+4GiB swap，接手时重查实际配置。
- CPU Python：`/root/heroes3-ai-lab/venv/bin/python`；CUDA Python：`/root/heroes3-ai-lab/gpu-venv/bin/python`。此前PyTorch2.10/cu128，当前版本以运行环境为准。
- 复用 `research/run-lab.sh`：它配置模块、原生库、隔离worker和线程数；`LAB_PYTHON`指定CPU/CUDA解释器。不要随手用Windows Python启动Linux模型。
- 原生gym版本此前固定11241d496db95541766498373e23245a67847a97；engine e956242503f465ae6ec0a62a3aeb2c4ea179db5c。版本/库SHA以各run冻结清单为准。
- GPU负责神经推理和更新；VCMI规则模拟仍为CPU。低GPU利用率不等于没有用CUDA，不要为提高仪表盘数字盲目增加并发。
- 全局资源锁：`/root/heroes3-ai-lab/evaluations/.pool-lock`，标准评估12worker、训练24worker。避免同时开启两个GPU学习器或重复的游戏池。检查活进程及实际文件增量，不凭旧control.json断定卡死/完成。
- 不覆盖正式Windows VCMI、原始原生库和游戏资产；实验在隔离目录/版本中做。

## 3. 当前模型和强化学习到底是什么

主线使用公开MMAI v15恢复的typed-graph actor/critic，约8,993,178参数，约100,356个heads参数可训练；不是通用LLM或自然语言API。它本身属于“结构化状态→候选合法动作评分”的Decision Model范式，不等于主指令所列全部架构比较已经完成。

核心：`research/recovered-graph.py`、`masked_ppo.py`、`vector_env.py`、`gpu_opponent.py`；新增参考约束在 `experiments/conservative-ppo-v1/reference_ppo.py`。Masked PPO使用GAE、合法分布、clip、entropy/value/gradient clipping；truncation对最终观测bootstrap。终局胜负来自原生result_type/winner/军队伤亡。

当前v2混合：B64初始化，独立冻结B64参考，新heads优化器；lr1e-4、32updates、rollout32、gamma1、stepcost0、potential shaping0.5、entropy0.005、reference KL0.1。24worker为12普通BattleAI、8有偏弱脚本、4原公开MMAI历史对手，即50%/33.33%/16.67%，不是精确50/30/20。每类角色平衡；专家三家族×双方角色分层。历史对手始终是原公开CPU ONNX，不随参考锚点改变。

脚本专家来自指定支线，只作对手与反例生成器，不能认证最优。Reference不能取ExpertOpponent.pair（它没有pair，旧assert_unchanged恒True）；当前实现独立加载冻结神经参考，从raw obs独立编码，不能复用已改变的学习器body embedding。

## 4. 已完成结果，明确不能说成达标

|实验|实际结果|结论|
|---|---|---|
|原公开作者→BattleAI，正式512|457/512=89.2578%|基线|
|旧选中组合→BattleAI，正式512|434/512=84.7656%|低于原公开基线|
|旧选中组合→原作者，正式512|268/512=52.3438%，场景聚类95%约[44.14%,60.55%]|不能证明稳定胜出|
|旧v3→BattleAI/作者，正式各512|214/512、84/512|失败基线，保留|
|BattleAI教师代理→BattleAI，512|254/512|depth2代理，不自动等于两个原生BattleAI完全相同|
|公开起点保守PPO开发，每对手192|public/16/32对BTAI均157；对作者96/103/101|未持续改善BTAI|
|185条Q2脚本BC，独立每模型12|10胜→9胜；平均阵亡72.583→77.667|拒绝作为变强证据|
|来源WAIT BC，独立每模型4|都4胜、每局损1幽灵龙；首WAIT/跨轮窗口1→2|部分行为迁移，没改善胜负/战损|
|旧普通开发匹配96：B64/185BC/WAITBC|BTAI84/83/85；作者58/58/58|差1场不足证明提高|

正式六套共3072场，0非法/0环境截断/0非正常终局；原模型/ONNX及报告审计在 `research/challenge-delivery-audit.json`。置信区间需按场景聚类，不能只拿逐局Wilson支持稳定泛化。

旧正式冻结组合文件 `models/challenge-v4/policy.pt`，SHA `14f5c4fca8c804c125eebabeb06a8483a137653ea54594321e9ca60cbb9cbb2e`。它是角色组合权重，能加载但没有一套可继承的单父优化器，继续PPO应新建优化器，不能伪造resume。

B64：`/root/heroes3-ai-lab/models/graph-finetune/1792068859379237126/update-64.pt`；SHA `1e022707186a3c0dad7c671233b100930e870fff6c79cc703fb5b89dfb192936`。这是旧全图阶段模型，不能把它的旧全图优化器直接装进新heads优化器。当前v2同方法16/32保存了本方法优化器/RNG，但按冻结边界重新开原生战斗，不能声称逐帧恢复局内状态。

## 5. 人类战术/专家来源的实际边界

- 已有28条战术目录、11条来源记录和15个试点候选。11条来源不是11位高手，也不是11份获准训练素材。
- 优先阿青Hero3，也登记狂小Z、咖啡、Lexiav等；B站HTTP412/动态频道外壳只取得部分元数据。没有完成高手视频理解、完整字幕获取或真人操作轨迹提取。
- 实际读取Hallas2001具名文字攻略，但没有认证其职业排名。WAIT案例是来源支持的工程重建，不是还原他的历史真实兵力、坐标或动作轨迹。
- WAIT复现8组16局均验证跨轮窗口，4组同损、4组WAIT损1ghost而control损2。只取4条首步WAIT，没把后续greedy整条轨迹标最优。老化和伤害随机性尚未事件级隔离。
- 真实CUDA BC 60步，NLL9.8438759→1.8457727；4训练动作argmax1→3，仍有一条WAIT排名第8。冻结后8个模型局的独立对照已完成，最终结果以 `experiments/EXPERT_PILOT_RESULTS.md` 为准。
- 185标签来自6个正常赢局，Q2探索，不是逐动作最优认证，也不是真人示范。训练前24局718条决策、2471空关系的原数据均保留。
- 数据门禁区分script/search/human_structured与experimental_reconstruction；video_guess不能冒充动作，未知状态/战损写null。
- 当前v15仅WAIT/DEFEND/MOVE/AMOVE/SHOOT；没有主动英雄魔法，没有主动拒绝自动反击。龙主动多目标边与反击误伤事件认证不同；GhostDragon没有喷吐，WAIT试验不能认证龙息。
- 反击剩余次数、持久unit ID、绝对数量等接口存在缺口；任意初始hex/朝向、独立行动次序、复杂障碍/城战未完成。场景实际用军量/槽位和默认loose，不能宣称tight夹具参数已经透传worker。
- 主动魔法、失明复活/镜像等为后续；兵链、经济、飞跳回进战略库，等待大地图接口。

## 6. 用户指定的另一条支线已经审计

聊天 `codex://threads/01a14038-9268-7ff0-989d-ce1cafe46b35`；worktree `G:\Heroes3-AI-Lab-worktrees\human-expert-learning-v1`；commit `5e3a7152d3ea8d3cc4626f4802480c3e50ac1fbf`。

该支线21局401转移、shape/dtype和前后图哈希链、合法动作、原生终局，以及保存的12步真实逐步回放已离线核查。真人动作和原生即时伤害事件均0。63条脚本数据来自4个败局；CPU40步BC后独立4/8→4/8，平均阵亡87.875→93.125；普通2/4→2/4。失败模型不应替换正式模型。

可复用记录/回放/专家接口；旧PPO适配器只做cases[0]、attacker、1env、1update smoke，并未消费完整混合课程。旧10项pattern用于24env实际14/6/4且角色/家族偏置，当前新mixed版本已改12/8/4及family×role门禁。专家“无友伤多目标强制优先”可能错过重要单目标击杀，是有偏策略，不代表最优或伤害事件认证。

参阅 `experiments/BRANCH_INTEGRATION_REVIEW.md`、`SIDEBRANCH_EVIDENCE_AUDIT.md/.json` 以及支线 `tools/human_expert/{README,RESULTS,AUDIT}.md`。

## 7. 已踩过的工程坑：不要再重复

1. JSON空边attrs=[]会丢(0,width)维度。使用 `experiments/expert-knowledge-v1/graph_observation_codec.py` 按真实pyconnector schema恢复；旧失败源码和数据已冻结，别热改。
2. Reference KL训练目标不能直接使用inference_mode内创建的张量参与反传；source BC已用no_grad修复。真实CPU forward/backward和CUDA结果分开记。
3. CUDA重算必须原推理批量24、atol2e-4/rtol0、deterministic+CUBLAS4096，不能放宽阈值掩盖旧scatter数值问题。相关CPU数学与实际恢复证据见reference目录及research/live-training-resume-contract.json。
4. reference与learner参数独立、冻结、不入optimizer；合法ID顺序必须一致，padding不应制造NaN/KL。
5. 旧 `run-next-mixed.py` 含失效PID和v1路径，不直接复用；当前 `run-mixed-v2.py` 已纠正。任何重启先核当前PID/输出/文件，观察超时不等于进程停止。
6. Source控制文件用status，部分旧控制器只读state；统一读两者，不能空等已失败任务。当前没有必要为此改活动控制器。
7. Windows PowerShell5的 `@(Get-Content -Raw|ConvertFrom-Json).Count` 可能为1；用解析出的数组.Count。UTF8 BOM需Python utf-8-sig。
8. 所有终局必须核result_type/winner/initial_armies/casualties；退出码0不等于报告已生成，缺报告不能补造。复活/召唤需要扩展永久战损审计，不套普通局假设。
9. checkpoint只在16/32保存，日志latest_update不等于已保存权重。新同方法resume必须验证config/planSHA/optimizer模式/RNG；body冻结不等于旧full-graph optimizer兼容。
10. 轮换/主动关闭未终局片段独立记账，不能冒充正常输赢或完全无中断。随机合法动作是探索手段，不是高质量教师。
11. 警惕脚本覆盖次数增加而胜率/战损变坏，两个BC试验都提供了这类反例。
12. WSL低资源/ONNX多进程CUDA重复模型曾导致内存问题，使用中央神经对手推理和CPU原生正式作者评估；原生每worker CUDA失败方案不要当已采用优化。
13. WorkBuddy拦截wsl.exe是它的命令拒绝策略，与GPU训练算法无关；按其安全中心正规放行，不改名/复制程序绕过。当前此Codex只读WSL成功，不代表另一个会话权限一定相同。

## 8. 数据划分和下一步验收

- 普通训练：`research/diverse-curriculum.json` IDs0..191；开发192..239。当前每模型×每对手48×2roles×2seeds=192；三模型两对手共1152。开发结果允许选择下一方案，不能称未见最终确认。
- 旧 `research/challenge-holdout.json` 的512场已看过，用于诊断。不得修改旧选择后重称新测试。
- 新 `experiments/confirmation-v2/scenarios.json`：32新镜像图，seed2026101601，8类×4，计划32×2×8=512/对手。清单SHA `4959d4d0b711c6a552a6d61b636bc19d5971625058900adfcf10510e88d2cf3c`；去重12清单404条记录、地图回读和重复生成通过。本次交接未运行该集合；接手再核有无被其他进程使用，不能凭历史保证仍未读。
- 新确认必须先按开发选定候选，固定模型/地图/规则/代码SHA，再用原公开CPU ONNX作者和BattleAI；保存全部输赢、异常、截断、非法、角色和按场景聚类区间。
- 先让当前v2六套评估结束，核原生结果、源/模型SHA、训练类别/角色计数和45个unfinished fragments；比较完整开发数据，不凭训练reward宣布提升。
- 若未改善，依据失败家族调整初始化、lr、KL、混合比例、强专家/搜索、BC质量或模型范围。方法可以改变，但不删失败、不作弊、不为了通过而挑容易地图，不机械重跑同一无效配置。
- 完整课程还欠：可靠反制专家和原生伤害/反击事件、高质量获准真人轨迹、多训练seed、五种等预算BC/PPO/BC+PPO/历史池对照、跨来源/兵种/布局泛化。主动施法和战略接口仍是长期欠项。
- 达不到目标就明确未达到；goal/阶段“完成”要按实际证据逐项验收。不要替用户购买云资源，不把本地训练改成外部API调用。

## 9. 交接包结构与证据优先级

`handoff/2026-10-17/` 包含原始两份指令、专家管线请求、关键文档/代码/JSON的快照副本、运行快照和SHA清单。大模型、完整原始轨迹和游戏资源不重复复制，它们留原路径；`artifact-index.json`登记可定位文件。需要实际WSL访问核验模型，Windows文档副本不能替代模型存在性检查。

优先级：最新活进程+本次实际输出 > 与SHA绑定的原始对局/模型/源码 > 聚合报告 > 历史文档陈述。部分源码/文档提到pending或v1暂停是阶段快照，最终专项事实在 `experiments/EXPERT_PILOT_RESULTS.md/.json`，当前训练事实在v2。不要修改冻结原文来假装早已完成。

这是共享文件交接，不是已确认收到的跨应用消息。当前没有可用的WorkBuddy消息发送接口；不能声称已向其会话送达或已读。接手AI读到本文后可在自己的新文件中记录接收时间/核查清单，但不要为了接收交接而打断正常评估。
