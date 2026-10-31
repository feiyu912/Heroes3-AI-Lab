# Heroes III — Human Expert Knowledge & Demonstration Pipeline：试点交付

记录日期：2026-10-16。初稿已完成公开来源筛选、候选目录、一个来源支持的真实VCMI规则与局部收益复现，以及4条首步示范。初稿时来源BC及独立测试尚未完成；后续已取得真实CUDA BC与训练标签离线拟合证据，见文末更新。**独立测试仍待完整报告，不能宣称模型已掌握可迁移技巧。** 本报告不替代普通BattleAI/MMAI胜率评测。

## 1. 专家资料目录与筛选标准

[registry.json](G:/Heroes3-AI-Lab/experiments/expert-knowledge-v1/registry.json) 收录11条来源记录，覆盖阿青Hero3、英雄无敌3狂小Z、给我一杯咖啡好吗、Lexiav、Richard Hallas及机核作者v翼。这里计的是“来源记录”，不是11位高手或11条有效示范；同一作者可能有多个来源。

每条保存链接、作者、可取得的发布时间、版本、资料类型、主题、访问范围、未知字段与许可状态。日期或版本未查明的内容保留null。按原始出处、可定位证据、规则可验证性和当前接口适用性筛选，不用播放量推断正确性。证据等级区分频道识别E0、元数据/章节E1、实际读到的明确作者文字E2、经核验的真人结构轨迹E3、固定引擎复现E4；不能把较高一级的实验结果倒填为低一级材料的原始内容。

阿青是重点研究来源，已取得“片伤远程发呆”“无失明假控制”“巧用龙息”等关联合集章节线索，但没有取得这些片段的具体操作轨迹、可靠时间位置或完整字幕。Lexiav当前仅确认频道入口。详见 [来源与候选说明](G:/Heroes3-AI-Lab/experiments/expert-knowledge-v1/SOURCES_AND_PILOTS.md)。

## 2. 战术知识记录格式

[TACTIC_KNOWLEDGE_FORMAT.md](G:/Heroes3-AI-Lab/experiments/expert-knowledge-v1/TACTIC_KNOWLEDGE_FORMAT.md) 定义来源、位置、目标、条件、机制、操作、收益原因、失败、正反方向、对手应对、版本、未知状态、置信度、证据及划分字段。

已填写的实例是 [source_wait_case.json](G:/Heroes3-AI-Lab/experiments/expert-knowledge-v1/source_wait_case.json) 和 [source_case.json](G:/Heroes3-AI-Lab/experiments/expert-knowledge-v1/source_case.json)。原始来源记录与实验结果分开保存，已冻结来源中的pending不由后来实验静默改写。动作图数据接口见 [DATA_CONTRACT.md](G:/Heroes3-AI-Lab/experiments/expert-knowledge-v1/wait-variant-v2/DATA_CONTRACT.md)。无法确定的兵力、坐标、技能、随机种子和版本不能编造。

## 3. 15个试点候选

机器清单及逐条失败条件、验证方案、来源定位见 [pilots.json](G:/Heroes3-AI-Lab/experiments/expert-knowledge-v1/pilots.json)。

|编号|候选|当前证据与范围|
|---|---|---|
|P01|诱导龙反击误伤友军|Hallas明确文字；实际反击友伤事件尚未复现|
|P02|己方龙站位防喷吐反击陷阱|Hallas明确建议；反制尚未实测|
|P03|护射手与片伤防守取舍|Hallas明确文字；来源专项未完成|
|P04|最快兵等待形成跨轮连续行动|已完成下述8组真实配对试点|
|P05|被贴射手等待友军解围后射击|Hallas明确文字；待重建|
|P06|射手分散避免一兵同时封两队|Hallas明确文字；待重建|
|P07|速度差风筝|v翼文字建议；待固定规则执行|
|P08|片伤射手价值判断导致发呆|阿青章节线索；没有操作证据|
|P09|无失明站位价值绑定假控制|阿青章节线索；旧AI适用性未知|
|P10|禁魔法大地精灵站位及游击|阿青章节线索；战斗/大地图需区分|
|P11|基础兵种机制交叉核验|狂小Z教程元数据；具体技巧待定位|
|P12|要塞防守与反制实例|咖啡教程元数据；具体技巧待定位|
|P13|竞技实战的操作与应对|Lexiav频道线索；具体VOD/轨迹未取得|
|P14|兵链、支点与一兵多用|战略档案，等大地图接口|
|P15|飞跳回、技能和经济评价|战略/主动魔法延期|

以上是候选，不是15条已验证专家轨迹。P11–P13尚需形成明确战术主张，不能直接用于训练。

## 4. 一个真实来源支持的VCMI复现案例

实际读取了Richard Hallas于2001-08-27发表的 [Heroes III Complete Strategy Guide第5页](https://www.insidemacgames.com/historical/features/view.php%3FID%3D64%26Page%3D5.html)，其Waiting to attack段明确讨论等待逆速度顺序及最快单位跨轮连续行动。Hallas是具名实质攻略作者；其职业选手身份、赛事成绩没有核验，不能称为认证职业高手录像。

采用幽灵龙与行尸的无主动英雄魔法局面。兵种、兵力、站位、英雄属性、种子和脚本回应均由实验室新建，**不是从该教程恢复出的历史战局**。4组训练兵力为幽灵龙4/6/8/10对行尸80/100/120/140，各交换攻守。

实际完成8组WAIT/直接行动配对，共16局，全部正常终局、0非法动作，8组均观察到跨轮连续行动窗口。前4组双方均损失1条幽灵龙，没有收益；后4组WAIT损失1条、直接行动损失2条，双方都获胜。无收益实验和原始状态均保留，没有只展示正例。报告为 [wait-train-comparison.json](G:/Heroes3-AI-Lab/experiments/expert-knowledge-v1/wait-variant-v2/wait-train-comparison.json)，对应逐局记录位于同目录wait-runs。

[dataset-audit.json](G:/Heroes3-AI-Lab/experiments/expert-knowledge-v1/wait-variant-v2/dataset-audit.json) 已核对原始结算、动作合法性、正例来源及文件哈希。幽灵龙老化和伤害随机性尚未做事件级因果隔离；相同种子下不同动作可改变随机数消耗。因此当前证明规则窗口和配对观察收益，**不是无混杂的纯等待收益因果证明**。同一种亡灵对局及固定脚本也不能证明通用策略迁移。

原先恐怖骑士的低速度重建及本试点无收益组都说明：机制成立不保证策略更好。多堆围攻v3已预先冻结，但因v2取得局部正例而保持未运行，没有冒称反制或围攻验证通过。

## 5. 专家动作及对抗场景如何产生

[candidate-bc-train.jsonl](G:/Heroes3-AI-Lab/experiments/expert-knowledge-v1/wait-variant-v2/candidate-bc-train.jsonl) 当前有4条示范，只取实测有收益配对的**第一步合法WAIT**，没有把后续greedy动作全标为专家最优。记录保留原始状态图、合法动作ID、选中动作、攻守方、来源、对照和混杂限制。它们属于experimental reconstruction，不属于human-recorded replay。

完整划分已冻结为 [all-source-wait-scenarios.json](G:/Heroes3-AI-Lab/experiments/expert-knowledge-v1/wait-variant-v2/all-source-wait-scenarios.json)：8训练、4开发、4测试。开发和测试在本交付记录形成时尚未执行。各划分为不同兵力和种子，仍是同一兵种家族，测试结论必须限定这个范围。

|方向|已完成|待实际执行|
|---|---|---|
|Offense：主动利用等待|8组规则窗口、4条局部收益首步标签|冻结模型后验证动作、伤亡和胜负变化|
|Defense：识别并反制等待|已列条件与反制假设|守位、主动等待、换目标、射击惩罚、无速度优势等响应的真实对照|
|防误学|保留无收益组；训练输入限制为合法train正例|将无收益/反效果局面加入选择性等待评测，防止学成总按WAIT|

反制方法目前是可执行的实验方案，尚无反制成功数据。下一步可复用同一双环境接口，为对方提供固定守位/等待/换目标脚本，预先冻结响应策略及新变体，再比较收益是否消失；不能把尚未运行的脚本称为验证过的专家对手。

## 6. 与当前PPO系统集成

保留现有模型结构、正式PPO任务、存档及BattleAI/MMAI基线。来源试点BC在隔离目录从B64模型初始化，仅调整策略头，图编码和价值头逐位保持。初稿时尚未取得该BC完成证据；后续完成与训练拟合结果见文末。训练损失降低仍不能代替动作或独立测试改善。

`train_source_wait.py`已补齐数据和运行门禁：启动前冻结输入及源码副本，等待资源锁期间变更会被拒绝；正标签需对应train原始正常终局与实际收益；模型冻结后校验权重、来源、数据、测试定义及每张地图；模型窗口由实际决策重算，缓存不能重新贴成别的模型结果。[source-pipeline-gate-check.json](G:/Heroes3-AI-Lab/experiments/expert-knowledge-v1/wait-variant-v2/source-pipeline-gate-check.json) 的CPU检查已拒绝7类篡改，未启动GPU或游戏；这是门禁证据，不是BC学习成功证据。

后续顺序为：完成隔离BC → 固定模型及规则 → 运行既定8个基线/新模型测试局 → 报告首动作、真实窗口、伤亡及胜负 → 对普通战斗和作者模型做回退检查。当前没有把PPO基线胜率改善归因于来源课程。若BC无行为改善或存在回退，应如实保留结果，再用训练/开发数据调整；已经查看的测试集不能继续当成全新确认测试。

PPO接入只使用训练划分，逐步混入经核验专家对抗局面，同时保留普通战斗与原作者对手，监测遗忘。课程加入比例、BC权重、KL保留项等需要开发集实测后冻结；不因课程“看起来合理”直接替换正式模型。

## 7. 暂不支持、版本差异和版权边界

当前v15战斗试点不支持主动英雄施法。露娜火墙、失明、镜像等先延期；兵链、经济、技能选择和飞跳回独立归战略知识库。龙反击友伤仍缺事件级复现，不能拿现有主动范围攻击标签冒充该案例。

Complete、SoD、HotA与固定VCMI版本分别记录。现有复现只核对特定等待顺序与局部终局；没有证明所有版本机制相同。旧AI估值发呆套路也不代表当前BattleAI或MMAI有同样缺陷。幽灵龙没有喷吐，本试点不声称验证龙息规则。

B站直接读取遇到HTTP412/失败，因此只使用公开索引可见元数据；YouTube/Twitch只返回频道外壳。没有绕过限制，没有下载或再分发视频，没有取得完整字幕或真实高手结构轨迹。公开可读不等于取得整段视频/字幕的再分发或训练许可，许可未知的媒体不批量采集。

进一步开展阿青、Lexiav等真实操作提取，需要合法可访问且可定位的讲解文本、字幕或获许可的存档/回放；若状态无法确定，继续标注未知，不从视频坐标猜出“已验证动作”。现有文字来源可先推进机制与重建闭环，但不能宣称已经完成视频理解、职业轨迹抽取、反制验证或通用人类战术学习。

## 后续更新：真实BC完成，4个训练标签部分拟合

[source-bc-training.json](G:/Heroes3-AI-Lab/experiments/expert-knowledge-v1/wait-variant-v2/source-bc-training.json) 记录真实CUDA策略头BC完成60步，使用4条训练示范，NLL由9.8438759降至1.8457727。模型SHA为 `839d7747c8a058aa0a34af329f199dcc5cd6d598d76db7b084b84330d8eb63e1`。

独立的 [offline_source_fit_audit.py](G:/Heroes3-AI-Lab/experiments/expert-knowledge-v1/offline_source_fit_audit.py) 仅用CPU读取初始模型、新模型及原4条train标签，没有读取测试状态或测试输出，没有反传、优化器、CUDA或游戏。它按相同4条批次复算图编码与策略头，并核对数据、模型和冻结codec/图模型SHA。结果保存在 [source-training-fit-audit.json](G:/Heroes3-AI-Lab/experiments/expert-knowledge-v1/wait-variant-v2/source-training-fit-audit.json)。

|训练条件|WAIT概率，训练前→后|WAIT排名，前→后|
|---|---|---|
|幽灵龙8对行尸120，进攻|98.996%→99.957%|1→1|
|幽灵龙8对行尸120，防守|3.733×10⁻⁸→3.482%|13→1|
|幽灵龙10对行尸140，进攻|25.652%→92.633%|2→1|
|幽灵龙10对行尸140，防守|8.369×10⁻¹⁰→1.928%|43→8|

训练标签argmax命中由1/4增至3/4；仍有一条没有成为最高概率动作。防守8龙局面虽升至第一名，概率也仅3.48%，不能称为高置信度选择。CPU重算NLL为9.84385395→1.84577227，与CUDA报告分别相差2.19×10⁻⁵、4.77×10⁻⁷，均通过2×10⁻⁴绝对容差。

这证明模型在4个训练状态上确实改变了动作分布并部分拟合标签；不是4条全部学会，也不是独立战损、通用迁移或反制能力得到证明。冻结后的8个模型测试局仍由单独管线完成和汇报，本次离线审计不读取其中途或最终输出。
