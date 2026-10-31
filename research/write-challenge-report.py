import datetime
import hashlib
import json
from pathlib import Path

root=Path('/mnt/g/Heroes3-AI-Lab');r=root/'research'
data=json.loads((r/'CHALLENGE_RESULTS.json').read_text())
selection=data['selection'];fresh={row['name']:row for row in data['fresh_results']}
labels={'fresh-upstream-vs-battleai':'作者公开 v15 → BattleAI','fresh-v3-vs-battleai':'原模型 v3 → BattleAI',
        'fresh-selected-vs-battleai':'当前选定模型 → BattleAI','fresh-selected-vs-upstream':'当前选定模型 → 作者 v15',
        'fresh-v3-vs-upstream':'原模型 v3 → 作者 v15','fresh-battleai-vs-battleai':'BattleAI → BattleAI'}
rows=[]
for name,label in labels.items():
    row=fresh[name];s=row['summary'][0];ci=row['scenario_cluster95']
    rows.append(f"| {label} | {s['wins']}/{s['battles']} | {s['win_rate']:.1%} | {ci[0]:.1%}–{ci[1]:.1%} | {s['truncated']} |")
concurrency=json.loads((r/'challenge-concurrency-results.json').read_text())
objective=data['objectives']
base='超过50%' if objective['beat_upstream_point_estimate'] else '没有超过50%'
proof='场景聚类区间下界也超过50%' if objective['beat_upstream_cluster95_lower_above_half'] else '场景聚类区间尚不能支持稳定超过50%'
near='达到' if objective['near100_defined_as_at_least95_percent'] else '未达到'
date=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(timespec='minutes')
text=f'''# 公开 MMAI 对战与24并发训练结果

完成时间：{date}。本报告记录真实游戏引擎结果，不把截断算成胜利。

## 直接结论

选定模型对作者公开模型的胜率{base}，{proof}。对 BattleAI 的“接近100%”指标（本轮预先定义为至少95%）{near}。这描述指定普通战斗测试，不能推广为完整英雄无敌III或对人类的胜率。

最终候选：`{selection['name']}`，策略类型 `{selection['policy']}`；根据两种对手的验证结果选择，未用最后512场测试选模型。原模型与原版上游模型也作为候选，避免强行采用退步模型。

## 公平共同基准

新测试为32套未参与训练/选择的双方完全相同军队及部署，每套交换攻守、8个构造随机种子，每项512局。6套兵种组合与训练相同，另外2套升级兵组合未在训练出现；场地仍为普通无障碍战场，最多三队兵种，无主动魔法/攻城。军队数量与部署不存在与旧课程的完全重复，审计见 `research/challenge-holdout-audit.json`。

| 对战 | 胜局 | 胜率 | 场景聚类95%区间 | 截断 |
|---|---:|---:|---:|---:|
'''+ '\n'.join(rows)+f'''

各场景、所有胜负及失败均保存在 research/CHALLENGE_RESULTS.json 和 fresh-*.json。区间按场景重采样，避免把同一军队的多个种子当作完全独立的军队；本轮每条训练路线仅一个新训练种子，仍不能代表训练随机性的全部范围。

旧160场诊断对照：作者 v15 对 BattleAI99/160=61.875%；原 v3 对 BattleAI88/160=55%；原 v3 直接对作者47/160=29.375%；作者自对战80/160=50%。它们已被用来设计后续研发，因此最终能力结论以这套新512场测试为主。

## 实际改进与训练

1. 下载作者正式发布的 v2.0/v15 攻方、守方 ONNX 模型，按模型元数据恢复关系顺序，并核对合法动作、概率归一化和动作输出。原生与Python交换控制端的终局伤亡一致；完整160场自对战50%。来源、大小与SHA256见 upstream-model-manifest.json。公开权重是否正好是日志89%成绩的那一份未独立确认。
2. 现有简化GNN补充候选动作关联的出招单位、主目标及第一个落点embedding，从原验证选定模型初始化；扩展初始输出与价值预测保持一致。仍使用聚合关系，尚未完整处理每种边属性；多目标原始特征保留，embedding采用主目标。
3. 增强与原网络各新增393216个PPO采样。原网络途中按用户要求从12/roll64切换24/roll32，保存并恢复进度；两者采样预算相同，但这项比较不能称为纯架构消融。
4. 继续24并发混合 BattleAI/作者模型训练；保持所有模型选取依据来自验证场景。失败的训练会保留日志并排除，不能冒充完整结果。
5. 将作者两个公开网络从ONNX参数恢复为可训练的Torch网络，分别约450万参数；动作概率、价值、批量图偏移及梯度检查通过。在保留完整有类型图编码器的基础上，用PPO调整策略/价值头，同时设置每个己方行动-0.002的轻微时间成本，鼓励收尾；胜负仍为+1/-1，人工截断仍用最终观测bootstrap。它是基于作者权重的继续训练，不是从零训练的原创模型；本轮未解冻整个图编码器，也不是仅改变一个因素的消融。

Masked PPO仍是算法；对手池、状态关联与预训练起点已经改变。仅凭网络利用率或一次失败不能判定必须换算法。后续应根据逐场失败定位，再决定扩大课程、奖励/历史自对战池、解冻图网络，或研究搜索与策略训练结合。

##24并发与GPU

游戏规则/每个VCMI实例运行在CPU、占普通内存；正式训练中己方模型推理及PPO更新运行在GPU、占显存。对战评测的模型推理以及训练中的原生作者模型对手推理仍在CPU。最初历史闭环是CPU；本轮正式继续训练使用GPU，但评测期间GPU可以接近空闲。显存空闲不意味着CPU游戏实例也可以放进显存。

恢复的两个作者网络共约899万参数，但本轮冻结图编码器，仅更新约10万参数的策略/价值头。GPU还会运行图编码推理，更新负载较小；与作者模型对战时，CPU对手推理和规则推进限制数据生成速度，所以CUDA确实工作与整体GPU利用率较低可以同时成立。

相同模型、相同三队兵种场景的完整训练测得12/16/20/24/32并发中位吞吐约339/394/418/465/490次决策每秒。24比12快约37%；32提升较小且占更多内存。40触发运行时2GiB内存余量检查并清理退出；48没有启动。当前WSL内存上限约16GiB，无交换内存的有效配置才被接受。用户最终指定24，后续正式训练固定24；不是为了填满显存扩大无益的模型。

更大的上游图网络的独立实际训练吞吐见 recovered-speed-grid.json，不能用小模型的465直接替代。吞吐变化也不等于学习能力增长。

## 交付与能力边界

最终权重、验证选择依据及来源放在 models/challenge-v4，完整实验配置和日志在 research。主指令的Decision Model普通战斗链路已实现并控制真实战斗；完整英雄/主动魔法、攻城、地图战略、1对7与可视化游戏中直接使用的完整集成尚未完成。

来源：[作者公开模型仓库](https://github.com/vcmi-mods/mmai)、[公开v2.0权重](https://github.com/smanolloff/vcmi-gym/releases/tag/v2.0)、[研发日志](https://smanolloff.github.io/projects/vcmi-gym/)。作者报告与本机复现分开记录。
'''
text=text.replace('##24','## 24')
text=text.replace('对战评测的模型推理以及训练中的原生作者模型对手推理仍在CPU','标准对战评测使用CPU推理；初始训练的原生作者模型对手也在CPU，后续集中GPU对手方案另行验收')
if (r/'goal-v5-validation.json').exists():
    experiments=json.loads((r/'goal-v5-validation.json').read_text())
    table=['| 候选 | 旧验证 BattleAI / 作者 | 多样化开发 BattleAI / 作者 |', '|---|---:|---:|']
    for experiment in experiments:
        table.append(f"| {experiment['name']} | {experiment['validation']['win_rate']:.1%} / {experiment['upstream_validation']['win_rate']:.1%} | {experiment['development_validation']['win_rate']:.1%} / {experiment['development_upstream_validation']['win_rate']:.1%} |")
    extension='\n\n## 扩展课程与图网络继续训练\n\n'+('\n'.join(table))+'\n\n训练课程扩大至192套完全镜像军队，另有48套开发场景；每次候选对比使用其中预定12套开发场景。兵种数量、部署槽位及兵种排列随机变化，每阶段攻守与对手类型均衡覆盖。使用折扣一致的兵力价值势函数，正常终局势函数置零；不会把终局胜负或老师动作放入策略输入。\n\n分别训练输出头、最后图层和全部图网络，最后图层路线约108万可训练参数，全部网络约899万参数。各阶段仍是Masked PPO，并不宣称是单变量消融或多个随机种子上的稳定结论。最终候选按两个验证集合、两种对手的最弱胜率选择，独立测试从未用于候选选择。\n\n最终候选训练模式：'+selection.get('finetuning_mode','lab-gnn')+'。显存/用时及实际训练规模见v5-*.json；GPU对手集中推理原型未通过一致性验收，未接入正式实验。\n'
    text=text.replace('本轮未解冻整个图编码器','最初恢复阶段未解冻图编码器；后续扩展实验另行比较解冻范围')
    text=text.replace('但本轮冻结图编码器，仅更新约10万参数的策略/价值头','最初恢复阶段冻结图编码器，仅更新约10万参数的策略/价值头；后续扩展实验另行训练最后图层或全部网络')
    text+=extension
    if 'goal_selection_metrics' in selection:
        if selection['goal_selection_metrics'].get('rule_version')==2:
            text+='\n## 选择规则与目标一致性\n\n最初目标归一化仍把旧压力局和镜像开发局同时纳入最弱进度。最后图层64/128轮的取舍表明，这可能优先选择兵力不等压力局更强、镜像胜率更低的存档，因此在最终测试前将主要选择依据对齐到等兵力开发集：BattleAI至少95%，且对作者的场景聚类95%下界严格大于50%；两者满足后优先BattleAI更接近100%，尚未满足时最大化两项目标的最弱相对进度。旧压力局保留为诊断及打破平局的依据，所有旧成绩仍保留。最终32套场景、每项512场及成功门槛均未改变。此调整依据验证反馈，详见goal-selection-mirror-alignment.json，不宣称从实验最开始就预注册；已经开始的训练保持原初始化和优化器轨迹。\n'
        else:
            text+='\n## 选择规则与目标一致性\n\n输出头中期探索后调整为旧/新开发集共同的目标归一化选择，独立测试门槛保持不变；这是验证驱动的调整，不宣称从实验开始就预注册。\n'
if (r/'central-opponent-throughput.json').exists():
    choice=json.loads((r/'central-opponent-throughput.json').read_text())
    text+='\n## 集中GPU对手采集\n\n原双环境原型的差异来自额外的启动重置；对齐首次战斗后，重新核对完整公开图（节点、规范化边、合法动作）及连续多场动作/结局，并检查CPU和GPU概率。关闭流程在父进程确认后结束独立游戏进程，避免双线程关闭竞态。训练对手权重独立冻结，每轮检查其参数版本；它仍是作者公开模型，没有替换为更弱对手。\n\n'
    text+=('24并发的两次完整采样/更新测试通过，后续训练采用集中GPU对手；包含启动开销、按16轮正式周期外推的吞吐提升约'+f"{choice['estimated_end_to_end_speedup']:.2f}"+'倍。这是外推估计，正式图网络训练的实际吞吐见各训练JSON。' if choice.get('use_central_gpu') else '集中GPU对手方案未满足正式采用条件，后续保留CPU对手；失败日志不计为成功训练。')
    text+=' 最终共同基准仍使用原来的原生CPU作者模型对手，不改变测试规则。\n'
    if choice.get('use_central_gpu'):
        text=text.replace('GPU对手集中推理原型未通过一致性验收，未接入正式实验。','集中GPU对手通过后续一致性与性能验收后，已用于正式图网络训练，详见下文。')
text=text.replace('最终候选按两个验证集合、两种对手的最弱胜率选择','最终候选按本报告后述的目标归一化验证规则选择')
if (r/'full-graph-cuda-recompute-contract.json').exists():
    numerical=json.loads((r/'full-graph-cuda-recompute-contract.json').read_text())
    if numerical.get('deterministic_rollout_batch_exact'):
        text+='\n## 完整图网络数值复核与恢复\n\n最后图层第115轮更新前，GPU图聚合的非确定性求和及不同批量形状产生0.00024414的log概率重算差异，超过2e-4检查阈值。完整112轮优化器/RNG存档保留，113/114两轮未保存工作丢弃，失败报告与日志归档。修复采用确定性CUDA并按原采样24批量进行更新前重算，保留更新微批量和原2e-4阈值；未跳过检查。64个不同训练观测分别通过双角色网络，三次同24批量重算误差为0，全部图层梯度也通过。原生/集中对手另做36局完整状态、动作与结局一致性验证。确定性计算有额外时间成本，早期非确定性性能测试的加速估算不能当成完整训练的新实测速度；实际用时与误差记录见各阶段JSON。\n'
if (r/'post-training-candidates-plan.json').exists():
    text+='\n## 冻结测试前的候选组合对照\n\n最后图层64/128轮出现对BattleAI与作者模型的取舍，故在任何新独立测试之前增加验证候选：按角色组合独立网络，以及对验证目标领先者和BattleAI领先者做25%/50%/75%权重插值。候选全部使用原来的四项48场真实验证；插值方法由视觉领域的[Model Soups研究](https://proceedings.mlr.press/v162/wortsman22a.html)提供动机，其论文并不证明本强化学习任务会受益。最终选择仍使用同一目标归一化规则，候选未胜出也保留成绩。最终测试在候选选择与原生兼容验证完成后才释放。\n'
    if selection.get('finetuning_mode')=='derived':
        text+='\n选中的是组合权重，属于父网络的算术衍生，没有凭空增加训练采样。完整配方、父存档SHA256及组合系数见其derivation_manifest。权重可重载并继续训练所有图层；组合没有单条原始优化器轨迹，因此继续训练采用新优化器，父模型原始优化器存档仍保留。\n'
native_path=root/'models/goal-v5-native-selected/manifest.json'
if native_path.exists():
    native=json.loads(native_path.read_text())
    if (not native.get('needs_numeric_and_live_validation',True) and native.get('validation',{}).get('passed')
        and native['checkpoint_sha256']==hashlib.sha256(Path(selection['checkpoint']).read_bytes()).hexdigest()):
        text+='\n## 选定模型的原生导出验证\n\n选定存档已导出为攻方/守方v15 ONNX。在WSL原生引擎的6局训练场景中加载导出模型，每次受控决策比较Torch/ONNX概率、价值与贪心动作，全部通过且正常结束。这项检查证明该无界面引擎下的导出兼容性，不作为强度成绩；最终胜率仍来自独立512场测试。模型与验证清单位于models/goal-v5-native-selected。\n'
if (r/'neutral-mirror-fixtures-audit.json').exists():
    audit=json.loads((r/'neutral-mirror-fixtures-audit.json').read_text())
    if audit['passed']:
        text+='\n## 镜像条件与实际引擎边界\n\n静态检查了272张多样化课程及独立测试地图：双方兵种、数量与槽位相同，全部英雄四项主属性设为0，无额外技能、装备和特长，且使用同一职业的ML中性英雄。检查实际ML英雄定义文件而非仅比较军队列表；该审计只读取地图与模组配置，没有读取最终胜负。\n\n沿用上游v15的30回合保护与400行动上限，非正常结束和截断不计胜利。后续评测在模型、地图和Python代码之外，还冻结实际原生游戏库、v15连接器/导出器、ONNX Runtime及ML英雄定义的SHA256，并在结束后复核；早期历史评测保留当时较小的冻结清单，不追认为包含这些新增文件。\n'
text=text.replace('另外2套升级兵组合未在训练出现','另外2套升级兵组合未在本轮新增训练课程出现；公开预训练阶段的接触情况未核实')
if (r/'tactical-curriculum-audit.json').exists():
    tactical=json.loads((r/'tactical-curriculum-audit.json').read_text())
    if tactical.get('passed'):
        text+='\n## 人类战术与当前训练的区别\n\n本次正式A/B/C路线从公开预训练模型继续做PPO，并未加入用户录像、人工战术动作标签或专门战术示范。训练按合法动作概率探索，验证使用贪心动作；这不等于从零均匀乱走，也不能证明模型已掌握保护射手、骗反击或等待抢行动顺序。\n\n另已准备120张四队镜像战术练习地图（96训练、24开发），涵盖保护射手、少量兵反击诱饵和分队集火。它们未用于本次A/B/C参数更新，初始拆兵由地图提供；策略本身没有战前拆兵动作。新地图与VIPBot完成6局运行检查，该检查不作为独立强度成绩，也不纳入本次候选选择。\n'
        if (r/'tactical-trace-review.json').exists():
            text+='\n战术记录工具已保存训练地图上一局真实BattleAI对战的逐步完整图状态与合法动作，重复两次轨迹一致，便于后续核对具体行为。单位行号只在单个观测内有效，图中未直接提供持久单位ID或明确反击次数；两次己方观测之间还包含对方行动，因此当前记录不构成战术掌握或因果收益的证明。仅凭WAIT次数、1兵队存在或整体胜率，不能宣称学会人类技巧。见research/tactical-trace-review.json。\n'
(root/'CHALLENGE_RESULTS.md').write_text(text)
print('Saved readable challenge report')
