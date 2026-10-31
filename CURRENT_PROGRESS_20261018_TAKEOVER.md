# 当前接管进展（2026-10-18起；2026-10-20恢复训练主线）

2026-10-23 新chat入口：NEW_CHAT_HANDOFF_20261023.md。用户询问未提升原因并准备换chat，已整理已证实缺陷、决策漂移、待检验假说、真实模型停点与恢复顺序；goal仍paused。本次实查招募policy只有CPU草稿、strategic-learned-recruitment-run-v1目录不存在，不能把此前分配任务当已实现。旧live段落均属历史。未启动训练/编译；最新ps/GPU compute查询未见相关任务。

2026-10-23 用户仅要求清理WSL，未恢复研发goal。已移除三个Heroes构建目录42份可重建cmake_pch.hxx.gch及旧npm/NVIDIA/Triton缓存，并apt-get clean；实际WSL空闲增加11379351552bytes（约10.60GiB），df used151G→140G。fstrim成功，报告865.9GiB只是所有空闲extent，不冒称本次释放该大小或Windows VHDX已缩小。关键冻结程序/库和恢复模型前后SHA一致，源码/模型/eval/worker原始证据不删。之后ninja会自动重建PCH，构建可能稍慢。操作清单及验证见maintenance/wsl-cleanup-20261023/README.md和SUMMARY.json。训练仍暂停。

2026-10-20 最新用户要求暂停已执行（覆盖下文所有live/继续实施旧快照）：三子任务已中断；battle17790经仅对确切learner发SIGINT后exit1，保留控制30新增/候选27新增的最后完整模型（G副本SHA通过）。实际/proc无lab native/learner/controller、nvidia compute空，GPU/pool锁均nonblocking实取后释放。96DEV未运行，没有学习率对照最终能力结论；中断不计败局。完整停点、模型SHA、阶段成绩及未完成招募草稿见PAUSE_HANDOFF_20261020_FINAL.md。不得自行恢复，等待用户后续恢复指令；完整goal未完成。

2026-10-20 最新source增量：根实际审了catalog/recruit/free-transfer关键CPP、v2 driver/draft diff，并核原CCallback.cpp swap=1/merge=2。资格可执行源已派生strategic-learned-recruitment-native-v2：仅从保留v1稿删除init draftgate两行，其余8payload exact；manifest865988a27bc8de8f257b767ac5b10927e76da96fe974e37414fe7519f38e7830、CONTRACT1f3a9d3c0777e31787df5e8cd2a2af1614d326a04f9b0f85ac0e83c3e42d15a3、driverfcb44690e69fe7d59e1587c9d2f2706c5141efb5394484d0c79c288b48c99552。新源build_allowed=true/native_run_allowed=false（未资格），9载荷/父cap02/accepted恢复验证和默认plan通过；未编译/未native。根实际build入口是该目录build_capsule.py --out /root/heroes3-ai-lab/evaluations/strategic-learned-recruitment-capsule-01 --execute，必须等controller17790全部退出释放GPU/pool后。不要覆盖旧失败或热改v1/v2已固定input。

schema6模型草稿实际CPU04通过4旧TRAIN投影+synthetic recruit_state、无recruit时oldlogits/critic/softmax逐位相等，新recruit actor/critic/bias有非零梯度，16负例拒绝，0step/0savedmodel；这不代表真实schema6观测已资格。真实catalog捕获前traininggate保持false。机制bootstrap由multihero_supply准备：先ready再launch native，收到first真实request后核catalog，避免先等catalog的启动循环；同turn真实Build→Recruit1→Move(out)→Recruit1same→Move(return)→freeACK→End。若无相邻一步目标，则机制专用fixture最小加实际相邻pickup，使commit不挡回城；原TRAIN不改、不随机挑seed找覆盖、无阶段则未覆盖。此为0PPO/非专家/不计胜率，NN/词表不作首资格前提。

运行仍是battle17790，最近实读candidate global48/stage18、新增2304真实Adam/9216rows、累计6144，337正常终局239胜0截断；control30新增已完（3840steps），96DEV未跑，不能报新能力提升。实际运行持续，goal active。新source/encoder/资格准备是为真实学习招募增加能力，而非将完整目标缩成单英雄pilot成功；剩余全目标见GOAL_GAPS.md。

2026-10-20 recruit草稿核心只读peer review无硬阻断；尚待C++编译/机制资格。五字段native绑定及ACK后selected-stock/完整实际目的军队/7资源差额核对，失败failclosed；新mode免费转兵支持同种新招后的真实状态新fingerprint。MAX_MOVES128仍会autoEnd，0hero仍rescue失败autoEnd，所以“整turn经济可选”受这些明确工程/actor限制。根要求尽量补全其余stock-level/offerids不变断言（或独立raw审核完整before/post），未冒称当前selected-level证明全局无变化。runtime creature catalogue已按真实CCreature getIndex/getJsonKey/IHandlerBase objects API在新源导出，request带实际raw catalogSHA，未在native捕获。第一次真实资格使用CPU机制脚本selector（不需NN先有词表、0PPO/非专家），之后用真实cap关联catalog冻结初始化，杜绝全UNK替代真实物种类别和循环依赖。旧冻结训练输入不改，controller17790继续；新native draft仍禁执行。下一source contract/builddriver待threat交根review，再在battle资源释放后实际编译与资格，不以Battle95%作为战略前置。

2026-10-20 本goal续轮实测：battle control已完整global60/stage30，新增3840真实Adam/15360rows、累计7680，552正常终局399胜0截断；candidate已从同parent30完整状态开始并完成global31/stage1（新增128、累计3968），controller17790仍live，96DEV未跑。根实际读取两臂training.restoration.json核对同parent/modelDigest/pre-LR AdamDigest/四RNG恢复与3840继承计数一致，只有bodyLR control1e-6/candidate3e-6不同，结果monitor-independent-01/two-arm-restoration-01/AUDIT.json passed。这不是两臂最终能力认证，也不把两条optimizer链合并计数。

战略free-transfer证据G归档已actual session15404 exit0、二次全SHA核验：29317普通文件+108symlink、733736527bytes，清单SHA13a2f96e7f7a9bb80cef040c3361a588b092998610296320184e9e55b8cc2ef9。含cap02/accepted备份、模型Adam、TRAIN/DEV全部raw、失败与资格fixture/source/恢复证书；外部Data/Mods链接目标保留而非伪称复制整树。路径newfree-transfer-run-v1/independent-dev-01/delivery-01。

learned-recruitment native源码草稿已实际实现真实候选枚举/quantity buckets/提交五字段tuple、ACK库存/实际目的军队/七资源变化核对、新模式同种新招后的免费交兵；9父payload匹配cap02，4文件变（CPP/h、protocol追加、server只增观察日志），仍unconditional draft执行禁用/未编译。根纠正新模式经济窗：Move后也保持开放，只End关闭，避免禁脚本招募后因首Move失去整回合经济能力；旧schema5不变。完整runtime creature词表由实际注册对象API生成并在真实资格时绑定SHA，不能以全UNK输入当合格训练。economy_policy在新policy目录准备encoder/model草稿，不起完整run/PPO包；multihero_supply对native做只读peerreview，不改同文件。无英雄仍只rescue/autoEnd、多英雄未解决；GOAL_GAPS.md已显式保留这些与真正人类战术/95%本地战斗等全目标缺口，未缩小成功定义。

2026-10-20 goal续轮实测进展：session17790仍live，control已global45/stage15，新增1920真实Adam/7680rows、累计5760（历史3840分开），272正常TRAIN终局190胜0截断；candidate尚未启动，最终96DEV未跑，不能报本轮能力提升。战略16raw+5090完整CPUproposal独立实际重算pass；TRAIN2089同观察对比发现town→mine argmax10次、反向0，18个NK同时含两目标的请求town argmax10→7。pair6 q4 baseline回城后day1军2860→5114，6dd首补兵延至day4；该策略差异真实，但不证明单步胜负因果。证据在newfree-transfer-run-v1/independent-dev-01/{REPORT.md,PAIR06_EVIDENCE.json,PROBABILITY_COMPARISON.json}。全G归档agent session15404仍在逐SHA核验，未报完成。

另一个被实测撤销的假设：2089 TRAIN中288请求806build候选，同request编码row碰撞为0；Tavern候选0、Market候选96，因此没有本批“Tavern/Market等价编码”实证。原encoder确未用building/faction字段，但构造反例不是native合法性证明；不据此立即改模型。CPU观察研究在strategic-economy-observation-study-20261020/train-evidence-03。

下一战略主线已开始隔离native源码实施：strategic-learned-recruitment-native-v1（threat_design_review负责，仍draft不可执行）。目标让town recruit真实候选与建造共用经济策略循环，使用原生CCreature::maxAmount/真实库存/slot，build和recruit不立即关闭窗口，move/End关闭；新模式去旧自动招募并处理新招同种兵的免费移交。旧v2/所有运行中source不改，未编译/未GPU/未native验证，不称已学会招募。economy_policy只完成CPU观察证据和字段建议，暂不启动新policy/run，待native契约确定。goal继续active，不以这些局部进展冒称完整战略AI已完成。

2026-10-20 当前实际进程：战略free-transfer DEV42494已exit0，16局5/8→4/8，only负翻转pair6，不升级新6dd模型。pair6前4请求逐JSON相同，q4 baseline833选kind4回城、6dd选kind2矿，之后才有policy观察分歧；不能把这一步单独认作输赢因果。multih​​ero_supply独立CPU复核/归档与TRAIN行为诊断仍在做。battle续训lr对照实际session17790已启动，control首个global31更新已完成新增128步/cumulative3968（parent3840不算新增），实际恢复JSON证明model/Adam和四RNG完全恢复后才采样，native新开。controller会串行control/candidate各30额外updates，之后实际96DEV共享parent32基线；冻结11rootpy/PLAN不得热改。goal实读active，不暂停、不标完成。

2026-10-20 最新goal工具实读已为active（覆盖下面旧paused元数据限制说明），用户恢复指令已生效，未标完成。免费交兵新训练实际session26101 exit0：完整8格2089rows/41真实build/4胜4负、132实际CUDA Adam，新模型6dd26e29b55364c293d9874c36a743e4636bcd0208daf5e61042e1f8b506ea00；GPU实际恢复model/Adam/stop+buildmoment/CPU-CUDA-Python RNG及6invalid通过，audit0优化。预定samecapsule02的16DEV3800正在session42494执行，未有最终能力结论。battle新continuation的真实parent GPU恢复亦通过（4RNG含NumPy/counter3840/9invalid），两lr臂将在DEV资源释放后串行启动，旧3840步不冒称新增。

2026-10-20 免费交兵已完成真实机制资格：capsule02在隔离fixture（仅TRAIN02派生移除己方起始英雄、把其20枪兵10弓手放己方城；原地图不改）真实雇出10枪兵英雄→首ACK后英雄30枪兵/城10弓手→次ACK后英雄30枪兵10弓手/城空，再发首次策略请求。资源不变，完整游戏及489owned-request排空严格通过，fixture48190 exit0、qualification/proof-02/QUALIFICATION.json passed。明确实际ID/player/type/server栈变更/ACK为直接观测；source/recipient/whole-stack依公开状态+编译源码唯一重建，不冒称slot/what完整payload镜像。此fixture0训练/不计胜率。此前普通TRAIN资格02游戏正常但未触发关键覆盖、proof01拒绝；首bootstrap01遗漏PLAN/原collector路径0native退出，均保留。下一固定原八格TRAIN3700/一更新，之后同capsule02的16DEV3800，预登记在新free-transfer-run-v1/PLAN.md，当前尚未新GPU更新。

战斗最终独立复核与真实归档均完成：30checkpoints/15360rows/488sourceSHA/240slots/64DEV通过，G证据包688文件5.44GB逐SHA一致。240格均至少一局（55格一局、185格至少两局），因此撤销“难格无终局反馈”假说。480固定TRAIN代表状态B64→final仅12argmax变化（2.5%），策略改动偏小但不能据此断定学习率/容量。下一新隔离continuation准备显式恢复3840-step学习器+全RNG后做相同预算controlbodylr1e-6 vs3e-6对照，不热改旧source或伪造live-native恢复；未启动这两臂。

2026-10-20 本轮最终更新：60图16并发局部战斗已完整30updates/3840实际CUDA Adam/15360rows/551正常TRAIN终局370胜0截断，final SHA dcaab92162b9c5b4cb9e5d9773067a320fe9b81fe91c1907449d4a7f8374cdaa；pipeline实际exit0。64固定DEV为BattleAI12/16→12/16、公开MMAI11/16→10/16，无收益不升级。单次每对手16局只是该固定DEV，不能替代历史192局总体统计或称达到95%。30个checkpoint有完整saved状态/readback，但本分支明确门禁not resume，不能冒称CLI续训或native环境恢复已经通过。独立CPU复核另在final-independent-01推进。

战略免费交兵修复native-v2已实际编译，capsule02构建session7821 exit0：原accepted源和三bin精确还原；manifest7404ac1b26b12faeb393d28a2a44083c003ad950cbca5b45a749948e99c59fc9，FLOW_CONTRACT32ff1ccd70f3a2e0d18b32f9772bf6b5d40a69fcc782b3104a964de0094e65c0。此为编译成功，尚待真实游戏移交守恒/首策略前ACK资格；新训练接线草稿保持fail closed，原冻结输入不变。

2026-10-20 最新实测（覆盖下面“准备中/续训中”旧快照）：战略探索链已实际完成4次更新，同一Adam累计504步（120+148+108+128），32个TRAIN完整局、8012行、130次真实策略建造（98基础/26兵营/6收入）。最终update4 SHA24b8c3f3d5ddacd61e48bd87a526c1fd59b2a83eafbdacfe44bd5ddcfb5d3e6d，GPU全状态恢复及6项负例已通过。预选最终模型16局DEV仍4/8→4/8，建造67→89不等于能力提升；无升级。完整训练/两批DEV/运行时归档delivery-01，tar SHA d3c45f1a8a79d0c25d41e3a427043df12bcbec4bf1cd92c0676fa143e96f3c62，原始证据保留。

局部战斗60图/16并发真实训练进行中：battle-diverse60-native-02截至本快照21/30更新，2688次实际CUDA Adam、10752行、380正常终局257胜0截断；这些是训练成绩，64局独立DEV尚未完成。单GPU学习器和池锁保持；native-01因根调度过早撞上未结束DEV而0更新退出，未强行抢锁，原始失败保留。

新战略失败诊断：final DEV pair03/07的新雇英雄在城内仅55/60兵力，城中仍有3318/26551部队，却先执行Move离城。首策略建造窗口跳过整个issueEconomy，同时跳过了免费驻军移交；原本same-position town也不列为Move候选。源军2/4栈，英雄仅1栈，存在空槽。正在新隔离候选修复“现成免费部队先移交再开策略窗口”，保留原招募/花费顺序和keys；未编译验证前不称修复完成。once重规划草稿暂搁置，不作为这一缺口的替代。

2026-10-20 后续实际学习主线：strategic-learned-build-exploration新建造bias按TRAIN预登记校准1.5，零梯度；随后实际8格1891rows/28build（含1真实CityHall）/120CUDAAdam，新d27d282b模型及真实GPU恢复+6invalid已通过，16DEV4/8→4/8无胜负提升，但两臂均真实自主建造。正在从d27保持同一Adam/RNG/coreprotocol续训到预选update4（controller session53873；continuation-01；新seed3000/3100/3200）；已实际update2再148步/cumulative268，2363rows/41build。不是ancestor188+120连续。战斗six-family12并发4updates/384CUDAAdam/1536rows完成、64DEV14/16→14/16和11/16→11/16无提升；独立CPU复核真实checkpoint/片段bootstrap通过。critic主导假设被4固定TRAIN批梯度反证（actor更大/非零支持不重叠），未按该猜测改loss。战斗下一16并发60TRAIN图×双角色×双真实对手/30updates预算准备中，无新进程启动主张。旧暂停已被最新用户恢复撤销，goal工具元数据仍paused无resume API，实际工作持续按授权；不称目标完成。所有新source冻结，历史accepted/B64未替换。

2026-10-20 最新实际训练（用户再次恢复后）：局部战斗B64→lastgraph新分支已真实4updates/256 CUDA Adamsteps/1024rollout样本/40训练终局33胜0截断，64局固定DEV BattleAI15/16→15/16、公开作者11/16→10/16，无提升不升级。首启动bootstrap containment拒绝0native/0update保留；v2仅修入口路径。checkpoint131e7c1c...、完整证据与模型在experiments/battle-training-resume-20261020-v2/delivery-01（tar187160640bytes，源前后和每归档成员SHA核验）。战略首次schema5自主建造训练亦已完成：新隔离native9payload成功编译并精确还原accepted源/三bin，全8TRAIN格3000rows/19实际建造/4胜4负，188真实CUDAAdamsteps，新checkpoint34a6a86ea74d727338388db74e0ab3b9e16ec85e45ef46313757b1ac814538bc。原始目录/root/heroes3-ai-lab/evaluations/strategic-learned-build-training-01；根源码/旧模型不覆盖。经济建造真实策略化但招募仍脚本、单神经英雄、战斗仍BattleAI。新schema5保存GPU恢复及same-window16局DEV准备中，尚不能声称收益；新checkpoint未替换accepted。后续以本段和新实验报告为准，不机械读下面旧暂停/未训练状态。

2026-10-20 用户再次明确“继续训练，战场/战略AI和战斗AI都继续”。该指令撤销下面的停止要求，已恢复三个子任务：native/schema5自主建造、policy/schema5训练接入、B64普通局部战斗PPO。启动时无训练/游戏进程，GPU空闲、MemAvailable约15GB/swap0，五冻结战斗文件SHA均通过。仅一个GPU learner，根统一资源锁调度；不是已经有新梯度更新。持久goal工具当前仍返回paused（该工具无resume参数），实际工作按最新用户授权恢复，不将其伪报active或complete。最新状态将另记本次实验目录。

2026-10-20 最新用户停止指令已执行：goal paused；economy_policy、multihero_supply 两个实施子智能体已中断；实时WSL进程无训练/VCMI游戏，GPU compute列表为空。停止后不得自行恢复。新经济学习目录仅未完成源码草稿，未编译、未原生验证、未训练，不得宣称已学会建造。下文旧active/正在实施均为历史状态。

停止时最新实际结果：T2探索分支真实172 CUDA Adam步，独立配对6/8→6/8，无胜率提升；随后用时奖励对照两独立分支各132步，独立配对4/8→4/8，所有配对策略观测和动作序列一致，无收益。两组评估种子和模型不同，不可跨组比较6/8与4/8。用时实验完整证据见experiments/strategic-efficiency-reward-v1/independent-final-01/REVIEW.md，保存模型和原始证据已归档。经济和招募仍脚本，神经策略单英雄，战斗仍原生BattleAI；无人类专家课程通过整体收益资格。工程与模型恢复验证成果保留，不等同整体战略能力提升。

2026-10-19 00:34左右用户明确要求停止，已paused并保存PAUSE_HANDOFF_20261019.md。2026-10-20收到active goal continuation后恢复；用户指出工程偏离训练主线，故运输v4继续搁置，最新入口experiments/strategic-learning-mainline-20261020/PLAN.md。下面旧“正在实施/active”以最新记录为准。

入口交接 NEW_CHAT_HANDOFF_20261018.md 已完整读取；本记录补充新接管工作，不覆盖旧记录。

## 最新有效状态索引（下面保留完整实施记录）

- 2026-10-20纠偏回训练主线：strategic-learning-mainline-20261020完成TRAIN-only探索审计、明确T2初始化、真实8格2742rows/172CUDAAdam步、bb341762完整checkpoint与真实GPU恢复、16局独立DEV6/8→6/8全部胜负不变。已独立复核慢胜day46→201，未提升/未升级accepted；失败首批6格后对手GarrisonHeroSwap拒绝保留0PPO。所有T2训练/失败/DEV归档39297regular/124links通过，详见新目录PROGRESS.md/TRAINING_RESULT.md/independent-dev-final-01。下一单因素效率reward对照已登记strategic-efficiency-reward-v1，fresh共享8格2111rows全准入、0该对照更新，严格day绑定/CPUcontrol梯度验证实现中。新经济学习接口方案仅报告，运输v4继续搁置，不再沿旧“下一v4恢复”实施。

- 最新工程工作（已跨到2026-10-19）：Director发送前登记、我方全部真实ACK后终局退出/原子取消peer等待、严格中立MakeAction ACK解析已隔离验证。旧三个无效proxy批次保留，paired04完整16局/独立raw重审/归档：模型4/8、坐标回撤脚本5/8、14override，仅固定DEV脚本信号。战术positive-exchange新16局反证4/8→3/8、永久损失+4，拒绝专家/BC。报告见strategic-director-terminal-drain-v4/independent-paired-04/REVIEW.md与human-tactics-positive-exchange-v2-independent-audit/RESULTS.md。双英雄有限库存供应已真实独立资格：修复先送错reserve后，town10pikeman→courier→main5→15、courierarcher3保全，98完整script事务/跨6ownturn；仅partial机制、无收益/持续招募/恢复主张。报告strategic-multihero-supply-native-v1/CARGO_V3_INDEPENDENT_REVIEW.md。下一v4正在实现native SaveLocalState内嵌完整控制+真实SaveGame/fresh hydration；尚未认证，最新进程以本文末段为准。神经策略仍单英雄，经济脚本、战斗BattleAI，0本轮PPO/专家提升主张。

- 当前native为strategy-candidates-v3 + 七级基础兵营/原生前置 + server显式battle-ready；五冻结战斗文件未变。server源码/installer见experiments/adv-server-battle-barrier-v1/。
- 经济完整12局严格验收已通过：Empty4/4、NK1/8，仅旧权重+脚本经济开发样本。独立原始审计experiments/strategic-server-barrier-readonly-audit/ACCEPTANCE06_REPORT.md。
- 新strict并行PPO从cleanprior完成唯一分支2updates/260真实CUDA Adam步；continuous vs split/resume真实CUDA模型、Adam、RNG、请求动作精确一致，报告experiments/strategic-vector-audits/native-cuda-clean-4env-boundary-01/REVIEW.md。
- 新模型冻结SHA9a6b15c6be3866d61d8af5fe830471089c39972e57eee6e326828213d5453159，位于experiments/strategic-vector-v1/native-cuda-boundary-clean-4env-01/continuous-2/update-2.pt。新CPU开发配对native-paired-dev-clean-01已完成16局，双方Empty4/4、NK1/4，8对净差0，无能力提升证据；finaltest未碰。
- 新server回合起点存档117动作/3类trace字节精确恢复；中央单GPU4→8→12→24纯采样阶梯全部通过。24真实并发6237动作，RSS2.75GB/PSS1.855GB、swap0，0optimizer；Linux原始输出已归档G并核验18220普通文件SHA及48链接记录，非新增训练。
- release-only A对照16局已完成（pilot02）：baseline3/8、candidate2/8，但翻转局在首次release前已有轨迹差异，因果解释受限；A未升级，已归档并恢复原V8源/三bin精确SHA。通用hold/retreat仍待实现；双英雄会面query/10枪兵转兵及EndTurn已由隔离原生探针和独立raw验证，但尚无通用运输AI。战术专家/BC资格仍0，完整goal仍active。schema4最新训练和独立DEV见下面两项，历史“0更新”描述仅适用于当时阶段。

- schema4新原生day1存档恢复：275请求/响应和5类轨迹逐字节相同，fresh/restore各304真apply；蓝方train02对NK资格局day47正常胜，544move+46auto EndTurn严格通过，仅开发工程证据、0新更新/不估胜率。报告experiments/strategic-typed-native-v1/README.md。

- typed真实CUDA工程更新74158291…完成8 Adam步；独立新ACK-drain运行时的八格课程539850b6…完成164 Adam步（2588策略行、21主动EndTurn、4胜4负）。后者显式继承7415权重并重置Adam，不能称同一optimizer连续172步。checkpoint-cuda-audit-02已真实恢复模型/Adam/stop moment和CPU/CUDA/Python RNG。入口experiments/strategic-typed-training-v1/README.md。
- 新collector_v5完整行观察与实际采样源码epoch门禁通过；typed-native-cuda-boundary-v5-01真实四局（两逻辑Empty训练局的复现）已建立continuous2 vs split1/resume2：32+20真实CUDA步，模型/Adam/全部RNG/采样状态/metadata精确，1544实际request/action文件逐字节相同。update2 checkpoint容器SHA不同但保存值完全一致，双方实物保留；这是显式新epoch工程模型，非5398新研究更新/提升。报告experiments/strategic-typed-training-v1/NATIVE_BOUNDARY_V5_REPORT.md。
- typed-curriculum-paired-dev-02完成16局/8配对：7415为5/8、5398为6/8、净+1，仅小规模DEV正向信号；final test未碰，未升级accepted V8/9a6。5052实际apply严格通过，但pair3在策略首次改选前已出现NPC/原生轨迹差异；翻转pair7首次改选发生在完全相同request121/day14。16局主动EndTurn均0，不能声称学会等待/撤退/人类战术。报告experiments/strategic-typed-training-v1/DEV_EVALUATION_02_REPORT.md。

## 已核验

初始无训练/游戏/学习器进程，GPU学习锁可用；冻结战斗五文件及B64、旧PPO update1/update2 SHA符合原记录。
详细证据：experiments/strategic-policy-v1/TAKEOVER_RUNTIME_AUDIT_20261018.json。

## 第三轮超时诊断与修复

三次只读动作重放保留于 replay-diagnostic-01/02/03。原11823请求逐SHA完全匹配；第三次原生decision文件SHA也与原失败局完全相同。
不是旧对话取消，也未发现视野包回退。11803次未到达远程目标中，11569次下一步即更换目标；真实成功移动11819，另4次是合法blocking visit，旧changed_tile_replies把两者合在一起。
月份真实生成怪物，原局与重放到day1305的74次出生完全一致；旧候选遗漏中立怪。最终邻格GUARDED与出生坐标吻合，但尚未完整还原最后探索边界的所有阻断点，不将其单独宣称唯一根因。

隔离Director targets v3加入回合内目标保持和可见中立军队候选；保留原生战斗规则与冻结战斗文件。原失败种子、旧update2权重和保存RNG回归在day28、237决策正常原生胜利，0 optimizer步；这只是工程回归。
协议：experiments/strategic-policy-v1/takeover-03/PROTOCOL.md。

## 训练与恢复实测

checkpoint原子写入、单次读取SHA、异常真实optimizer步数、actor/critic本轮变化、拒绝partial恢复、CPU预检不触CUDA RNG已加固并有CPU故障注入证据。
旧权重通过显式 --initialize-from 迁移，重置optimizer/update/RNG，父SHA记录；不伪装原协议resume。

experiments/strategic-policy-v1/takeover-03/native-boundary-01/ 已真实完成连续2更新、split1、resume2，共16个课程对局（含确定性重复，不是16个独立能力样本）。
comparison.json passed=true：模型、Adam、全部RNG、逐局rollout/native决策与结果一致。
连续两轮实际optimizer56+76=132步；actor本轮L2变化0.2246154/0.3376541，critic0.5917951/0.6082465。
训练8局对EmptyAI4胜、对Nullkiller2四负；未证明模型变强。
进程树峰RSS约2.35GB（共享页重复计数），设备总GPU显存峰1817MiB（含桌面），不是GPU纯训练占用。

## 独立评估与下一研发

paired-dev-01 已完成冻结CPU argmax配对：两张v2开发图、双方角色、EmptyAI/NK对手，initial prior与新迁移后update2都为EmptyAI4胜、NK4负，净胜差0。共16局执行/8个配对单元，独立于optimizer，无最终test，没有能力提升。
四个NK训练失败局的706决策已核实：强敌被攻击候选过滤后未提供给模型，城内增援长期滞留；不是招募接口全失效。证据experiments/strategic-nk-failure-audit-20261018/REPORT.md。

## 24并发CPU实测（不等于并行PPO）

experiments/cpu-simulator-throughput-v1/native-01完成1/2共12工作负载；native-02完成1/2/4/8/12/24，共204工作负载。96个stage24任务中，实际同一采样有24原生PID+24worker，不是仅队列标签。
native02六级吞吐约0.40/0.75/1.39/2.48/3.42/5.48局每秒；24并发RSS2.807GB、PSS1.910GB，无新增swap，全部原生正常、SHA不变、无残留，池锁主管独占并给worker继承租约。
四种固定训练工作负载在所有规模中的完整状态/决策/目标轨迹SHA相同。重复局用于吞吐和确定性，不算独立能力样本。证据AUDIT.json与RESULTS.md。
单GPU批量策略采样协调器正在独立实现，尚未实跑并行PPO。

## 新可见威胁/补给协议

当前隔离native已切strategy-candidates-v3，额外输出visible_threats和own_towns，强敌仍不能作为不安全攻击目标，但不会从观测删除。坐标都是visitable；敌兵只用原生公开粗略估计，自城用自有准确兵力。已知目标入口未揭示时不再调用getHeroInfo；不获取隐藏对象。
v1工具及旧模型原协议保留，当前native不能直接用v1 broker/trainer启动。应使用新experiments/strategic-policy-v2工具，不伪装旧协议resume。
v2新encoder为26 state/23 candidate，新format；firstlayer旧列重排、新列置零。CPU新旧迁移logits/value误差0，缺字段/旧schema/非法值拒绝，mask/新特征梯度/4mode broker闭环通过。新增特征初始化权重0，不自动证明会用威胁信息。
checkpoints/threat-supply-initial-v3.pt从新v1 continuous-2/update-2.pt迁移，保留全lineage，新optimizer0。
真实new-policy v3-smoke在训练02蓝方seed2026101923完成224决策/day27正常终局、输NK；工程通过，无提升。
独立supply-aware脚本原注册16局执行到第11局被strict审计停止：前5对轨迹完全相同，0改选、无收益；第11局出现原生移动拒绝，未混入训练或当正常配对。

## 新发现的查询时序与经济依赖缺口

查询根因：QueryResolved在下一层HeroLevelUp prompt之前到达，旧queryResolved立即advanceTurn导致移动先于新prompt而发送，服务端因query栈未清拒绝。
已仅删除queryResolved中的立即推进，等待QueryReply ACK处理后继续。旧失败种子回归前156请求/动作字节相同，原失败动作现在成功并继续消耗1348移动力至0；249决策全局0move_failed/0economy_failed、15回复全成功。本局仍负，不称能力提升或所有竞态消失。证据experiments/query-drain-regression-01-readonly-audit/。

经济根因：运行本地Castle配置明确lvl3依赖lvl4，脚本priorities缺4及以上；四个历史局自城始终只30/31两级。新隔离builder已补七个基础dwelling，并仅对dwelling从原生深依赖表达式找ALLOWED前置；经济优先顺序未改，仍是脚本。
旧visible-v3与query-only-v4源码/三二进制/config变体均保存于 /root/heroes3-ai-lab/src/vcmi-adv-variants/。
经济编译首轮因LogicalExpression前置声明缺完整include失败，补include后隔离编译通过。acceptance-01首局真实day5建33→day6建32，招募与守恒转兵五兵种[0,2,4,6,8]，169兵进入原主；但第2局出现另一查询竞态，整批验收停止，未进入NK。协议experiments/strategic-economy-v4/PLAN.md，失败独立证据experiments/strategic-economy-v4-failure-audit-01/。

第二竞态根因：BattleEnded回调立即推进，早于战后升级prompt以及原生movement-query解除。已新增movementBusy跟随PlayerBlocked::ONGOING_MOVEMENT，而非假定存在UPCOMING_BATTLE解除；battleEnded不再立即推进，只在原生movement-query解除后继续。新增blocked/unblocked状态轨迹。新二进制已编译，正在原失败seed1860蓝方EmptyAI单点回归；尚未验收通过，不修改旧失败证据。

该movement-barrier回归后来已307/307真实ACK通过；旧1..272请求相同，273因新版本等待已死怪物160的RemoveObject完成而正确更换候选，旧版在battleEnded提前看到幽灵目标。不是“前295完全相同”的精确反事实；原comparison-failed诊断保留，功能证据另存movement-barrier-regression-01-audit。
acceptance-02前2工程通过，第3局发现新的spurious终局动作：PlayerBlocked解除仍越过未消费QueryReply ACK，在原生已宣布胜局后发动作286并被拒绝。未放宽门禁、未进训练。
新增advanceTurn必须queryRequests也为空的最终ACK屏障。原失败回归前285真实动作请求/动作字节完全相同，285/285成功ACK，spurious286不再生成；2次QueryReply全成功，无拒绝/终局后动作。query-ack-barrier-regression-01-audit保存证据。当前acceptance-03按原4Empty→8NK重新严格验收，尚以其最终EXECUTION为准。

历史采样门禁需更正：旧pilot02胜局558决策/557移动回复的最后一步，独立尾日志发现它可能是BattleEnded后、GameOver前误发的未执行移动，而非制胜攻击本身。逐request/native decision吻合只证明选择意图被native记录，不自动证明服务端执行。旧两次实际CUDA更新与权重文件依旧确实存在，但其执行门禁有历史缺口，不能将全部采样称逐动作执行已证。新collector逐原生ACK、回复与拒绝日志做严格门禁，未确认末动作整批拒绝；旧training.json不重写。

## 新并行采样/优化目标

strategic-vector-v1/collect_vector.py中央单model批量推断、逐环境独立generator、同步完整终局与逐请求native消费门禁已CPU假进程验证；尚未真实CUDA采样。
episode_balanced_ppo.py独立新协议：actor/entropy只给多候选选择，按每局自由选择数等权；critic按每局步数等权，避免77%强制步和长EmptyAI局稀释目标。复制强制步不改变actor目标/梯度、重复一局步不改变critic目标/梯度等CPU检查通过。不是原v1协议恢复，也未因CPU检查发生新CUDA学习。
新的parallel_trainer正集成完整update原子checkpoint/父SHA/Adam与RNG/边界恢复，待经济和查询实测通过再2→4→24实际采样与更新。
额外CPU审查发现旧新算法模块在已有Adam momentum时全forced批仍会因动量改变actor；新算法schema-v2已将无自由选择minibatch的actor grad置None，actor参数与optimizer状态保持，critic继续更新。修前证据保留，CPU03复测通过，尚无该新算法真实CUDA更新。

native-collect-02已真实完成单GPU集中推断的2环境采样，572条全执行确认、0拒绝/0未确认末动作/0遗留，0optimizer步，保留为工程采样而非学习成绩。
动态async微批使10条critic value出现<=5.96e-8浮差；旧代码还把参数SHA混入envseed，导致下一轮种子雪崩。CPU02端到端精确恢复失败已保留。去掉hashseed后async CPU03仍非逐位；新默认barrier批次等所有active环境本轮request/terminal再统一forward，CPU04真实新建fake对局连续2update vs split/resume的请求、动作、logp/value、模型、Adam、全部保存RNG逐位一致。不是只用归档batch掩盖异步失败；真实CUDA向量边界仍待验。
严格新PPO将从新干净未训练迁移prior开始：strategic-policy-v2/checkpoints/threat-supply-clean-prior-v3.pt，SHA6ced669638242eff327c2b29c3ab635528f07167a7959a2170985f2dc304e2c9。父为原prior-initial-v2.pt更新0，不继承历史弱执行门禁训练；旧模型和lineage均保留。

## 战术支线

原75局1797steps/SHA/严格事件/终局只读复核通过；撤销旧示范标签保持撤销。
新visible-exchange第一次运行在游戏创建前因冻结清单缺PLAN.md失败，证据保留。新pilot02修复冻结清单与预检后真实16局357步，全部合法正常。
teacher4/8、候选4/8，平均主力/总体损失差0，4次真实改选有益与有害抵消。预注册收益门槛失败，BC资格0、无专家认证。
原始事件独立审计：experiments/human-tactics-visible-exchange-pilot02-audit/RESULTS.md。

完整战略AI目标尚未完成，目标保持active。经济依然脚本，战斗委托原生BattleAI；局部95%/接近100%及MMAI目标没有新达成证据。

acceptance-03完成4Empty工程全通过，首NK在day6有44已执行动作后超时；是双方query弹出导致movement_unblocked早于BattleEnded，而后者缺唤醒。该局invalid不是负，后7未跑。直接恢复battleEnded唤醒的acceptance-04又在首Empty终局出现未确认末动作，严格门禁拦截，失败均保留。
据此不再推测客户端事件顺序：新增隔离server显式战斗ready屏障。engageIntoBattle登记玩家；handleReceivedPack完成整个apply和ACK之后，仅当该玩家query栈空且不存在其active battle时发UPCOMING_BATTLE END。Director等待此信号，BattleEnded本身不推进。改动只传输就绪通知、不改规则/奖励/胜负/行动合法性；原server源码备份与可重复installer在experiments/adv-server-battle-barrier-v1/。仅支持当前已验证无活动战斗的回合起点恢复，尚待编译和真实回归。

serverready编译通过：libvcmi.so d7016313e9f0e0dfc36d46a9e24d718fb2e7552e6433b5dcd0ca6a26cdaa285a；源码三SHA见installed-source-sha256.json。acceptance05因误用无torch系统解释器在游戏前失败（不计游戏），05b使用既有CPU venv，4工程通过、NK1861完整41天负。NK1862也原生正常46天负、314请求314回复0拒绝，但旧raw auditor机械要求最后trace行terminal，遇到defeat后的合法native_battle_ready状态通知而拒绝；没有终局后动作。05b失败不覆写。新审计将只允许terminal后纯ready白名单、要求所有其他状态字段与terminal完全一致，并新增反例；不放宽执行/拒绝/未确认动作门禁。尚未启动新CUDA优化。

acceptance-06最终12局正常结束并通过原注册严格raw门禁：4Empty工程全通过，8NK开发局1胜7负。此处是旧目标权重+新脚本经济，不是新PPO更新或独立提升；样本/种子/版本不同，不能直接与旧0/4作因果比较。terminal-ready whitelist全部反例/正例通过（其余状态必须与唯一terminal完全相同）。额外新增的“battle start/end客户端计数相等”诊断在终局客户端退出前未消费最后ready时不成立，明确是辅助诊断而非事后添加的训练准入要求；逐动作执行与零拒绝要求不变。下一步4env cleanprior CUDA barrier纯采样已授权runner，parent学习器待它释放GPU后才启动。

4env cleanprior barrier真实CUDA纯采样通过：717决策=701位移+16合法blocking visits，0拒绝/0未确认执行/0optimizer。env0末动作的执行回复完整，但终局后最后ACK未消费1次，明确分类terminal_ack_missing_after_execution，不声称所有ACK齐全。11.8541秒，同一资源采样4native+4worker；峰RSS461.62MB/PSS343.96MB、Torch采样allocated34.67/reserved35.65MB（不含驱动/上下文），swap0，残留0。证据native-collect-clean-4env-01/各独立审计。
新server cleanprior fresh new-policy单局seed2026102401 day13胜，117请求/动作=112位移+5blocking；回合起点加载117请求动作和3类trace字节全部相同，native_load_verified=true，0optimizer，证据strategic-vector-audits/cleanprior-turnstart-2026102401/。当前parent已启动4env新CUDA continuous2，目录strategic-vector-v1/native-cuda-boundary-clean-4env-01/continuous-2；仅此一个学习器，待完成再串行split1/resume2与严格对照，不能先声称更新成功。

新v3/strict vector CUDA continuous2已真实成功：update1=1818样本/8完整局、421自由选择、116 Adam步、actor L2 .4309126926550346、critic1.5714396653238123，SHA6644caecf42e5b776eca182f5ddc3d9ed9b532772be4eeb0ccd98b5bd98e51ac；update2=2281样本/8局、491自由选择、144 Adam步、actor .6072322013091563、critic1.2691137430147243，SHA9a6b15c6be3866d61d8af5fe830471089c39972e57eee6e326828213d5453159。总260实际CUDA Adam步，0partial/invalid，工程更新成立；未独立评估，不称变强。现在串行独立split1运行，随后同协议resume到update2做精确恢复审计。

新并行真实CUDA完整update边界已由独立默认CUDA审计精确通过：strategic-vector-audits/native-cuda-clean-4env-boundary-01/AUDIT.json passed_exact=true/validation_error=null/failed_checks=[]。continuous2 vs 独立split1+resume2逐局请求/动作/logp/value/return、initial/update1/update2模型与Adam及CPU/CUDA/Python/episode RNG、协议/source全部一致。唯一训练分支2updates/260步；验证另做116+144真实步，是恢复重复，不额外累入交付模型训练轮次。当前runner用CPU执行cleanprior vs冻结update2八对16局新seed开发评估，原图已见、不动finaltest，尚无独立能力提升结论。

新paired-dev-clean-01最终16/16 strict正常、5949决策独立raw通过：cleanprior与新update2都5/8（Empty4/4，NK1/4），8对净胜差0、discordant0；5对实际请求动作轨迹不同，但无新能力提升证据，不以个别赢局更快或输局提前结束作整体提升。dev历史已见，distinctmaps2/noCI，finaltest未碰。runner现按既定授权8→12→24真实CUDA纯采样容量阶梯，固定已训练candidate9a6、零optimizer，逐级合法/资源/清理过关才扩。
下一方法A候选仅当前可见近距>=1.5倍压力下释放commit（Chebyshev<=12是预注册新参数，不是原生拦截半径）；源候选9a8dda...，尚未安装编译。当前accepted server-ready-v8源码/三二进制/config已归档WSL variants/server-ready-v8，后续对照先8baseline再编译A并8candidate，同一已冻结训练权重，不将机制效果混成学习提升。

中央单GPU真实vector容量8→12→24全部严格有效，始终0optimizer：8env2188rows/35.371s/RSS.971GB/PSS.694GB；12env3482rows/59.266s/RSS1.436GB/PSS1.006GB；24env6237rows/51.957s/RSS2.750GB/PSS1.855GB，24native+24worker同刻实证，8cells各3unique seed、swap0/minavailable12.872GB、两锁free/残留0。24热输出移至Linux独立目录以保持120s预算，随后完整归档G；forward占wall12.86%，不可仅凭并发/输出路径共同变化断言NTFS是唯一瓶颈，也不可跨异工作负载game/s作纯扩展结论。实际容量证据在native-capacity-learned-01，Linux24/root/heroes3-ai-lab/evaluations/strategic-vector-capacity-learned-01/scale-24保留。
phaseA prepare已查种子1881/82无冲突，2681native源+426共同输入+3bin冻结，planSHA1b635929be64183c2bb5a2af52f6d8a14c1a2b1817727a405d595e5766f60dd1，15CPU反例通过；tactics开始native-pilot-01 baseline8，候选还未安装。所有臂固定同9a6权重、不PPO。

A原baseline pilot01前4合法，第5train02红1881原生80天正常负/767动作执行，却被旧army审计Ambiguous transfer拒绝。确定根因是纯Python Counter({cid:count})覆盖重复兵种槽：hero弓兵[6,4,6]→[42,4,6]与town36→0真实16→52净36，原生ArrangeStacks2321收/执行/ACK全证。不是转兵失败或模型数据造假。旧pilot01 failed保留；tactics只修audit_supply_raw逐槽累加与反例，新pilot02按同固定seed/权重完整重8baseline（重复工程验证不是新增能力样本），native/候选阈值未改。checkpoint独立重算历史06/经济转兵组件影响，PPOcollector执行门禁和CUDA梯度/精确恢复不依赖该Counter，不重写旧训练记录。

A pilot02已完成16局独立raw：6000决策、227QueryReply、0拒绝/未证执行。baseline3/8→candidate2/8，release真实377次；其中333次旧目标仍可用本会压单、44次本来已失效。不得将release数当收益。唯一胜转负pair7在request17/day3已动作不同，但首release到request155、主hero此前day15已丢失，因此净-1不是干净release因果证明，最早native差异仍在定位。A不晋级；源/三bin/config保留variants/threat-release-A-v9。parent已安全恢复baselineV8并重新编译，三bin SHA逐字节回到b94162.../bbe0de.../d70163...，Director e198e32...，五冻结战斗SHA仍全通过。
schema4独立CPU模型27state/25candidate、typed move/end_turn、单hero、own_turn正int已由runner完成；128真实move-only请求迁移前后logits/value误差0，21反例/梯度/save-load通过。typed-from-update2-v4.pt SHA2a630a48a9eafb599ff74210df41d2de7dd225ad129e4e7aba1f45fc5c307e6c仅显式权重迁移，0schema4更新/未真实EndTurn。新broker/typed事件门禁在独立目录准备，禁止当native成果。
多英雄机制probe三版本/fixture/runner仅CPU准备，待独立增量构建capsule并实际验证；原source能力审计32局均最多同时1hero，尚无真实多hero会面、守恒转兵或courier能力证明。

## 多英雄隔离探针预检02（继续执行，尚无原生结果）

已将线程服务器和三处固定运行资产目录链接处理冻结到 experiments/multihero-mechanism-probe-v1/build-driver-frozen-02；16项capsule CPU检查和20项机制CPU检查通过，仅为工具检查。
真实执行 multihero-capsules-02 在源码清单预检发现 defender-ipnkyfqb-best3.onnx 悬挂链接，未进入源码替换、编译或游戏。失败原始证据 /root/heroes3-ai-lab/evaluations/multihero-capsules-02/BLOCKED_OR_FAILED.json 保留。继续只读核查全部链接及CMake引用，精确区分非编译运行资产；不以通配放行替代核实。
当前仍为已验收V8；本次0游戏、0训练样本、0optimizer。typed schema4 CPU模型/事件合同已准备，原生候选在独立目录审查，未安装、未训练。

## 真实双英雄会面机制已验收（0样本/0更新，非终局）

frozen03完成三个隔离capsule真实增量编译，并重建恢复原V8三bin精确SHA；EXECUTION passed=true/rebuild_required=false。实际client映射capsule lib路径/inode/device/SHA及runServer线程已证，不只client文件SHA。
runner历经03/04/05初始化目录及验证器问题，所有失败保留。EntryPoint按argv0切cwd，最终工作目录client链接启动解决资源定位；运行期settings自动保存改列可变输出并冻结初始副本。MapQueries/QueriesProcessor及raw证实Garrison query只server pop，不发预期QueryResolved；改以真实pop+QueryReply/EndTurn应用成功与同请求ACK判定，close04、transfer01全新重跑通过。
transfer01真实ArrangeStacks5转移10枪兵：courier10枪兵+3弓兵→3弓兵；receiver5→15枪兵，守恒、双方非空，QueryReply6/EndTurn7成功。original-unhandled01查询未关闭，20秒工程超时、不计胜负。独立审核器逐包raw+state已通过，删应用证据/错ACK/破守恒3反例拒绝。报告 experiments/multihero-mechanism-probe-v1-independent-audit/REPORT.md；AUDIT在native-01/。原始Linux保留并归档G native-evidence-01（以ARCHIVE.json最终结果为准）。
这不是通用courier或能力提升。尚未把探针代码升级训练环境；schema4原生候选未编译。三个子智能体因用量限制退出，主进程继续。

## schema4已真实编译、EndTurn原生执行与运行资产故障修复

独立typed capsule01真实编译通过；原V8再次重建恢复e198源码/b941 client/bbe0 server/d701 lib精确SHA，不升级当前训练环境。C++实际协议helper7个SHA向量/17响应案例通过，不等于游戏验证。
完整Lua资产的typed diagnostic02实际2move+2policy EndTurn同请求/服务端真apply/ACK全证；原whole-game gate仍因非终局正确拒绝，不合成game_over。实际迟到ACK数0，合成反例验证仍不能代替真实时序覆盖。
第一次typed fullgame01在264move/day29战斗中120秒超时，0样本/0optimizer/不计输赢。原始日志268MB保留：缺41脚本中多个damage/combat layer，最后战斗9610轮/70084行动。root独立V8同seed2026102601/同父权重对照275move/day30正常胜。定位为capsule启动器漏打包原生Lua运行资产，不是模型或BattleAI算法必然失败。
run_fullgame_scripts.py复制41脚本并逐SHA比对compiledsource清单、缺脚本即无效；新fullgame02同binary/seed/model完整30天red胜，275policy move+29auto EndTurn共304真apply raw门禁通过；模型未选policy EndTurn。275移动决策归一后与V8对照逐字段一致；failed初264完全一致。两个实验除补脚本与检查外不换模型/规则。报告experiments/strategic-typed-native-v1/README.md及runtime-scripts-causal-audit-01、native-fullgame-raw-audit-02。
为修正旧probe运行资产不全，frozen07已在完整41脚本环境重跑3个会面探针，native-complete-assets-02独立raw全通过，兵力状态SHA保持一致；旧probe仅无战斗局部链路证据保留，正式机制依据改为完整资产复验。当前所有工作0新PPO、0专家课程，能力提升仍未证明。持续goal active。

## schema4原生回合起点恢复与蓝方长流程

run_game_v4.py已支持两张训练图、双方阵营、Empty/NK及原生testsave；固定finaltest仍未碰。实际从fullgame02的day1 own-turn-start .vsgm1加载，原生3项load标记全证；275请求/275响应、5类broker/decision/state/target/typed trace逐字节全一致，fresh/restore各304真apply门禁通过。证据native-restore-exact-01/AUDIT.json，save SHAe4cd26674bcc10c2d7448c35adfff25b00a4446cb970362a9a2eb65b8956e1ad。仅此起点，不扩称任意中途/战斗恢复或schema4 optimizer恢复。
新蓝方train02 seed2026102602对Nullkiller2正常day47胜：544策略move+46auto EndTurn、590真apply raw全部过、0policy EndTurn。不是配对提升/胜率估计，仍继承旧权重0schema4更新。第一次read-only audit错误要求全部player gameOver callback只有1；源码log在playerID guard前、red负与blue胜均合法，失败输出01/旧审核器保留，02按owned colour精确过滤并对照state终局，未重跑或改写游戏。报告native-blue-nk-raw-audit-02/AUDIT.json。
多英雄fullassets补验与typed失败/成功/对照全部先前8目录已归档G native-evidence-01，ARCHIVE passed=true，共5399记录；新增restore/blue NK另行补归档。goal仍active，正式运行V8未升级，后续需typed采样/PPO完整边界和独立配对评估，同时将真实会面机制推进到多英雄运输控制。
补归档native-evidence-02已完成并逐SHA核对：restore1034记录、blue-NK1571记录，ARCHIVE passed=true，原Linux证据保留；未展开运行资产链接。蓝方全程最多同时1hero，turn-start先后hero3/22/43/23/124，不将5个顺序替补误称5英雄调度。

## typed真实CUDA随机采样与PPO入账门禁

新experiments/strategic-typed-training-v1与旧v2/vector/weights-only文件隔离，未改已冻结输入。单CUDA模型随机采样由父进程GPU→pool两锁与继承FD device/inode/排他性实证约束，未并行运行第二学习器。新seed2026102701 red/Empty完整局正常胜：126move+1模型抽样EndTurn+12auto EndTurn，共139真服务端apply/同请求ACK由原raw审计通过。此为1训练场景，不推能力提升或胜率。
原始请求在CUDA上独立复算，127动作/旧logp/value/响应/起止generator RNG逐项精确一致。admitted-episode-01准许127行后续PPO（126move/1EndTurn），自动12行排除；入账不等于已经更新。source/model/raw/输出SHA链均检查。新typed episode-balanced PPO模块已转schema4并加强native绑定/操作/策略SHA/精确抽样/整体终局门禁。
CPU仅反向传播检查stop_bias梯度0.0018394241342321038，其他梯度有限；空reward/未证执行/错op/旧schema/无终局/错checkpoint六反例均在step0拒绝。此轮CPU optimizer0/CUDA optimizer0，没有新训练checkpoint。下一步必须新建不冒充旧weights-only的可恢复checkpoint格式，并真实验证完整update边界，再配对评估；不能把已完成采样或梯度误说模型已训练。
证据入口experiments/strategic-typed-training-v1/README.md。单env CUDA仅此规模，不把旧schema3的24容量实证冒充新typed24训练。
新typed-onpolicy原始目录已完整归档G strategic-typed-training-v1/native-evidence-01，738记录逐SHA核对/链接不展开，ARCHIVE passed=true。五冻结战斗文件末次再次全OK。原新采样/准入工具和admitted数据已作为冻结证据，后续可恢复格式/采样器升级需新版本文件，禁止热改使本次Plan SHA失效。

## 新typed可恢复格式、真实CUDA更新与终局ACK边界新失败

model_io.py新增独立strategic-typed-ppo-checkpoint-v1，旧weights-only格式保持严格不变。CPU checkpoint-cpu-01实际1次仅测试Adam步，actor.stop_bias动量/模型/Adam/CPU+Python RNG精确恢复，写入前故障保旧文件，7类非法恢复拒绝；TEST_ONLY文件禁止默认部署和CUDA恢复，不计交付训练。
真实cuda-update-engineering-01由已原生+CUDA重放认证127行完成1完整更新/8 CUDA Adam步，actor L2 .12115378564732837，critic .19168280469877838，stop_bias -4→-4.0008697509765625。checkpoint SHA74158291dbf4213d4282a96fc620ba6d720707737c79dad01db84e3ac12308e1。真实CUDA独立boundary审计模型/Adam/stop动量/CPU+CUDA+Python RNG精确，5非法恢复不改任何状态；这不是continuous-vs-split native两更新比较，后者尚未做。单局仅工程，不称能力提升。
新亲本7415采样blue/train02/NK seed2026102802/logical1正常负，385move+1policy EndTurn+41auto，共427真apply、386行CUDA重放精确准入。尚未用这单负局更新。数学复核单终局回报单局中心化会取消actor的常量胜负项（CPU反事实分析maxdiff4.768e-7，0反事实样本准入/0optimizer），所以改为同一亲本8格混合批次，禁止把旧亲本赢局与新亲本负局混训。
8格cohort typed-onpolicy-balanced-01前两Empty格有效（259/179行），第三格train01/red/NK seed2026102812在day12因7天无城正常负，但最终自动EndTurn330只有真实server成功、缺client ACK，审核拒绝，batch accepted_rows0/optimizer0，未换seed规避失败。原始日志：PlayerEndsGame在CGameHandler结束EndTurn并发ACK前发出，client测试模式allPlayersEnded立即关闭，丢掉真实ACK。未放宽EndTurn必须ACK的门禁。
新隔离experiments/strategic-terminal-ack-drain-v1候选只改client收尾：ThreadSafeVector加持锁empty；测试模式全部终局后等待既有waitingRequest登记请求逐个真实PackageApplied排空再关闭。游戏规则、胜负检查、server apply/ACK不改。正在4编译任务受锁构建新capsule并最终重编译精确恢复V8；不可在build运行时改冻结候选。新epoch不允许7415旧optimizer假resume，必要时仅显式继承权重并记录重置。

## 终局修复复现与首个新epoch混合课程更新

终局ACK-drain capsule01实际构建/重建恢复全部通过，正式V8 source/三bin精确恢复不升级。原失败seed2812/7415权重100请求响应、decision/state/targets/broker轨迹逐字节完全相同；新增实际EndTurn330 ACK在game_over后收到，没有终局后行动，仍day12无城正常负。regression-exact-01/和native-repro-raw-audit-01/全过，admitted-repro100行仅资格复现，不混入新epoch训练。
新client capsule8格typed-onpolicy-balanced-ack-01实采全部结束：前7格严格准入，第8格原生正常退出0/ACK排空，collector轮询漏读最后game_over致wrapper false。未重跑游戏或改原JSON；audit_game_v5从最终raw终局、exit0和真实ACK逐项只读复核，native_completed/transport_drained真实齐全，admit_v4 CUDA逐项精确重放587行准入；原失败RESULT保留。collector_v4改为退出后读取最终已刷新的事件，超时/kill仍拒绝。reconcile_curriculum新ledger独立封存8格2588行、21policy EndTurn，4Empty胜/4NK负，均同一7415策略/同一native epoch，0额外重采样。
新epoch因client源/collector协议改变，train_update_v2明确--initialize7415重置optimizer，记录父1update/8步和完整lineage，未假resume旧协议。cuda-curriculum-ack-01真正完成1完整8格PPO更新、164 CUDA Adam步，actor L2 .4584993197865499/critic1.0209397348435896，stop_bias -4.00086975→-3.99550915，stage checkpoint SHA539850b6552a97adb10425605d7eebc065cf60d799a192833227cb2cb220bcc3。批次真实4胜4负是训练成绩，不是提升结论；全164步、模型精确读回过关，独立完整边界审计待执行。
独立DEV配对已按预先固定8对seed2026110600..07启动，baseline7415与candidate5398冻结、同一ACK-drain binary，CPU argmax、两张历史已见DEV图/双方/Empty+NK，finaltest未动。首个策略请求比较检查行动前世界是否相同，invalid不计负，尚无胜率/提升结论。正式V8与历史模型9a6仍未升级。

## 新课程独立DEV配对最终16局与行为限制复核

paired-dev-02严格16局8对：baseline7415为5/8，candidate5398为6/8，净+1/discordant1。均CPU argmax同一native binary/41脚本，5052个实际Move/EndTurn应用和ACK通过（4570policy move+482auto EndTurn），评估0optimizer/0训练样本，finaltest未碰。只称小样本DEV正向迹象，不能称95%、总体稳定提升或人类战术学习。
更细复核发现：虽8对首请求都字节一致，pair3在首策略改选18前，request17已世界观测不同，原生/NK非确定性仍在。保留该loss/loss对，不掩盖因果限制。唯一翻转pair7在相同request121/day14先改选等启发式分数frontier，request122才轨迹分歧；原先day75负→新day122胜，支持局部路径改变线索，但不扩推稳健优势。
2103基线观测逐条CPU单样本shape复算，旧argmax全部精确，新模型仅21改选；居中logit最大变化.0572433/中位.0129452。所有16评估局policy EndTurn=0，新模型bestMove-stop gap最小4.45825/中位7.56248，不能将+1归因学会等待或撤退。固定启发式先验与commit候选瓶颈仍须改进，不能只堆训练。
5398检查点的164 Adam步、模型/stop动量/CPU+CUDA+Python RNG在checkpoint-cuda-audit-02独立精确恢复，5非法恢复均不改模型/Adam/RNG。尚未建立该typed流水线continuous-vs-split原生两更新等价。eval01失败为读取live NDJSON未结束行，保留0完成配对；eval02仅延迟未换行tail、完成行仍严格拒绝错误，91分割位置CPU检查通过，不改预注册模型/种子/终点。
报告experiments/strategic-typed-training-v1/DEV_EVALUATION_02_REPORT.md。原生数据（含失败）正归档native-evidence-phase-02，需以ARCHIVE.json最终结果为准。持续goal active，正式V8/9a6及冻结战斗未升级，多英雄运输AI/人类专家资格仍未完成。

## DEV原始世界前缀复核、同策略复跑与训练采样观察修复

native-evidence-phase-02/ARCHIVE.json 已passed：8目录合计31469条普通文件SHA/链接元数据记录，包含失败尝试与完整16评估局；原Linux证据保留，不展开游戏资产链接。
新只读audit_paired_world_prefix.py复核全部8对server移动前缀：pair3在我方首动作前第3条移动即不同，绝非策略改选所致；pair7在policy9后第38条移动即对手英雄顺序不同，早于policy121改选。audit_movement_order.py进一步区分：pair3改选前65条移动集合也不同；pair7改选前320条移动按owned-decision边界计的集合相同，仅顺序不同，但仍不认证完整隐藏世界/RNG一致。已补充DEV报告，不将相同visible request误称世界完全一致。
repeat_dev_control.py预先限定单次旧策略重跑pair3，同7415/seed2026110603/原native，真实357请求/选择逐条精确、同样loss；对手第36条移动顺序不同但没有改变策略观测。此控制局独立于原8配对终点，0optimizer/0训练样本，原5/8 vs6/8不重算、不挑样。
idle-after-dev-01.json核实accepted V8源码/三bin及五冻结战斗SHA全一致，GPU/pool锁均可独占，native/learner进程0，GPU compute0，内存可用约14.79GiB，swap使用0。此为该时刻快照。
collect_episode_v5.py / admit_episode_v5.py 将已通过91分割位置检查的live_jsonl完整行观察用于训练，不改冻结v4；新train_update_v3.py同时将actual admission/collector/source哈希绑定到protocol，不能只凭native runtime相同接受工具暗改。真实CUDA入口collector-epoch-cuda-check-02分别拒绝旧runtime、同runtime旧collector、新collector恢复旧checkpoint协议，均在Adam调用0时拒绝。check01用错旧runtime fixture，先被正确的runtime门禁拦截；失败记录保留，未计为源码门禁通过。
新采样资格typed-onpolicy-observer-v5-01使用5398冻结权重、train01/red/Empty、seed2026110700/logical1：253policy move+25auto EndTurn，278真实apply/ACK、正常win；admitted-observer-v5-01在CUDA重放253动作/logp/value和初末采样RNG逐项精确。0optimizer，不是新增学习收益或两更新连续恢复证明。该253行尚未更新；新train_v3若正式启用须显式新epoch，不能把5398旧protocol optimizer假resume。新控制和采样raw正归档native-evidence-controls-01，以ARCHIVE最终结果为准。
持续goal active；下一关键缺口仍包括typed完整连续vs分段原生两更新等价、固定prior与回合目标commit的策略限制、通用多英雄调度/经济学习和真实战术课程认证。

## 新v5完整原生两更新连续/分段恢复实证

native_boundary_v5.py 与 run_boundary_v5.py 冻结后实际执行continuous2、split1、fresh-process resume2。显式继承5398权重并重置Adam的新工程epoch；训练图train01/red/Empty seed2026110800和train02/blue/Empty seed2026110801，每个分支重新真实采样，4局正常终局/真实apply-ACK审计/CUDA独立重放准入全过。单learner连续保留model/Adam/全局RNG，child仅推断/重放，GPU/pool租约串行，parent在child运行期间不调用CUDA。没有用归档batch冒充第二次原生采样。
continuous update1为506策略行/32 CUDA Adam步；update2为266新on-policy行/20步，总52。split/resume重复同样52步，不将104执行步称同一模型104步、不将两逻辑训练局的复跑称4独立能力样本；仅工程恢复测试，单局中心化缺陷不被当作策略改进。5398研究模型未改。
COMPARISON passed且独立native-boundary-v5-audit-01再核验完整bundle values：模型、Adam moments/steps/group、CPU/CUDA/Python RNG、collection_states、progress/lineage/protocol逐项精确。额外独立审计纠正原比较器response glob未覆盖真实action-*文件的问题：实际1012+532=1544 request/action JSON逐字节一致；broker/logp/value及decision/state/targets trace也精确。
update1两分支物理SHA相同17367db7…；update2保存值完全一致，但container SHA continuous22fcd42e6175c49df9bf229293609fe8d166180e19e4ada2c68306cbb7c58fce、resumed a3b0ac6d37800872baf06db23a890eda7b205733331d95270b6192eb18ebc16c不同，不宣称checkpoint整文件字节相同。全部实物保留，完整raw/checkpoints正归档native-evidence-boundary-v5-01；报告NATIVE_BOUNDARY_V5_REPORT.md，归档以ARCHIVE.json最终passed为准。
此前native-evidence-controls-01已passed（1204+990=2194记录）；两次控制/采样资格局全部SHA/链接元数据复制验证通过。
新增action-opportunity-audit-01对全部16 DEV局只读计数：baseline1516/2103=72.09%、candidate1821/2467=73.81%的观测仅一个move+stop；看到敌军时相应682/923、897/1161。此类行虽是PPO数学自由选择，却无其他目的地可选；不能仅凭该计数把全部归因commit，但源码确有回合内retained目标剪成单move。该限制与固定prior/stop gap需先解决，再扩大研究更新；不能取消commit导致旧第三轮目标抖动问题复发。
goal继续active。Empty工程两更新恢复缺口已按以上限定补上；NK完整隐藏世界确定性、任意midturn/battle恢复、typed24训练、多英雄与学习经济、人类战术资格仍未完成。

补记：native-evidence-boundary-v5-01/ARCHIVE.json 已passed，5061普通文件SHA+16链接记录完整复制核对；原Linux raw保持。idle-after-boundary-v5-01再确认accepted V8/五冻结文件全SHA一致、两个锁可独占、native/learner/GPU compute0、swap使用0。新增run_boundary_v5_cli.py为指定全新out的复现入口，原执行launcher/driver不改；仅syntax/help验证CLI，不假称额外4局。

## 有界可见威胁中断与独立脚本回撤假设（新研究分支）

新增experiments/strategic-threat-replan-v2/，不改旧A/typed/GPU训练源码。新native在同一binary内严格off/once：仅原已可见敌英雄>=own1.5、同层Cheb<=12、retained目标仍合法且真实完整候选>1时，每hero/own_turn最多一次打开已有合法表；选择后立即commit，预算随yourTurn重置。无额外逃生格/空城/安全奖励/越过战斗查询门禁。真实纯C++18边界/预算断言过；独立agent只读源码review无阻断。显式player cast为防御性输出，原PlayerColor底层本为int32，不算发现字符JSON缺陷。
新typed-bounded-replan-capsule-01真实编译和重新编译恢复accepted V8源码/三bin精确SHA全通过；client仍332e985b…，new lib4cf725d9301a8e8abb447f5d18955cbda4f661fdc93b8ea4e2a3befe0ff66091。三Empty资格legacy旧capsule/off/once同seed2026110900，117move+12auto各正常win，238请求/响应/轨迹文件逐SHA完全相同；仅工程资格。
预注册8对训练图诊断typed-bounded-replan-paired-01（seeds2026110900..07、5398同权重CPUargmax、同binary）全16局结束：off4/8、once4/8，17真实release、0改goal、0改next。因果字段旧runner的zip/双臂max有审计缺口，False不可称世界相同；独立causal审计另行补充。初始raw执行全过，0optimizer/训练/专家标签，不升级默认。开放可选目标本身未改变行为，不能再仅堆PPO或把此当学会撤退。
独立audit_replan_v2加强证明raw_sha/owned/source绑定，重新extract实际serverapply并重跑exact执行contract；遍历全部请求重建retained目标，检出无日志多候选/重复预算。review-v2-native-01全16局3542个策略request/action、2482个retained检查、17release通过；review-v2-cpu-01的18反例明确是假fixture且不认证native，全部拒绝。原冻结v1审核器/runner原样保留。
另立PROXY_PLAN.md：同once binary两arm，5398模型 vs 仅在真实release时对现有合法非军事候选做坐标clearance脚本排序，要求比当前位置和模型下一步都严格远离已见强敌，保留模型选EndTurn。公开压力坐标不是敌可达距离或安全保证，不是学习/人类专家。17归档状态离线12次可改选；CPU broker实际重算模型推荐精确、fallback/输入不变通过，0native/optimizer。
proxy工程fixture typed-clearance-proxy-qualification-01复用seed0902仅机制资格：实际85move+10auto、95真apply/ACK、正常loss；两个script override（request71/day9 clearance6→7，79/day10 5→6），v2执行审核和独立CPU模型+proxy重算通过，0专家/训练样本。原baseline同seed仍loss但day12→proxyday10，不能拿远离坐标当整体收益。
已启动单独固定8对typed-clearance-proxy-paired-01，seed2026111000..07，两臂均once，同native/5398；新paired_proxy.py含EOF差异检查、真实script override前prefix筛查，不凭seed同就认证因果。当前仍运行，tool session6217，最终以RESULT.json为准，切勿重复启动。前两Empty pair双方win且0override。代理source/runner/plan已冻结，运行中不可改。
完整已完成capsule/3资格/16诊断/proxy资格原始证据正通过archive.py归档native-evidence-01（session待当前工具返回确认）；原Linux保留。新proxy全16诊断完成后需另归档，不能复制正在写的raw。goal active，完整战略AI/通用多英雄/学习经济/真实人类课程仍远未完成。

## proxy首批审计失败、真实发送登记竞态定位与Director限定修复

typed-clearance-proxy-paired-01已终止而非仍运行：前2 Empty对完整，pair02/b虽原生正常结束，但raw_events_v4在client.log108701拒绝server rq1485先于typed binding108703，整批RESULT passed=false，未计其胜负或训练。切勿仅改两遍映射放宽门禁。
原生CClient::sendRequest522..538真实代码：先waitingRequest/ID/player登记，再sendGamePack，最后requestSent，因此快线程server可早于typed上下文。请求442看似错位的坐标实际是convertFromVisitablePos固定object偏移，不是相邻动作错配；独立agent与root分别核实。公开失败与该更正均保留。
新strategic-request-bind-barrier-v1全AI提前通知提案编译/精确恢复过但0原生局、未采纳；独立review发现NK QueryReply也用requestSent，所以v2限定实际receiver.dllName==DirectorAI时发送前登记，其余AI保留原post-send顺序并exactly once。现成shared_ptr捕获receiver，不变虚表/ABI。Director另核对actual native ID/player、MoveHero hero/单object目标与prepared上下文。实际源码dispatch片段编译5情景通过（fake fixture，非原生认证）。
v2新typed-request-bind-director-capsule-01真实编译/原V8 source+3bin重编译SHA恢复通过；new client9f3487c9f0bde496a8e2d7fa060345c7e398592078a0f691ad80918ccdc606a8，lib0376356de6dc87c67164193fb62bd88d39c98805a88a8d89d03ef730412c6403。原失败seed2026111002/同5398+clearance/同once重新真实运行typed-request-bind-repro-01：601policy+58auto=659真实apply/ACK正常负，whole-game、v2 retained/预算、CPU frozen-model/proxy全过，5真实override。compare_repro对1206 request/action/gameplay文件逐SHA全部一致；原659apply中仅rq1485先于context，新659全部在真实context后，不改规则/路径/胜负、不追认旧失败局。报告native-repro-comparison-01/AUDIT.json。
完整paired_proxy_bind_v2.py以相同原定1000..07 seeds和proxy方法、两臂同新capsule重跑8对，当前active session6459；是修复工程后的预注册批次重跑，不冒称新独立holdout。原paired01 failed与源码/原始日志保持。
新bounded原16局独立CAUSAL_STABILITY_REVIEW：8对完整语义政策序列及去候选的可见观测序列全相同，4个有release pair首次真实release前完整server移动前缀相同；pair3后续第1339条只是动作顺序差异(双方1801条)，不推完整世界确定。双方目标切换/反向所选步计数逐对相同，16局MAX cap事件0，最高单回合20moves。EOF投影12反例通过。
native-evidence-01归档已passed：4目录17913普通文件SHA+80链接记录。失败proxy首批正归档request-bind-v2/failed-proxy-evidence-01（session47806），明确experiment_passed=false；两版capsule正归档native-capsule-evidence-01（session7336）。保留Linux原证据。后续还需归档成功repro与完整paired02，等待实际终局不得重启现job。goal active，0本轮GPU/PPO/专家标签。

## 第二批终局超时与所有我方请求真实确认的新终止协议

paired02现已停止，session6459已退出，不能按上文active状态重启。pair03/b实际237策略move+27auto=264次apply/ACK，真实defeat/day28后，对手最后发出的MoveHero867没有ACK；工程120秒终止(-15)，不计败局、不用于更新。旧raw whole_game_valid仅证明策略消费，native_game_completed=false/transport_drained=false/winner=null，不能解释成整局有效。

源码交叉核实：CGameHandler在所有玩家结束后设置SHUTDOWN，CVCMIServer立即停止NetworkHandler，后来发出的对手请求无法进入服务端handleReceivedPack。继续等待所有客户端请求ACK会永久等待。新隔离strategic-director-terminal-drain-v1只在真实所有玩家结束且所有Director实际请求已收到真实ACK后请求正常退出；对手剩余等待由原finishGameplay/requestTermination明确取消。新增每条Director注册/真实ACK及所有实际ACK的ID/owner/native pack_type记录，取消意图和实际终止快照分开记录，不虚构ACK或执行成功；新v6完整对局审核和v3重规划审核要求这一新协议，旧审核器/失败证据不追改。

新候选第一次CPU准备因原if空格不匹配断言失败，0原生源码写入；保留prepare.py并以complete_prepare.py补齐候选。新capsule typed-director-terminal-drain-capsule-01正在持双锁编译/恢复验证，session79115，仅此构建，不运行游戏或GPU learner。独立agent新CPU审核3正例/26拒绝反例通过，仅假fixture，非原生资格。

归档最终结果：failed-proxy-evidence-01 6354记录、failed-proxy-evidence-02 8055记录均复制SHA通过且experiment_passed=false，未评分；native-capsule-evidence-01两capsule各238普通文件通过；native-repro-evidence-01成功repro1682普通文件+4链接通过。Linux原证据保留。持续goal active，0本轮训练/optimizer/专家标签，通用多英雄和学习经济仍待实现。

终局修复预运行review补记：v1 capsule01已build/restored passed、0native；v2 capsule02采用atomic snapshot+clear也build/restored passed、0native。独立review又发现原ThreadSafeVector pushBack在锁外检查terminating，可能穿过终止后入队，以及晚ACK触发旧assert；因此不启动这两个版本游戏，保留已构建实物。新v3在同mx内终止并返回实际clear IDs、锁内拒绝晚pushBack、wait predicate观察termination、晚tryRemove返回false；独立agent正在完成源码/CPU线程片段测试及capsule源码绑定门禁，尚未build或native。v6已纠正whole_game_valid必须完整contract+真实terminal+exit0+owned drain，单列event_contract_valid；旧v5/失败证据不追改。下一运行以v3原生资格3局（相同NK超时fixture+red/blue Empty）为准，不计能力提升。

v3后续实证：138项提取真实ThreadSafeVector片段线程CPU检查、28项ledger/proof拒绝反例+5整局负例过；均非游戏认证。capsule03真实build及accepted V8源/三bin重编译SHA恢复passed，session14977结束。新runner/v6独立绑定9候选SHA、source-snapshot、build-source-manifest和实际加载inode/hash，显式新atomic语义。
typed-director-terminal-drain-qualification-01新3局runner+v6 raw+v3replan+CPU model/proxy全部通过（session66750结束）。原超时fixture seed2026111003蓝方NK：237policy move+27auto=264实际apply，399所有Director请求（含经济/查询/战斗）注册和真实ACK逐ID/type/owner/success齐全、正常exit0/loss；atomic终止明确清除foreign866/867，0我方取消，不虚构peer执行状态/成功。原237request+237action逐字节完全一致，decisions/targets/replan三trace相同，strategy-trace存在差异待独立说明；原旧超时仍invalid/unscored。新G报告v3/native-repro-comparison-01。红/蓝Empty对照正常完成，无能力主张。
已启动typed-clearance-proxy-paired-03，固定原1000..07种子和相同算法/两臂once/同5398CPU argmax，两臂均capsule03，源/资格RESULT+PLAN及其当前输入hash冻结；不是新独立holdout。进程由新paired_proxy_drain_v3.py执行，切勿重复启动，最终以RESULT.json为准。独立agent复核3资格raw；另一agent仅CPU诊断人类战术旧无收益原因并准备新隔离候选，不占模拟/GPU资源。持续goal active，0新optimizer/训练/专家标签。

paired03最新更正：session89178已退出failed，2 Empty对完整，pair02/a原生正常exit0却被v6的统一ACK parser拒绝。例client.log67358真实`NativeRequestAck id=838 player=-1 pack_type=198 success=1`；当前regex只收非负player。独立源码已核对NEUTRAL=-1（另有-2/-3/-4专用值，不会任意放开），正在核对MakeAction具体来源并准备全新Python审核epoch v4；native capsule03不需再编译，旧paired03不追改分数/结果。failed-proxy-evidence-03正归档（session95571），原始记录保留。

三资格独立原始复核independent-qualification-01/AUDIT.json passed：NK399实际我方请求=237Move+27End+81MakeAction+23Recruit+20Arrange+7Build+2QueryReply+1Save+1AdvReady，逐ID/owner/type均与真实统一ACK和DirectorACK一致。实际867发送=865真实ACK与atomic取消{866,867}并集，0我方取消；取消不是未执行证明。strategy-trace共同前1112行逐字节相同，旧仅多1条defeat后native_battle_ready，新正常退出未消费该尾部通知，不是此前动作/经济轨迹变更。报告INDEPENDENT_QUALIFICATION_REVIEW.md。
native-evidence-01归档已passed：3capsule各238普通文件、3资格2553普通文件+12链接，共3267普通文件SHA验证，Linux原件保留。idle-after-paired-03.json确认原V8/冻结五文件SHA全一致、无游戏/学习器/GPUcompute、双锁可独占、swap0、MemAvailable约15.56GB。root另委派全新双英雄供应支线实现隔离脚本控制器候选/协议与CPU测试，仅准备，无共享编译/native/GPU；不是已实现运输AI或学习。

failed-proxy-evidence-03归档最终passed，4659记录，explicit experiment_passed=false、0评分/训练。

人类战术独立支线真实新试验：human-tactics-positive-exchange-v2在新种子2026111801/02、2 TRAIN图×攻守×原生teacher2/positive脚本，共16局全部正常完成、0非法/截断，340动作完整严格事件窗口。positive门禁仅保留估计net>0且比baseline高>1 permille的普通近战候选，公共当前图输入，无事件/seed/未来RNG入策略；不称人类专家。冻结31工件逐步SHA检查，原战斗环境未改，pool串行、0GPU/optimizer/BC。最外launch在16局后CPU audit因父进程缺vcmi_gym PYTHONPATH exit1，保留此工程缺口；未改运行输入、未重跑游戏，用显式同runtime PYTHONPATH/LD_LIBRARY_PATH直接跑冻结audit_native.py exit0。AUDIT.json真实重算全部动作/原生终局：teacher4/8、candidate3/8，2override仅1fixture/role，主力与总永久损失各合计+4（每配对均值+0.5），fixture1 defender seed1801基线胜→候选负，1802同胜但多损失1主力。预注册门槛false，明确拒绝推进/训练/专家认证，0新合格课程。独立agent另目录复核raw和失败因果，不加种子冲淡负结果。战略v4仅CPU修parser，终局native capsule03不重编。双英雄候选也仅隔离准备。

战略v4审核器现已冻结，原生仍同capsule03/atomic-v3，不重编。只允许统一ACK的NEUTRAL=-1且pack198/真实较早同ID发送10MakeAction；Director注册/ACK仍owned0/1，-2/-3/-4等拒绝。28registry+5wholegame+17neutral假fixture反例过。read-only-requalification-01/AUDIT.json四raw全pass，0新native：旧3资格和paired03/pair02a（489move+48auto、884 owned ACK、39实际neutral ACK、取消foreign1766不涉owned）。原paired03仍failed/unscored，绝不回改。新paired_proxy_drain_v4.py把该门禁/source/original_batch/games全部input/output SHA校验并冻结，已启动typed-clearance-proxy-paired-04，session92195；当前已完成6对，两Empty图四对双方胜，两train01 NK配对双方负，proxy仅多存活49→58天及14→28天，不是能力提升。最后两对仍以最终RESULT为准，不重启/改输入。

战术独立审计human-tactics-positive-exchange-v2-independent-audit/RESULTS.md、AUDIT_01/TRACE_EFFECTS_01/ARCHIVE_INVENTORY_01全完成：16摘要+16gz、21源码快照、31冻结输入逐SHA通过。两真实override均fixture1/defender step11，前事件/动作/公开图前缀精确相同；actor为我方主力ID5，baseline打敌主力ID2杀3并换血，candidate杀单兵ID0、下一真实状态teacher再杀单兵ID1，未削弱敌主力随后先手打我主力。说明一步正净值漏掉压制/行动机会成本，但后继RNG消费/占位改变，不能将+4永久损失全单因归首次选择。保留机制反证，0专家/BC，不立刻加阈值/种子救成绩。LAUNCHER_TRANSCRIPT_EXCERPT.txt为工具session78732真实错误摘录（非原重定向stderr），保留exit1与后续独立CPU audit exit0区别。

paired04最终完整passed，session92195结束：16真实正常局，model4/8、proxy5/8净+1、14实际override、0optimizer/训练/专家/finaltest。不是fresh heldout或模型提升。唯一翻转pair07 train02/blue/NK seed1007，baseline day28/196move负→proxy day42/397move胜。独立independent-paired-04/AUDIT与PREFIX_BINDING_AUDIT全16重审/原三层proof及raw前后SHA过：request1..63和action1..62逐字节同；首override63的真实release和native_action_sent行之间0 server moves，两边之前全部185服务端移动（含NPC）语义/次序一致。首下一request/非候选可见观测差异64；投影一致不等完整世界确定。pair02/03仍双方负，只多存活；5无override pair完整policy/movement相同。全16 MAX128 cap事件0、最高单回合13move，pair07 goal switches25/68、selected reversal13/13，不将长局当变强。报告v4/independent-paired-04/REVIEW.md。完整raw归档paired-evidence-04已passed：14975普通文件SHA+64链接，Linux原件保留。

下一战略实现转双英雄真实供应：strategic-multihero-supply-v1隔离script控制器+适配器，58 C++ CPU控制测试、33 sidecar/builder门禁及实际TU语法通过，0原生构建/游戏；未支持native恢复、招募/经济/持续补给，无模型调用。EndTurn早NewTurn/晚ACK、意外友军会面close-only、movement query中转兵等已源码复核。冻结交接与观测补丁消息交叉，agent需恢复v1最终manifest精确旧SHA，并在新v2仅加native日志镜像/真实town army观测；不可声称v1从未短暂编辑。此期间0build/native，原已运行输入未改。root在strategic-multihero-supply-native-v1新建独立有限库存fixture和默认plan-only runner，manifest地图SHA c2aa18bfef86cd58dc74cb498f482cb38c74f54d7f3087de9b417e92f665269d；尚未加载，不假设town army已生效。目标仅1次真实pickup/delivery/保留reserve/跨两ownturn与queryclose，不称完整game/安全存档或能力。等待v2最终源/独立专用auditor后root双锁build并验证。

双英雄源最终记录：v1已恢复四宣告SHA（V1_RESTORATION.json，root另核对manifest/driver）；新strategic-multihero-supply-v2行为controller与v1相同，只加真实DirectorSupplyEvent镜像、town army/visitor及每条actual_request完整原生payload观测。CPU58控制+33sidecar/builder+9观测mock、实际TU syntax全过，仍非native资格。v2 manifest=d096d6ff0a7a1476c09f7ecdf9a460eeccc5590997fa4a1f33e970659d7d3023，driver=f15cc494795d1ab89033523ea7fd8e9159f54cb631db0e0177ebdd075791baaf；最终plan06未执行。root现已启动scripted-supply-capsule-01实际双锁build，tool session62081，运行中不得改v2候选/manifest/driver；尚未完成或开始native游戏。root新run_native.py默认plan，execute控制ownturn cap只是partial工程stop，不假正常终局/安全存档；冻结完整编译工件和helper依赖，41脚本与实际载入线程身份仍必验。独立agent在新audit_supply.py准备部分事务完整前缀机制审核，不能复用schema4证明。下一步先等build精确恢复accepted V8通过，再默认plan核对与独立fixture实机，所有失败保留后分析修新版本。

scripted-supply-capsule-01最终真实build/exact恢复passed（session62081结束）；plan01 default prepare通过、0游戏。随后scripted-supply-native-01在同seed2026111901/新stockfixture运行约1秒，实际控制至ownturn6、-15部分stop，0game/winner/optimizer/训练/恢复资格，源码/全部编译输入SHA及41脚本/实际inode/lib/runServer线程全过。362 supply观察、91脚本send/90已ACK、1query/名义cycle1，不将partial exit0当物流资格。
真实原生反证：rq8/day1 town3 slot0的10pikeman入courier2 slot1；rq53/day3却把courier初始reserve slot0的3archer送main0，反留真实cargo10pikeman。主力最终5pikeman+3archer，信使10pikeman，townempty。专用独立native-review-04/AUDIT.json明确generic_transfer_mechanisms_qualified=true但cargo_goal_qualified=false/passed=false；rq54 QueryReply49/0真实query49 pop/destruct/ACK严格闭合，两个hero真实移动、跨ownturn1..6、配送后courier继续均证实，尾部rq98未完成单列，不假drain。Move/End以真实TypedActionApplied精确ID，Arrange/Query需真实received+visitor success唯一窗口+payload/army delta，ACK success不能单独证明真实apply。18CPU拒绝反例与“合法转兵但送错cargo”负例过，旧解析拒绝01/02证据保留。
该partial已归档partial-evidence-01：472普通SHA+4链接，明确whole_game=false/不因归档认证机制；capsule-evidence-01 240普通SHA过，Linux原件保留。旧v2已运行输入冻结不改。新strategic-multihero-supply-v3正实现显式initial reserve/picked/cargo/delivered ledger：只在真实pickup ACK登记、只交实际cargo整槽并保全reserve，同种合并无法全槽安全分开则close incomplete不split、不假成功；close ACK后才计successful job。新trace schema events-v3/epoch cargo-v3，开关仍scripted_supply_v1仅源兼容，未恢复旧epoch。root新run_native_cargo_v2.py和PLAN_CARGO_V2.md复用原fixture/seed作具体修复回归，旧runner/PLAN保持，尚未build/run新cargo版。当前无native/GPU/build live；agents仅CPU实现/审核，goal active。

2026-10-19凌晨续记（跨日，不改变goal）：双英雄首probe专用审核最终权威为native-review-06/AUDIT.json，source audit_supply.py SHA6fe41bfcd1c9333215cdac09a852b0f0146ec43932f3e4b29a9b033d80290aa9、报告397af7898116cdb5cf16d68f78cc6672fa44a386385fe57aefccf173baff8e76，90已完成事务/82真实moves、tail98未完；generic true/cargo false不变。审核01..05为开发中间历史报告、源已迭代且没有旧源快照，不能作为当前可复跑认证；没有篡改原生raw/已跑runtime。最终源和audit-cpu-05（20拒绝+partialtail+送错cargo负例）现冻结；说明SUPPLY_AUDIT_REVIEW.md。v3账本审核另新文件准备，不改旧final。货物和保留量按真实兵种计数证明，不声称追踪同种士兵个体身份；原reserve七槽有归档，转后至少保全初始各兵种数量，same-type合并/partial另CPU覆盖。新cargo程序尚未finalfreeze/build/run。

v3最终实际采用更保守逐槽ACK贡献：pickup只在真实ACK后记cargo_slots，交兵须整槽count完全等于该槽ACK贡献且初始reserve槽species/count仍在；不会把初始同种小槽错当cargo，也不声称追踪个体士兵。same-kind merge/外部重排或战损不被悄悄当合法配送。CPU89controller+41sidecar/builder+13实际trace mock与TU syntax过，仍非native资格；v3正式冻结manifest6d8f1c02189e61d9397428f6417a9ae90bfbb8075a807b9409ca5fd9ec1aa8fb，finalplan07。root已启动scripted-supply-cargo-capsule-01实际双锁build，session19138，尚未最终返回/新native运行。v3 schema events-v3、controller_epoch cargo-v3，恢复仍未支持；独立新audit_supply_cargo_v3.py准备中，旧06审核源不改。下一步等build精确恢复通过，使用新cargo runner/PLAN在同stockfixture/seed回归，不能把old first-slot配送当成功。

v3实机与独立资格已通过（限定部分运输机制）：session19138真实build及accepted V8 source/三bin重编译SHA精确恢复passed。新cargo-plan01默认prepare后，scripted-supply-cargo-native-01同fixture/seed真实执行至ownturn6、约1秒、partial -15，0game/winner/optimizer/训练/恢复资格。488 native镜像/file事件逐条一致，98完整脚本事务/89moves/99全部owned注册与真实ACK（含interface请求），11payload/41脚本/编译工件/实际lib inode与runServer线程/input SHA全过。
最终权威cargo-native-review-01/AUDIT.json SHA2fbdb694a13401a64cee484a0b2e635c3d7170a481566d2f54b02e929eabf62d，独立source audit_supply_cargo_v3.py SHA7990c1d59929a90fb77423405970697f6d0b5a3df94a5ef268ccc2954af2c725、cargo-audit-cpu04的15拒绝+positive/incompleteclose过且现冻结。真实rq8 pickup real_ack时cargo仍0，control_ack后才10；rq53整slot1的10pikeman进main slot0（5→15），real_ack时ledger仍10，control_ack后cargo0/delivered10且success仍0；rq54 QueryReply49/0实际query49 pop/destruct/真实serverapply，close real_ack仍success0，control_ack后才success1。courier原slot0 archer3全过程保全，town10→0，之后真实courier继续位移与跨ownturn1..6持久角色/任务通过。不凭successful_jobs布尔、不假未完尾部完成、不称整game/drain/恢复/收益。报告CARGO_V3_INDEPENDENT_REVIEW.md。新partial-cargo-evidence-01归档472普通SHA+4links、cargo-capsule-evidence-01 240普通SHA通过，Linux原件保留。当前无native/GPU/build live；下一缺口是持久控制native保存/加载整合、持续招募补给及完整战略多英雄学习，而非继续堆同图运输次数。

当前下一实施：新strategic-multihero-supply-v4原生控制恢复，agent已由followup_task正式启动（此前给idle agent的send_message只排队，不表示在执行）。root与两agent分别交叉读实际API纠正旧笼统结论：PlayerState.playerLocalSettings确实被CPlayerState.h126序列化，SaveLocalState真实server写该字段，cb->getPlayerState可读，CPlayerInterface已有加载deserialize示例；缺的是Director人工写入/读取控制，不是原生不可保存。新路线namespace完整controller JSON→真实SaveLocalState ACK→SaveGame真实ACK及file/header/SHA/成功marker→reference直接继续，不在callback等待外部release或自己通用ACK；root后续据snapshot和稳定save建原子外部bundle，fresh --testsave从native嵌入payload校验并hydrate，外部sidecar不能伪装native状态。SaveGame visitor即使gh.save内部catch失败仍ACK1，故不能仅ACK认证save成功。
checkpoint计划在turn2实际cargo10已pickup未deliver、并至少本轮1script动作已真实ACK的干净边界，验证非零spent/cursor/visited/task不被reset；首次load的yourTurn由TurnOrder onGameStarted重发，必须作为resume通知，不能++ownturn/清budget/重选roles。原savefrequency1没生成任何vsgm1，须主动SaveGame。当前v4尚在CPU实现/独立审计框架阶段，未finalfreeze/build/native，不宣称恢复通过；v3和全部旧runner/auditor/proof已冻结。idle-after-cargo-01.json再次确认accepted V8/五冻结SHA全过，双锁独占、native/learner/GPUcompute0、swap0、MemAvailable15.61GB。goal active。
