# 全新窗口接管：Heroes III AI Lab

交接日期：2026-10-18。用户要求转到全新窗口、创建 goal，继续原来两个 WorkBuddy 窗口及本窗口的全部相关工作。本文件为最新状态入口；旧交接文件里“只读复核”“暂停”“还在运行”的描述可能已过期。以下成果需结合原始记录复核，不能因交接文字直接认定验收通过。

## 1. 用户目标与授权

继续开发能够完成《英雄无敌3》完整对局的 AI，从局部战斗走向探索、资源、经济、招募、兵力调度和整体取胜。完整战略对局是当前优先级；单场 BattleAI 至少95%、接近100%和稳定战胜公开作者 MMAI，仍为局部能力目标，但不是战略工作的前置条件。不得承诺所有兵力局面必胜。

结合可核查的人类专家知识，学会主动使用和反制战术，而不是盲目模仿或只利用旧 AI 漏洞。当前事件、接口和训练闭环只是工程进展，远未证明目标达成。创建明确的持续 goal，依据实测失败调整方法，最终交付可恢复模型、可复现实验、独立评估与诚实报告。不要仅写计划后停下；用户已授权读写、隔离编译、实验和训练，不要重复问常规实施许可。允许子智能体分工，独占GPU学习器，协调共享环境资源。

24并发是此前用户授权的训练规模，不代表现有战略架构已实现24环境；当前战略PPO是单环境接口试点，应先稳定再测吞吐扩展。

## 2. 交接时进程与最新结果（最先复核）

交接时通过 WSL ps 实核：无训练器、vcmiclient、vcmiserver 或 broker 进程。最近训练已失败退出，不能说仍在训练，也不能盲目重复启动。

最新记录：`experiments/strategic-policy-v1/ppo-pilot-02/training.json`，status=failed，但 CUDA_training=true 是有实际参数更新支撑的：

- update1：4个正常完整对局，1271决策，80个minibatch，保存 update-1.pt。
- update2：4个正常完整对局，1515决策，96个minibatch，保存 update-2.pt。
- 这8局对EmptyAI四局全胜，对Nullkiller2四局全败，是训练采样，不是独立测试。
- update3 episode0：DirectorAI红方对EmptyAI，train-01-mines，seed2026101930，90秒超时，11823个真实已执行决策、11823次有效位移。不能再把这个问题简单归因于此前已修好的“移动不执行”或“对话总取消”。需要查目标循环、策略停滞、游戏结束条件与完整轨迹，尚无已证根因。
- 该超时局 reward=null、valid=false，未进入PPO，update3未更新，整个程序按门禁停止。保留原始证据。
- update1 SHA256：965eb0f363ba04a09e6844efdb59dbdd7b16aaa53d0e84660d35f376bc9e302b。
- update2 SHA256：25ff6d18c51698394991ae84c53800d1c8488a0005f172427989e4fed384b5b0。
- 失败原生目录：`/root/heroes3-ai-lab/workers/adv-runs/update-3-episode-0-2026101930-2ahbjm60`。
- 失败采样目录：`/root/heroes3-ai-lab/workers/strategy-agent-runs/update-3-episode-0-4edxrk4r`。
- 12个变化tensor当前是相对初始化累计值，不足以分别说明本次actor/critic改进；尚未证明模型变强。

此前 ppo-pilot-01 在采样阶段失败，实际更新0；其目录 POSTMORTEM.md 已纠正旧字段误报。勿混淆两轮。

交接后追加只读审计：`experiments/strategic-policy-v1/ppo-pilot-02/TIMEOUT_TRACE_AUDIT.json`，可由同目录上级的 audit_timeout_readonly.py 重算。11823个决策记录全部没有kind0敌英雄或kind1敌城候选（不仅是模型没选），10872次选探索。最后一次模型决策为day1305，原生随后仍推进到day1938；之后633回合只有回合/招募事件、没有移动决策。日志有10905次“That hero is not visible!”、634次“no target for hero”、0次external policy failed。末尾英雄仍有1560移动力、数千兵和大量资源。该证据把下一步优先级指向可见对象信息读取/敌方目标构造/路径可达与无目标退出，而不是简单加训练时长或GPU并发。尚不能仅凭日志把所有缺目标归于单一根因；应核对getHeroInfo/getTownInfo参数含义、引擎可见性、候选过滤与真实路径，禁止以读隐藏状态替代修复。

## 3. 环境和关键路径

Windows工作区 `G:\Heroes3-AI-Lab`；WSL发行版 Ubuntu-22.04，root；共享盘 `/mnt/g/Heroes3-AI-Lab`；主Linux目录 `/root/heroes3-ai-lab`。

- CPU Python：`/root/heroes3-ai-lab/venv/bin/python`。
- GPU Python：`/root/heroes3-ai-lab/gpu-venv/bin/python`，Torch2.10.0+cu128，RTX5070Ti16GB。机器32GB内存，WSL约16GB+4GBswap，i7-14700KF28逻辑线程。
- 共享模拟池锁 `/root/heroes3-ai-lab/evaluations/.pool-lock`。PPO还独占GPU学习器锁，详查脚本；不可多个学习器同时抢GPU。
- 隔离战略源 `/root/heroes3-ai-lab/src/vcmi-adv`，构建 `/root/heroes3-ai-lab/src/vcmi-adv-build`，ENABLE_ML=OFF。
- 原冻结战斗构建 `/root/heroes3-ai-lab/src/gym/vcmi/rel/bin`，严禁就地改动。
- 事件运行时 `/root/heroes3-ai-lab-events-v2`，保留已有隔离补丁和原始轨迹。

PowerShell嵌套WSL引号易把包含管道的regex拆成shell命令。复杂任务优先写脚本再调用，勿反复内联复杂转义。WSL代理提示不是训练错误。Linux无rg时用grep；Windows有rg。运行中的SHA冻结源码/模型/二进制不要热修改，先结束本轮并记录再出新协议/目录。不得覆盖旧评估或粗暴杀全部python/WSL。

## 4. 战略工程现状

主要源码 `experiments/adv-ai/CDirectorAI.cpp/.h`。安装 `experiments/adv-install-ai.py`，隔离编译 `ninja -C /root/heroes3-ai-lab/src/vcmi-adv-build -j 6 vcmiclient vcmiserver`。修改前先看对应源码，不机械照抄旧推测。

已修并实测：

1. initBattleInterface/cbc空指针，真实战斗回调接入；原生Nullkiller2路径保留。
2. 仅用引擎可见对象枚举；敌军粗略兵力用原生可见信息估计，不偷读隐藏兵数。
3. 引擎Pathfinder真实单步路径；visitable位置转实际位置偏移；请求ACK/战斗/查询调度；无进展检测和每回合动作上限。
4. 合法建造、招募、逐兵组调拨、无英雄时重招；这些目前是脚本经济，不是学出的经济策略。
5. yes/no访问和交战对话应答1，旧版总答0会取消；此问题已修，最新超时另查。
6. 自有资源/军队/城镇变化与候选动作可审计轨迹；通过唯一request/action文件实现本地模型选合法战略目标。
7. 真实存档加载恢复：修隔离客户端testsave退出和无真人颜色的错误setPlayer；原局与恢复局同种子同结果、134次移动和57条自有状态记录完全一致。只验证回合起点，不声称任意动作中断可恢复。

主runner `experiments/adventure_runner_v5.py`：唯一目录，计划与源码/二进制SHA，角色分配回读，超时/崩溃/缺终局/变更输入拒绝，原生winner为准；save-file/gdb/agent-dir支持。注意：外层被杀时嵌套新session子进程清理还需加固；EmptyAI对手的turns字段可能null（应从原生日期轨迹补，不伪造）；尚无原生最大游戏天数，不能只靠90秒墙钟把循环当败局。

`experiments/adventure-takeover-v5/` 重要证据：

- TAKEOVER_PLAN.md：总接管方向。
- ECONOMY_RESTORE_AUDIT.json、ECONOMY_RESTORED_STATE_AUDIT.json、save_restore_audit.md：资源变化、招募/调拨守恒与恢复实测。
- development-01：旧脚本策略18局开发基准，17正常1堆损坏崩溃；Director11个有效对局全败，另1局invalid，不得算12负。
- HEAP_FAILURE_DIAGNOSIS.md/HEAP_FAILURE_LOG_AUDIT.json/heap_abort.gdb：崩溃未定因，同种子后续两次完整正常，不能归罪上游也不能宣布修复。

fixtures是3张36×36工程开发图；fixtures-v2有预分割train/dev/test各2张，已安装Maps/adv目录。训练图为 `takeover-v2-train-01-mines` 和 `takeover-v2-train-02-development`，实际完整加载过。dev为river/reserves，test亦river/reserves但不同固定地图；截至交接v2 dev/test未运行。旧72×72竞技场不能当探索经济强度证明。地图英雄特长/首动可能不完全对称，必须双角色、多图多种子、原生对照。

## 5. 战略模型与PPO

目录 `experiments/strategic-policy-v1/`：README.md、encoder.py、model.py、broker.py、smoke_game.py、train_ppo_pilot.py、CPU_SELFCHECK_v2.json。

合法可见候选请求schema strategy-candidates-v2。11个state和15个candidate特征，6类目标；模型 PriorCandidateActorCritic 64维，固定正启发式prior+可训练残差actor及critic。初始残差最后层零，使argmax等于启发式；不叫专家预训练。value未校准，不是胜率。初始 `checkpoints/prior-initial-v2.pt` SHA 8dd2cc8eeb09c2e83421fd0ec6c2958ba64716580e2dac74086bbb8d92f7e5d3。

CPU回放和真实broker闭环证明合法mask/请求消费；同seed启发式和初始prior完整轨迹一致。战略战斗仍委托原生BattleAI，并未把B64战斗模型嵌入整局，也没有神经网络决策经济/主动英雄魔法。

当前PPO：CUDA推理和反向，单环境，4局/update（EmptyAI双角色、NK双角色），交替两训练图；完整终局+1/-1、gamma1，无额外奖励塑形；PPO4epoch/minibatch64/lr3e-4/clip.2/entropy.005/KL门禁；逐transition均匀采样，分别报告局长，不能当独立游戏数。原生逐动作ACK与所选候选严格对齐，invalid整局剔除并停止本轮。代码/地图/模型/二进制SHA检查和源码快照。权重、优化器、Python/Torch CPU/CUDA RNG已写checkpoint；--resume边界功能已实现，但尚未实测。

最新入口：
`wsl -d Ubuntu-22.04 -- /root/heroes3-ai-lab/gpu-venv/bin/python /mnt/g/Heroes3-AI-Lab/experiments/strategic-policy-v1/train_ppo_pilot.py --help`

不要直接用旧out再跑。改协议或修代码后用新目录；现有resume会校验冻结协议，改动后需明确迁移而不是伪装同协议恢复。

`G:\Heroes3-AI-Lab\STRATEGIC_PPO_REVIEW.md` 是最新独立只读审查，另见 events-v3/STRATEGIC_PPO_READONLY_EVIDENCE.json。CPU实核旧failed轮594条logp与native消费一致，padding概率0，update0与初始完全相同。审查区分了旧快照缺陷和当前树已见修复，不要把旧问题直接当现状。

还需：每次更新分别记录actor/critic相对上次的变化，真实optimizer步数（异常后也如实记录）、恢复文件SHA和一致性、原子checkpoint、CPU preflight不要恢复CUDA RNG、实际边界恢复对照。不能用changed_tensors累计值或loss降低宣布变强。

## 6. 人类战术支线最新事实

先读 `experiments/human-tactics-events-v3/RESULTS.md`、CURRICULUM_RESULTS.md、DELIVERY_AUDIT.json、DATA_QUALITY_WITHDRAWAL.json、SEARCH_INTERFACE_AUDIT.md。

- 本轮75个真实完整战斗1797steps，0非法0截断；原生事件时序、动作前后归属和稳定单位ID修复。有限反击与皇家狮鹫无限反击例外可由真实事件复现。
- 旧events-v2日志452局最后批事件丢失不能伪造；旧62 Q3示范认证已撤销，143 Q2待复核，当前BC可用样本0。
- WAIT→诱饵→主力三版课程均未证明总体提升，有些局机制发生却把先手让给敌方导致更差。不认证、不直接喂BC/PPO。
- BattleAI turns=2/4/10不是minimax深度；试点扩大交换队列反而更差。
- 编译接口没有clone/save/load。CGameState memory save排除当前battle，不能当战斗克隆。HypotheticBattle只是近似，可研究独立公平搜索适配，但需验证。
- 同seed前缀重放分支试验已成功，改变合法WAIT后真实后续分叉；这是离线机制探针，不是允许上线偷看真实未来随机数的搜索。
- 真实公开文本来源目录 `experiments/adventure-takeover-v5/expert-source-retaliation.json/.md`。多来源含中文攻略、RPGClassics、Reddit；作者身份/版本未知明确标注。没有完成视频动作提取或获得完整高手轨迹，不可声称已经大规模学高手。

尊重平台访问限制和版权，不绕限制批量下载。人类技巧记录应含来源/版本/适用条件/操作/机制/反制/失败条件/置信度，先做10–20候选再认证少量高质量案例。战略兵链/经济/飞跳回独立归档，主动英雄魔法当前v15不支持。零有效专家时不要堆混合PPO假装课程已成功。

## 7. 冻结战斗成果与不可篡改证据

B64最佳局部战斗权重 `/root/heroes3-ai-lab/models/graph-finetune/1792068859379237126/update-64.pt`，SHA 1e022707186a3c0dad7c671233b100930e870fff6c79cc703fb5b89dfb192936。

192局开发集B64 vsBattleAI172/192=89.58%，vs作者114/192=59.38%；BattleAI20败=攻7守13，不是守16。mixed16无提升，mixed32退步。公开模型BattleAI157/192。两个固定模型胜局并集180/192只是事后oracle，不是新模型/蒸馏理论上限。正式512局另有不同分布，不能混报开发成绩。confirmation-v2独立32图尚未用于当前新候选，不要调参反复看独立测试。

冻结校验脚本 `experiments/adv-verify-frozen.sh`，接管期间最近已五项通过；新窗口应重验：

```
libvcmi.so bd50e62ccee1c1e22af4d3bb0f18d6dc1fbc80c5bc0f601489cc3662e34b4441
libmlserverplugin.so d2d1e26c31cb371c53b52a5d4dfdac8f09d329391a8eacbc29ec8df833b458fa
vcmiserver 26ab58b469584dfd58f5ce2fe3502503409962f6c928c59ad7c63d46c8999a05
vcmiclient 8c820049b5f220e19b0f41dc21cb28b15f1114ecc8cf1e0839fff580e32541ab
libmlclient.so cc8aaea44afd80016f11f8be9404edcea63d109345f6345a0504e60fca1722ae
```

原冻结战斗环境与历史失败模型/轨迹/源码快照均保留；原主目录并非全面零修改（有隔离战略构建和新workers），准确表述是原冻结战斗文件未改。

## 8. 建议接管顺序（允许依据实测调整）

1. 读取本文件、最新training.json、PPO复核和战略源码关键段；get_goal检查新窗口状态，无活动goal则create_goal，存在则续做。核对进程、资源锁、GPU、磁盘及冻结SHA。不必重读几百万token历史。
2. 优先诊断pilot02第三轮11823步超时：读取目标/日期/位置/资源循环，确认为什么对只结束回合的EmptyAI都不能及时结束。把功能缺陷、策略弱点和超时门禁分开；针对性改法出新版本，不把任意“卡住就赢/输”当正确终局。不热改运行代码。
3. 加固checkpoint/真实step/恢复/actor-critic审计和进程清理。用旧update2做只读加载与轨迹评估；同协议才能声称原样恢复，改协议必须明确迁移。实测完整训练→保存→加载→边界续训。
4. 稳定后冻结候选，在v2开发图双角色做initial-prior vs learned同图同种子配对，留最终测试不碰。训练胜EmptyAI不证明战胜NK；当前对NK全败。根据失败调整目标/奖励/候选策略，不是机械加迭代。
5. 战术支线继续寻找有独立收益的专家/反制案例或公平近似搜索接口，保持无效标签隔离。两线资源有锁，独立只读/文档可并行，不并行GPU学习器。
6. 小样本验证后再测环境吞吐和内存，逐步并行、批量CUDA推理。不得把CPU游戏模拟声称搬进GPU，也不得为了提高GPU占用盲目开24/48。
7. 持续落盘CURRENT_PROGRESS/交接/可复现实验；报告区分接口、训练、开发、独立测试。功能跑通、两次梯度更新或单图胜利不足以完成goal。需要外部输入时明确真实缺口，不假装已视频理解。

用户希望你持续把事情做完，遇到失败应检查、调整、继续，而不是只发“下一步建议”。但不得用夸大数字、不公平测试或无限重复失败配方来凑完成。

## 9. 本次新接管的持续追加入口（原第1–8节保留）

最新实施状态见工作区根目录 `CURRENT_PROGRESS_20261018_TAKEOVER.md`，实际任务goal保持active。
该文件记录了：原超时11823请求精确重放、目标承诺/清怪、真实CUDA边界恢复、独立开发净提升0、真实24并发CPU模拟、v3威胁补给观测、两处查询竞态及经济建筑前置修复、仍在严格验收中的新并行训练器。

特别注意，当前隔离native已升级 `strategy-candidates-v3`，旧 `strategic-policy-v1` 工具是历史协议，不能直接向当前native启动旧broker/trainer。使用 `experiments/strategic-policy-v2/` 和 `experiments/strategic-vector-v1/` 新工具，并先查其最新实跑report状态。旧权重和失败轨迹不删除；历史门禁不足另附审计，不改写旧training.json。

新证据入口：`experiments/strategic-policy-v1/takeover-03/`、`experiments/cpu-simulator-throughput-v1/RESULTS.md`、`experiments/strategic-policy-v2-audits/`、`experiments/strategic-vector-audits/`、`experiments/strategic-economy-v4/`。经济验收和并行trainer仍可能在后续失败后出新版本，务必读当前状态而非机械接受本追加概述。
