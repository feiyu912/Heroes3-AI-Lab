# 正在进行的完整训练目标

用户授权离开期间持续研发。现有goal为active：公平验证稳定战胜公开MMAI、对BattleAI至少95%胜率的方法，保存可恢复模型和真实独立结果。预定实验完成不代表goal完成；不达标继续研究，不能伪报成功。

固定24个游戏训练进程、一个CUDA训练器。标准评测最多12并发，与正式训练串行。无新子代理。

当前：v5-diverse-heads已完成256轮；验证选择128轮作为下一阶段起点。v5-diverse-last正微调最后图层和输出头（1084450可训练参数），之后v5-diverse-all微调全图。当前实际进度/存档以research/v5-diverse-last.json和all.json为准。

控制文件research/goal-v5-control.json。最新运行PIDs/日志以research/goal-v5-recovery-status.json为准：监督器382、恢复主流水线383、续训验证等待器384（2026-10-15 21:32恢复后）；旧83186/7825/30345已退出，旧sessions不再使用。Windows隐藏finish-challenge-artifacts.ps1已重启，等待最终6项512场对战完成，限时24小时。扩展训练每阶段限时86400秒，可从真实优化器存档继续，不能重跑完成阶段覆盖证据。

GPU集中批量对手推理已通过完整公开图状态/动作/结果一致性检查（CPU和CUDA各36局，两种模式，hash版本2）。24并发两次完整性能测试均正常退出，CPU热身后70.71/79.67决策每秒，集中CUDA为112.59/128.02。计入启动摊销的16轮估算加速1.619倍；这是估算，不冒充全图训练实测。正式后续训练已自动采用BattleAI+MMAI_GPU，冻结公开对手参数独立于学习器，逐轮检查权重不变。见central-opponent-contract.json、central-opponent-cuda-contract.json、central-opponent-throughput.json。最终能力测试仍使用原生CPU作者ONNX模型。

最后图层实际自动微批量选择32已通过：不改变参数/RNG，预试仅810MiB预留；当前训练每轮约50余决策每秒，GPU总显存约2.45GiB，可用WSL内存约6GiB，CUDA_training=true。不要以低显存误判CPU训练。原生每进程ONNX CUDA方案内存门槛不通过，use_cuda=false，未采用。

A128旧验证BattleAI32/48、MMAI23/48；新开发验证BattleAI41/48、MMAI28/48。A256对应32/48、22/48、36/48、27/48。新开发集为12套镜像军队、攻守各2种子共48场；这些不是最终测试，也不能证明稳定领先。公开原模型新开发成绩BattleAI37/48、MMAI24/48。

选择规则于A128结果之后、B/C训练及最终测试之前调整并披露：最大化旧/新开发集四项相对目标进度的最弱项（BattleAI胜率/.95、对MMAI按场景聚类95%置信下界/.50），再按BattleAI总成绩、MMAI下界、总成绩和伤亡打破平局。见goal-selection-plan.json、goal_selection.py。最终成功门槛不变：独立BattleAI至少95%，对MMAI场景聚类95%下界严格超过50%。

192套多样化训练地图，48套开发地图中目前12套用于验证；独立32套512场最终测试不参与训练或选择。全部范围仅普通3队战斗，未覆盖主动英雄魔法、攻城、大地图及完整1打7游戏。不能声称整个主指令所有系统均已实现。

持久化：checkpoint原子替换/fsync，报告只引用已保存存档；goal_training_recovery.py校验ZIP CRC、恢复优化器和RNG、保留跨尝试的历史。每轮记录GPU、内存、时间与重算误差。恢复图模型log概率重算绝对容差2e-4，经过真实CUDA批量误差校验。旧96轮后故障与14轮未保存工作已归档，不冒充保留进度。

ONNX导出支持图层/全图权重和独立别名，finetuned-export-contract.json的所有参数扰动测试已通过。新verify-selected-native-export.py用于选定真实权重的数值+6局原生兼容验证，尚待运行；兼容验证只使用训练场景，不是强度评估。最终还需实际检查报告图片、最终SHA和恢复入口。

后续：持续监督B/C及最终测试；若不达标，依据失败对局改方法，保持goal active。不得为节省时间将目标标记complete。正式独立测试如已看过，后续改模型须使用新的冻结后确认集，旧测试降为诊断。

补充：A128真实候选的原生ONNX导出已完成6局兼容验证，逐决策Torch/ONNX概率和值相符、贪心动作完全相同、全部正常结束，最大概率误差约1.35e-5；见models/goal-v5-native-candidate-a128/manifest.json。这是候选兼容性，最终选定模型须重跑验证。最后图层update32完整优化器/RNG存档已校验CRC、有限参数与SHA，并复制到Windows models/goal-v5-recovery。

2026-10-15补充：新工具analyze-development-errors.py、propose-role-portfolio.py已读取验证集生成逐组合/角色诊断和组合提案，不读取最终测试。A256攻击+A128防守估计新开发BattleAI42/48、MMAI30/48，尚未真正组合权重或实战，不可当成绩。必须在B/C验证后重算。verify-live-training-resume.py/session55168等待C完成且GPU训练器全部退出，获得评测池锁后运行一次真实24并发CUDA续训，核验优化器步数/RNG/参数更新，试验权重排除选择。当前仅waiting，尚未passed。已补gamma/GAE/全图entropy可选入口及RUN_TRAINING转发，默认训练行为不变；finite-win-objective-contract.json数学检查通过，gamma1/stepcost0尚未训练。未来方法依据见research/goal-v6-method-notes.md。

重要数值故障已修复（第115轮更新前）：完整图网络GPU scatter求和非确定性，加上采样24/更新32的批量形状不同，触发0.00024414大于2e-4的检查。未采用放宽容差：train-graph-finetune现在启用确定性CUDA（CUBLAS_WORKSPACE_CONFIG=:4096:8），PPO预检查按原采样24批量重算，更新微批量仍32，绝对阈值仍2e-4。full-graph-cuda-recompute-contract.json：64个不同真实训练观测×双模型角色，三次同24批量重复误差为0，跨批量差异仍记录；全图梯度通过。central-opponent-cuda-deterministic-contract.json的36局完整状态/动作/结局全部一致通过。已归档失败控制/进度/日志及114轮报告，从完整112轮优化器和RNG继续剩余16轮，113/114两轮未保存工作明确丢弃。第112轮权重也已备份Windows。recover-goal-supervisors.py只恢复监督器及失败阶段，保留原3成功阶段、A256、A128/A256全部验证。新PID详见recovery-status。原live-training-resume等待器因主阶段failed按设计退出（并非实际续训测试失败），已归档该状态并重启384；仍未通过真实续训探针，待C完成后自动执行。

恢复实测：新训练器PID413从112已继续到116，CUDA_training=true，逐次重算误差0、recompute_batch_size24，无截断。确定性scatter有性能代价，目前约27决策/秒，早期约50余为不同数值模式，不能混称同一次完整速度。最终报告脚本已修正原GPU原型未采用的过时表述、统一目标选择规则，并披露故障、两轮未保存丢弃及确定性计算的代价。若后续优化速度，应保留确定性采样/更新前同批量检查及原阈值，不得以跳过数值校验换速度。

最新阶段（2026-10-15晚）：最后图层B128已完成。B64四项48场成绩：旧BattleAI32、旧作者23、新BattleAI44、新作者33；B128为36、25、40、35。B64新开发91.67%/68.75%，B128为83.33%/72.92%，不能把两者最好成绩拼成同一模型。completed-graph-recovery-contract.json已离线核验实际112到128的16轮CUDA恢复，优化器各参数步数均增加768，环境采样增加12288、16轮重算误差全部0、RNG载荷有效，原112存档与Windows备份SHA一致。B128也已备份Windows。

当前全图C训练PID16075，24并发、8993178可训练参数，microbatch16容量检查2016MiB通过，重算0，约15.6决策/秒，尚未验证能力。监督器382/主流水线383/续训探针等待384仍在。为补做真正针对B64/B128取舍的方法对照，post-training-candidates.py/session19389正在等待C全部验证完成：它有意SIGSTOP最终选择器PID385（ps的T是预期，不是任务暂停/崩溃），不暂停C训练，也不启动额外环境。此辅助步骤完成前不能手动释放385或开始新最终测试。计划见post-training-candidates-plan.json、状态见post-training-candidates-control.json。它将以原规则选择更好的角色组合（如有）及三种固定权重插值，在标准12并发池逐一真实验证、为选定模型执行6局训练场景原生ONNX验证，然后写入最终选择并SIGCONT385。若失败会保留错误、使流水线失败而不发布部分结果，需要修复并恢复，不能跳过。

新derived_models.py已实际生成B64攻击/B128防守及50%权重插值两个候选，并校验有限参数和保存重载，见models/derived-candidates；尚未对战，不能宣称胜率。后续辅助步骤的donor会按C结束后的验证结果选取，固定alpha.25/.5/.75，完全排除最终测试。Model Soups原论文只作为方法动机，不宣称已有RL强度保证。组合存档没有虚构优化器历史：finetuning_mode=derived、continuation_mode=all、resume_available=false；save-challenge-model.py已支持此类模型新优化器继续全图训练，全部父存档优化器另保留。最终报告与runtime快照已同步披露这些方法及选定ONNX的真实验证条件。

当前更新：C已到25/128、所有重算误差0、无截断，首个全图16轮完整优化器存档已校验并复制Windows。post-training候选等待器原session19389/PID17098在等待状态有意替换以加载最终冻结备份步骤（SIGTERM没有中断训练）；最新为session88247/PID18081，selector385仍按计划T，不能当作崩溃重启。它在候选真实验证和原生导出之后会调用final_policy_freeze.save：把选定checkpoint原始字节复制到Windows models/goal-final-freeze/policy.pt，并写final-policy-freeze.json绑定SHA、验证文件SHA和选择信息，再释放385开始最终测试。run-fresh-challenge-evaluation.py在每项对战开始前核对源模型与冻结备份SHA。任何freeze已存在后的失败，禁止用recover-goal-supervisors.py重跑模型选择，应保持冻结选择只恢复失败的最终阶段；此约束已有代码门槛，防止把看过的测试重新用于选模型。

本轮新增中期验证等待器：run-mid-training-validation.py已参数化，session60783正在等待C64（v5-all-midpoint-status.json，实际确认训练PID16075），存档到位后使用额外1个CPU评测worker完成四项48场验证，不读取最终结果，24训练worker继续；标准评测池锁防止双评测池，启动时要求WSL可用内存大于4GiB，当前约6GiB。其输出名与正式C64验证一致，正式阶段会复用已有完成报告。

公平配置实查已完成：audit-neutral-mirror-fixtures.py/neutral-mirror-fixtures-audit.json检查实际272张diverse及holdout地图和活动Mods/ML/Content/heroes.json。4个ML英雄同职业、无特长/预设技能/装备/法术，map中四项主属性0、经验0、技能空，双方军队及槽位相同。没有读取最终胜负。确认原生v15 constants.h MAX_ROUNDS=30，ENABLE_ML的BAI在超限时撤退；训练worker拒绝非NORMAL结束，最终success也排除非正常结束与截断，因此不会把超限撤退当作正常获胜。最终报告补充此边界。

评测freeze实际原先仅包含Python/模型/地图，现已补实际libvcmi.so、libmlclient.so、libmlserverplugin.so、connector_v15.so、exporter_v15.so、CPU libonnxruntime.so及ML heroes.json。evaluation-provenance-runtime-contract.json在一个开发场景上实测22个文件freeze/verify通过。未来C64及最终评测采用新冻结集，旧A/B报告保留当时较小清单，不伪称历史已包含新文件。评测核心输出/规则无变化，Native库与模组本身未改。

最新覆盖说明（优先于上文旧进度）：C全图已完成95/128轮，CUDA_training=true、24并发，累计3025局、1次截断，重算误差仍0。中期C64四项48场验证均正常完成：旧BattleAI35、旧MMAI26、新BattleAI45（93.75%）、新MMAI26（54.17%）。不能与B64的新MMAI33/48拼成同一模型；全图训练出现对作者成绩回退的迹象。1344场历史验证原始结束标志/胜负/存活兵力审计通过，见validation-win-semantics-audit.json。

选择规则现为v2，见goal-selection-mirror-alignment.json及goal_selection.py：旧20..25的6套场景中4套兵量不对称，降为压力诊断；主要按新镜像开发集BattleAI95%与MMAI场景聚类95%下界严格超过50%的共同达标程度选择，达标后优先更高BattleAI胜率。最终独立32套512场、最终成功门槛均未更改且尚未读取最终成绩。监督器内存中仍是v1；post-training-candidates会在正式最终冻结前按v2重新选择，不能跳过。

当前辅助任务：post-training-candidates PID23302/session96021等待C完成，最终选择器385仍有意SIGSTOP；真实续训验证等待器现为PID26443/session6864，旧384已替换；中期验证18184/session60783已完成。上述为本次记录，继续操作需核验实际进程状态，不能以旧PID判断崩溃。

用户询问人类战术：当前正式A/B/C是公开作者预训练图模型上的PPO，依赖正常胜负、兵力价值势函数及步数成本；没有接入用户录像、人工战术动作标签或专门的保护射手/骗反击/等待课程。合法动作概率采样是探索，不是均匀乱走；验证使用贪心动作并换角色/固定种子。已从实际v15环境确认VIPBot可作为对手，原生VIPBot.cpp含护卫移动逻辑，但当前对手只有BattleAI和冻结MMAI_GPU，尚未加入VIPBot，不能声称已学会护射手战术。后续专项必须用行为证据和实战验证；拆分兵队不在当前战斗动作空间，英雄魔法仍关闭。

本次实际新增进展：make-tactical-curriculum.py生成并重读验证120张四队镜像地图（三类：护射手、少量兵反击诱饵、分队集火），96训练/24开发；mixed-tactical-curriculum.json共288训练地图。当前正式训练未使用新课程，也没有专家动作标签。1个额外CPU评测worker已完成三张训练地图交换攻守的6局VIPBot兼容实战，4胜、0截断、0非正常结束、0非法动作，见tactical-vip-smoke.json；仅证明新地图/4队模型/VIPBot能运行，不是独立胜率证据，不加入v5模型选择。协议见goal-v6-method-notes.md。新课程没有读取最终地图或成绩。C96完整模型/优化器/RNG已校验并备份models/goal-v5-recovery，SHA423ba26a640985ec36ac1c6f6da090c78b7bf1fdc8e423b3d57aff5fcd739ab3。

战术观测记录已实际实现并验证：trace-tactical-battle.py在全局评测锁下只运行1个CPU环境，限制训练地图并检查4GiB余量，保存每个学习器行动时的完整图、合法动作、选择动作关系、解码单位与终局，源文件/模型/原生环境SHA冻结核对。B64在tactical-expendable-retaliation-00攻击BattleAI的一局28个决策正常获胜，重复两次完整记录完全相同，见tactical-traces/b64-retaliation-attacker-v2.jsonl.gz、对应manifest及tactical-trace-review.json；4次WAIT/4次SHOOT等仅行为事实，不证明已学会骗反击。单位索引逐观测局部，当前图无持久单位ID或明确反击次数；两观测之间含对方动作，不能用状态差冒充只由我方动作导致。原生render尝试异常退出已改为纯观测记录；原生shutdown可能终止Python进程，因此先原子保存/重读校验manifest再关闭。没有改原生库或正式训练。

最新用户范围扩展：已收到Human Tactics Curriculum完整指令附件916aa86a-d446-4ddd-80f3-e4dba044b521/Pasted text.txt，要求前三专项龙喷吐/单兵骗反击/尸巫云、知识库/专家/示范/短程BC+PPO/独立测试与六份文档；随后明确授权子智能体研究真实高手来源（阿青优先但多作者）、15左右候选，并至少一个真实文字/轨迹案例完成规则重建→专家→学习→独立测试。保持原>=95% BattleAI/稳定胜作者goal不变，新增工作不替代原目标。用户明确保护当前128轮，未改其参数或协议。

C128已全部完成并校验备份Windows（SHA6168c281abf6374f426b7d3462c4a9d406cc4355c92c5577d9eb2d0e49e37334）。真实24并发CUDA恢复128→129已passed（live-training-resume-contract.json）：每参数优化器步数+96、样本+768、RNG/参数改变、0截断、全部worker0退出；129探针排除模型选择。C128新镜像开发BattleAI39/48、作者30/48，退步不默认采用。post-training候选仍按v2运行，已实战role组合45/48 BattleAI、32/48作者，25%插值43/48、30/48，剩余插值/最终冻结未结束；具体以实时文件为准。

隔离专项目录experiments/human-tactics-v1：编码前INTERFACE_AUDIT.md已核对固定源码，IsMeleedBy/IsShotBy确含主动龙/尸巫额外目标，含友伤及death-cloud免疫过滤。generate_scenarios.py已实测24地图（12train/6dev/6test）首3专项，实际随机兵量/槽位/阵型与攻守，不是任意坐标/朝向。coverage-value-v1专家只做可见相对价值覆盖代理、原生BattleEvaluator depth2 fallback，不是最优专家或已认证骗反击/反制。安全算术单测通过，首局龙expert scenario0 attacker seed2026102801实际15决策正常获胜，1个多敌机会并选1次多目标攻击；最初outcome int keys误用string造成失败已保留，run_episode.py已JSON标准化后v2成功。

Human专项 run_pilot.py/session17802 正在与原流水线共享全局池锁串行收集12专家+12 B64训练场景对照，接着固定60步CUDA policy-head BC（新优化器，图/价值头冻结）、冻结模型后测试6新场景×双角色，每模型12局。尚未完成，不当成果。BC只过滤正常赢局的Q2候选，不是已认证强专家。agent只读发现后续复用门槛/样本manifest偏弱、无结算时战损0问题：当前首次试验需独立检查所有已完成文件、如截断存在则不能用有偏战损均值。不要在run_episode.py冻结期间编辑任何human目录已有Python，否则会触发SHA校验；新增模块也要写完后再开下一局。原生shutdown可能exit0，因此必须查看completed报告而不只看进程returncode。

用户已明确允许子代理。/root/expert_sources完成experiments/expert-knowledge-v1的11来源registry、15候选pilots、SOURCES_AND_PILOTS.md、可重建目录脚本、source_case.json（Hallas龙反击友伤）与source_wait_case.json（Hallas等待跨轮窗口）。阿青等B站只得标题/章节，HTTP412未绕过；YouTube/Twitch仅外壳；没有真实视频理解/字幕或人类原操作轨迹。Hallas2001-08-27 Complete原创攻略公开文字已实际读，职业身份未核验；所有实验坐标/数量为重建，不能说从视频提取。sourcecase原17词短引文，同源不再追加长引文。

重要：v5最终候选现已冻结并开始测试，禁止再改选择。选定v6-role-portfolio（攻C64+守B64，以derivation manifest为准），SHA14f5c4fca8c804c125eebabeb06a8483a137653ea54594321e9ca60cbb9cbb2e；Windows goal-final-freeze备份相同，原生ONNX 6局兼容检查passed。独立BattleAI已出512局：选定434胜=84.765625%，公开原模型457胜=89.2578125%，旧v3 214胜=41.796875%。都0截断/0非法/0非正常；diagnose-frozen-final.py对两份原始1024局终局/剩余军队审计通过。原目标>=95%明确未达，不能mark complete；其余作者对战/6项汇总仍在原管线继续。未来改模型必须新独立确认集，本512仍是v5有效最终结果，但改进时只能当诊断，不能重新选模型后重复宣称独立。

frozen-final-diagnostics.json：选定比公开原模型少23胜，攻方219vs220几乎持平，守方215vs237回退22；monk/pegasus/pikeman组合37vs58贡献21净回退，archer/griffin/pikeman52vs62也下降，archer/dendroidGuard/griffin62vs52上升。不能只扩大训练量或继续用12小开发军队挑模型，后续宜扩大开发场景并保留原公开策略约束，是否实际有效需新实测。

真实来源WAIT机制已实测：原Dread训练前4条件window_verified=true，但WAIT/noWAIT均正常赢、同损1，没有收益，绝不以此冒充可用强专家。/root/expert_sources正在wait-variant-v2/run_variants.py，session93202/PID85637，ghostDragon14 vs walkingDead3四训练参数组×攻守，首对同损1仍无收益；保留aging因果混杂，只有正常配对收益+窗口才将首步WAIT写candidate-bc-train.jsonl，不会把整条greedy轨迹标最优。另预先冻结heldout-scenarios.json dev/test各2参数组×roles，尚未读结果。v3多慢队围攻场景已预注册生成但未启动，用于与原攻略“不要提前飞入被多队围攻”条件对应，避免单堆硬拼天然反击抵消WAIT收益。根代理train_source_wait.py已写，可指定--experiment，要求两角色真实收益示范才能60步CUDA heads-only BC，冻结后独立test；尚未运行/未证明训练有效。

来源数据质量工程已实做：expert_demonstration_schema.json、validate_demonstration.py、DEMONSTRATION_INGESTION.md、test_demonstration_gate.py及demonstration-gate-check.json；5项门禁测试passed，真实v1.gz仅Q2探索可用，Q3强专家门禁拒绝，非法human动作/video_guess/未知终局均拒绝。没有真人轨迹，合成非法样例禁训练。agent audit_human_pilot.py当前已实际核验16条已完成记录全部SHA/gzip/内外字段/合法动作/胜负与兵力一致，0截断/0缺结算，partial=true；BC/test未出现。当前原生shutdown正常终局不等于干净关闭，不能凭exit0认成功；此前“shutdown必定退出解释器”只是观察推断，不是已定位原生路径，报告不应过度断言。

2026-10-16最新：原冻结候选对作者512场已完成268胜=52.34375%，0截断/0非法/0非正常；普通Wilson下界48.016%也不足50%，真正判定还要最终场景聚类CI（勿混用）。不是稳定胜作者，原goal仍未达。还有v3作者对照、teacher对照等6套汇总/Windows模型/图片/快照待原流水线完成，不能提前写goal complete。原正式测试PID131074当前已退出或将退出，后续实际进程查ps，未完成不是卡死；此前慢的MMAI512确有活跃worker/文件数递增。

新防遗忘路线已实际编码和CPU校验但尚未GPU训练：experiments/conservative-ppo-v1/reference_ppo.py、check_reference_ppo.py、cpu-math-check.json（passed）、METHOD.md。coef0与原PPO权重bitwise及共同指标相同；正KL梯度朝reference；非法padding NaN/inf不影响合法概率和梯度；独立原始观测参考编码、不复用学习器body；参考冻结/不入optimizer、候选顺序校验，重算atol不超过2e-4/rtol0且显式原采样批量。根代理prepare_trainer.py已生成隔离train_conservative_heads.py，原research训练脚本未改。共享公开fixed_opponent.pair作为冻结reference，逐原始obs独立encode并存合法log_probs/IDs，明确24批量重算；只训练policy/value heads，public body保持冻结。

conservative run_experiment.py已启动session56556，等待原冻结6套报告finalization completed后再拿全局池锁；初次BOM解析失败已保留control.before-bom-fix.json，Windows状态读取改utf-8-sig后重启（未启动任何训练）。新预先计划experiment-plan.json：public initial-pair起点、24workers、32updates、roll32、lr1e-5、reference KL.1、gamma1/stepcost0/shaping.5/entropy.005，BattleAI+原公开MMAI_GPU；这是组合方法改变，非KL单变量消融。保存16/32候选，与public baseline在全部48开发场景×双角色×2seed=192局/对手比较，最终测试仍用CPU原生作者。旧已看512只作诊断，新候选若有希望必须冻结后用新独立确认集，不重排或改旧v5结果。新控制器与source BC均遵守同一flock；已修“把等待同一锁的BC进程误判成并发GPU训练”的门槛，仍拒绝未受该锁管理的旧trainer。

Human v1/session17802已到scenario16 defender专家采集，尚未BC。原Dread session16012/PID69458在同一池锁下收集机械/无收益对照，结果未完成；source v2 session93202/PID85637仍在跑预定8训练配对，首对无收益。v2 all-source-wait-scenarios.json已另冻16张总清单（8train/4dev/4test），原train-only清单未改。/root/expert_sources已预注册v3 ghost快飞兵对多队慢兵4个训练条件，wrapper等待器session14416（continue_after_v2.py）仅在v2正常结束8对且全无收益才启动v3，避免同时扩大队列；v3未开始前不能声称训练示范有效。没有任何source高质量BC正样本时train_source_wait.py必须拒绝启动，不能降低收益门槛。

子代理/root/tactics_catalog已完成六份根目录文档及28条catalog.json，保留历史状态、明确pending。其正在只读复审Human pilot并写独立experiments/expert-knowledge-v1/audit_human_pilot.py/审计JSON，避免改运行中的Python。根代理负责experiments/expert-knowledge-v1/reconstruct_wait.py：已生成16张Hallas WAIT原理镜像角色变体地图（每侧单堆dreadKnight vs walkingDead，双方亡灵避免正士气），8个参数组train4/dev2/test2；使用现有OpponentVector双端传输控制CPU脚本慢兵（内部MMAI_GPU标签只是transport，不是GPU模型），比较WAIT与no-wait，实际记录轮次及对手行动数验证跨轮无对方插入的窗口，正常终局兵力审计。训练组正在session16012等待/运行，尚无结果时不得声明已复现。后续须依据真实配对收益筛示范，再BC+独立测试；龙反击友伤事件级认证仍pending。所有专项与原v5最终512场测试/模型选择完全隔离。

2026-10-16 00:27 事实更新（替代此前pending推断）：旧6套512总3072对战、报告/选中模型/PNG/运行快照已全部完成，Windows收尾器JSON数组计数问题修复。独立artifact审计research/challenge-delivery-audit.json passed；目标仍未达（BattleAI84.765625%、作者52.34375%且场景聚类CI跨50%）。新保守PPO真实24并发CUDA已21/32，0截断、recompute误差0、reference未变，session56556。Human原24采集全部完成718决策，原BC因空关系shape失败，原证据保留；独立v2恢复器CPU预检通过，session80201等同一资源锁，6赢局185条Q2标签。专家source v2八配对全部完成，4组局部收益筛4条首步WAIT，非人类回放且aging混杂。来源BC旧等待PID193780在训练前停止以修复测试freeze执行/源码校验，尚无模型；/root/expert_sources负责修复后root重启。graph_observation_codec.py恢复真实关系宽度，4条source混批真实模型CPU验证通过。详见experiments/EXPERT_PIPELINE_STATUS.md；不要改原Human冻结Py。两子代理已明确获用户授权。

2026-10-16 00:34：conservative实际32/32 CUDA结束，all_workers_exit_zero=true，正在全48开发评估，不能当goal成功。Human v2真实CUDA BC60step完成185样本NLL12.508869→8.337526，graph/value不变，模型bde72571e0555a41c0696e17179ea42a47c15e3ba7170e3e1be612e92f32f4d4，session80201在24局heldout。sourceBC首个CUDA session56930因inference reference反传失败before checkpoint，失败JSON保留；expert_sources修no_grad并真实B64/4样本CPU两轮backward通过（NLL9.84385→9.62377），7类门禁再通过，重启session26867 pid206353 queued且源码冻结。sourcecontrol字段status不是state，retention当前读state，已记录此兼容缺口，不改运行中冻结controller；root必须监控source若失败防retention空等。新retention576开发对照session26861已启动，B64-BattleAI96局84胜，后续正在MMAI等待共享锁。
用户新增参考支线codex://threads/01a14038-9268-7ff0-989d-ce1cafe46b35，已搜索当前可用工具没有read_thread后读用户指定本地session；支线在G:/Heroes3-AI-Lab-worktrees/human-expert-learning-v1，commit5e3a7152d。已读RESULTS/README和git记录，clean。支线63脚本标签40CPU BC，独立8条件4/8→4/8、平均阵亡87.875→93.125，普通2/4→2/4；21局401转移，真人0，逐步回放与PPO专家smoke已有实现。不可采纳该失败模型为提高成果。两子代理现只读核对支线ppo_adapter/curriculum/opponents与原始证据，分别产BRANCH_INTEGRATION_REVIEW.md及SIDEBRANCH_EVIDENCE_AUDIT.md/JSON，不启动任何额外训练/游戏，不改当前冻结源码。优先复用可靠采集/回放/课程接口避免重复研发，actualdamage事件/GUI真人/强反制仍待做。

用户2026-10-16明确要求先结束之后继续：所有本聊天训练/评估worker已停止，goal应paused且不得自动重开。混合训练7更新未到16保存点，只有日志，实际模型仍B64；恢复须新输出从B64重启。完整成果/恢复注意事项见PAUSED_HANDOFF_20261016.md和experiments/expert-mixed-b64-run-v1/paused-state.json。

2026-10-17 23:15 恢复执行（WorkBuddy，用户授权继续）：goal 重新 active。用新计划 `experiments/expert-mixed-ppo-v1/b64-anchor-plan-v2.json`（plan_sha256 `0b51ff49e7dc32203a5362f83c99a024a9ce74be235e0f86931ec2d980223ff1`，与 v1 协议逐位相同）从 B64 重跑，编排为新脚本 `experiments/run-mixed-v2.py`、新输出目录 `experiments/expert-mixed-b64-run-v2/`。训练 32/32 完成、CUDA、24 worker 全部正常退出、resumed_from_update=0；检查点 update-16 SHA `326d0721…aba633`、update-32 SHA `4eb5fa7a…bbe65a`。首次启动被 WSL 客户端回收中断于第 1 次更新，该产物已归档为 `training.killed-after-update1.json`。

开发集 48 场景×双角色×双种子：B64 对 BattleAI 172/192=89.58%、mixed-16 同 172、mixed-32 164；对作者 114/113/109。**新方法无效，32 更新退步**，目标未达，差 11 胜。参照：公开原模型同条件对 BattleAI 仅 157/192，B64 已强于公开原模型。

关键核算：B64 的 20 场败局中 12 场连公开原模型也输，只有 8 场可由模仿公开模型挽回，因此蒸馏上限 180/192=93.75% < 95%。必须靠更强策略本身。败局高度集中：20 场中 16 场是「守方×射手+飞行兵」（67/80=83.8%），与冻结 512 场中 monk/pegasus/pikeman 净回退 21 胜一致。48 个开发场景中 38 个是角色决定胜负，必须用场景聚类区间。完整报告 `experiments/EXPERT_MIXED_V2_RESULTS.md`。`confirmation-v2` 仍未运行。

2026-10-17 23:55 优先级变更（用户）：完整对局战略层优先，普通战斗95%降为局部诊断目标，不再是战略层门槛。v2 无效配置不再延长到128更新。大地图接口审计见 `experiments/STRATEGIC_LAYER_AUDIT.md`。

实测：vcmi-gym v15 无大地图接口；VCMI 原生 `vcmiclient --headless --testmap Maps/<name> --ai A --ai B` 可跑无头 AI 对局；战略 AI 仅 Nullkiller2/EmptyAI；535 张 .vmap 全为战斗夹具且用 ml 英雄。`make-adv-map.py` 已派生 core 英雄地图 `Maps/adv/adv-arena-01.vmap`，实测通过完整加载与校验并到达 `Gamestate initialized!`（M0 达成）。

硬阻塞（M1 未达成）：`server/CGameHandler.cpp:613` 无条件构造 `ML::ServerPlugin(..., si->mlconfig)`，ML 配置走 StartInfo 而非 settings.json，故改 settings/schema/停用模组均无效；默认 mlconfig 下 `InitStats` 抛 "Cannot track stats when randomHeroes is disabled"，即使绕过，`heropools.at(0)` 在普通冒险地图上仍越界。`rel/` 为活构建目录，就地重建会连带重建 libvcmi.so 与 libmlserverplugin.so，破坏已冻结的 3072 场正式评估 provenance，故不可就地重建。解锁需 `ENABLE_ML=OFF` 独立构建（方案B）或隔离构建+完整条件补丁（方案A）。

未完成：任何战略层策略代码、整局轨迹、与 NKAI 的同图对照；主动英雄魔法、兵链、经济、飞跳回仍未开始。confirmation-v2 仍未运行。

2026-10-18 00:57 方案B 执行完成（隔离 ENABLE_ML=OFF 构建），冻结战斗环境 5/5 SHA 全程未变。源码副本 src/vcmi-adv、构建 src/vcmi-adv-build、cmake 3.31.10、-j8；新 vcmiserver 无 libmlserverplugin 依赖。隔离副本必修三处：BattleProcessor.cpp 的 mlplugin 未加 ML 宏保护（编译失败）；Client.cpp::initMapHandler 在无头且非 ML 时不创建 CMapHandler（导致 Invalid access to GameInstance::map）；--ai 是死参数，改为 LAB_ADV_AI_<slot> 环境变量按玩家指定 AI。

M1 已达成：Nullkiller2 vs Nullkiller2 完整对局，day 91（随机种子）/ day 21（seed 2026101801），原生胜负结算，exit=0，0 崩溃；同种子重复结果一致。M2 部分：自研 CDirectorAI 已实现、注册并被正确选中（Player red will be lead by DirectorAI），但对局在 MoveHero 后 core dump；把 endTurn 移到 heroMoved 未解决，下一步需按英雄归属过滤 heroMoved 并核 cbc 是否为 null。未验证存档/恢复；M3 轨迹、M4 基线对照未开始。报告 experiments/ADVENTURE_M1_REPORT.md。
