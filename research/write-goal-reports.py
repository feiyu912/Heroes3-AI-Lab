"""Publish the completed initial V2 experiment suite, including negative results."""
from pathlib import Path
import hashlib
import json
import shutil
import statistics

root = Path('/mnt/g/Heroes3-AI-Lab')
research = root / 'research'


def read(name):
    return json.loads((research / name).read_text(encoding='utf-8-sig'))


def publish(name, text):
    path = root / name
    history = research / 'history-before-goal'
    history.mkdir(exist_ok=True)
    if path.exists() and not (history / name).exists():
        shutil.copy2(path, history / name)
    path.write_text(text, encoding='utf-8')


results = read('GOAL_RESULTS.json')
suite = read('ppo-research-suite.json')
assert len(suite) == 10 and sum(r['steps'] for r in suite) == 983040
selection = read('selected-trained-model.json')
selected_training = json.loads(Path(selection['training_report']).read_text())
fixed_grid = read('training-device-grid-fixed.json')
quality = json.loads(Path('/root/heroes3-ai-lab/datasets/teacher-balanced-v1/manifest.json').read_text())
audit = read('teacher-label-audit.json')
bc = read('bc-balanced-v1.json')
ablation = read('bc-balanced-ablation-v1.json')
rows = []
for run in suite:
    train = json.loads(Path(run['training_report']).read_text())
    assert train['completed'] and train['all_workers_exit_zero']
    validation = json.loads(Path(run['validation_report']).read_text())['summary'][0]
    test = run['summary']
    rows.append(dict(name=run['name'], samples=run['steps'], updates=len(train['records']),
                     validation=validation, test=test, wall_seconds=train['wall_seconds'],
                     effective_steps_per_second=run['steps']/train['wall_seconds'],
                     pss_peak_mib=train['sampled_peak_total_pss_mib'],
                     gpu_peak_allocated_mib=train['gpu_peak_allocated_mib'],
                     episodes=train['records'][-1]['episodes_total'],
                     training_truncations=train['records'][-1]['truncations_total']))
table = ['| 对照 | 采样步 | 更新次数 | 验证胜率48场 | 测试胜率160场 | 正常终局平均损失单位数 |',
         '|---|---:|---:|---:|---:|---:|']
for row in rows:
    table.append(f"| {row['name']} | {row['samples']:,} | {row['updates']} | {row['validation']['win_rate']:.1%} | {row['test']['win_rate']:.1%} | {row['test']['mean_permanent_units_lost']:.2f} |")

publish('TRAINING_THROUGHPUT.md', '# GPU与完整训练实测\n\n2026-10-14。本轮全部正式训练固定12环境，中央GPU推理/更新，游戏规则模拟仍由CPU运行。\n\n' + '\n'.join(table) + f'''

十组每组98,304步，合计983,040步。3个独立训练种子、终局战损率塑形、混合对手、rollout32/64、batch64/128、epoch3/1及MLP/Attention/GNN均实际运行；各自保持同采样预算。混合对手为BattleAI/StupidAI/随机合法各1/3。所有有效正式训练退出正常，损失/梯度有限，掩码与旧log-prob重算通过。最大训练PSS采样峰值{max(r['pss_peak_mib'] for r in rows)/1024:.2f}GiB，GPU分配峰值{max(r['gpu_peak_allocated_mib'] for r in rows):.1f}MiB（不含全部CUDA上下文/桌面显示）。训练中总计{sum(r['training_truncations'] for r in rows)}次回合限制截断，正确bootstrap最终状态并切断GAE；不是全部episode都到真实胜负。

CPU/GPU完整配置网格见research/training-device-grid-fixed.json：4/8/12/16/20环境 × CPU/CPU、CPU/GPU、GPU/GPU ×2重复，每点6次PPO更新，去掉首个更新后统计稳态。所有worker同一20对10弓箭手场景/攻击侧/初始BC-MLP、相同规则与种子前缀；rollout32/batch64/epoch3，精确合法动作、真实模型推理、采样及更新全部包含。不同设备的随机采样序列可能不同，所以固定的是场景与预算，而不是跨设备逐帧完全相同。两次范围和完整含初始化指标均保留，不挑最好一次。最早的training-device-grid.json混合场景分布随并行数改变，仅作为探索性数据；不能直接据此认定跨并行数优劣。

| 固定场景12环境 | 稳态steps/s中位数 | 两次范围 | PSS采样峰值GiB |
|---|---:|---:|---:|
''' + '\n'.join(f"| {s['inference']}推理/{s['training']}更新 | {s['median_steps_per_second']:.1f} | {s['min_steps_per_second']:.1f}–{s['max_steps_per_second']:.1f} | {s['peak_pss_mib']/1024:.2f} |" for s in fixed_grid['summary'] if s['workers'] == 12) + '''

固定简单MLP场景的CPU推理/GPU更新略快；多兵种GNN/Attention的网络计算更重，本轮采用GPU推理和更新。Windows同版本/同真实输入网络微基准为model-device-benchmark-windows.json：小MLP批1/12的CPU推理更快，训练batch64的GPU明显更快。微基准包含数据传输、5次预热/20测量；不能把它代替WSL完整训练速度。

可变候选batching已比较：padding-benchmark.json，对同1024个真实验证状态，随机padding与按候选数量分组，32/64/128/256batch、3重复，含排序、装配、传输和GPU推理。分组减少padding，但这里只测离线推理；不能宣称PPO学习质量或更新速度必然改善。首重复有冷启动，查看中位数和后续重复。

优化：模拟worker不再导入Torch/CUDA（12个worker均验证false）；抽出NumPy-only battle_features.py。缓存next Value避免重复前向，两个独立实际运行的action及GAE return hash完全一致。原v15接收max_steps但不执行该上限；已在vector_env增加显式step cap，并用真实一回合测试验证final observation与reset observation分开。实际Gym回合上限为30，wrapper默认step cap400，通常先到回合上限。

Masked PPO配置：gamma.99、GAE lambda.95、clip.2、entropy.01、value系数.5、梯度裁剪.5、KL阈值.03、Adam1e-4。纯胜负普通步0/正常终局±1；塑形仅终局小权重.05×(敌我真实伤亡数量比例差)，仅限无复活/召唤课程，不当作兵种价值或跨地图最优奖励。

GPU测温/占用每16更新采样，全部在保护限内。WSL可用内存2GiB/Swap256MiB保护，出现异常/超时/过多截断会停止。core-type-telemetry.json读取Windows CPU-set：16逻辑线程较高效率等级、12较低等级，与8P+12E结构吻合；采样平均利用率约34.6%/16.9%，包括主机后台负载，不是训练进程专用数据。微软说明较高EfficiencyClass通常更快但功耗效率较低：[接口定义](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-system_cpu_set_information)。WSL虚拟编号没有可验证的主机核映射，没有伪造P/E绑核结论；CPU实时温度/频率仍无可靠传感器。

每次更新保存latest/优化器/进度，周期策略快照保留。新checkpoint还保存CPU和CUDA RNG；早期checkpoint只存CPU RNG，恢复不等于原战斗逐帧继续。所有环境会以记录seed重新创建。resume-gpu-probe.json已验证恢复128更新的选定模型并继续GPU更新、正常退出。RUN_TRAINING.ps1默认GPU、12环境、正确v2课程，先续训再做验证集战斗检查；后台没有无上限训练器。
''')

model_table = ['| BC模型 | 参数量 | 测试Teacher Top-1 | 独立战斗胜率 |', '|---|---:|---:|---:|']
for r in bc['results']:
    battle = json.loads((research / f"balanced-bc-{r['architecture']}-test.json").read_text())['summary'][0]
    model_table.append(f"| {r['architecture']} | {r['parameter_count']:,} | {r['test']['top1']:.1%} | {battle['win_rate']:.1%} |")
for r in ablation['results']:
    battle = json.loads((research / f"balanced-bc-{r['architecture']}-test.json").read_text())['summary'][0]
    model_table.append(f"| {r['architecture']} | {r['parameter_count']:,} | {r['test']['top1']:.1%} | {battle['win_rate']:.1%} |")
publish('DECISION_MODEL_BASELINE.md', '# Decision Model与真实战斗结果\n\n2026-10-14。共享实体编码＋动态候选评分＋可训练Value头；已完成真实BattleAI数据→BC→checkpoint重载→实际VCMI执行→Masked PPO→独立评测。\n\n' + '\n'.join(model_table) + f'''

BC用同一课程/种子20261014，width128（小模型消融64）、12epoch/batch64/Adam3e-4/梯度裁剪1.0；以验证CE挑checkpoint。MLP池化、两层Attention、两层普通GNN实测；无需LLM/JSON token输出。无Value头变体真实去掉该头，比较的是BC，不把无critic训练冒充Actor-Critic PPO。

所有网络共享v15编码，输出只对引擎合法候选归一化，padding概率0；空集合在非终局被拒绝。Action ID只在当前状态内有效。实体输入和候选关系复用引擎规则，不重新写伤害算法。模型输入缺口详见STATE_INTERFACE_AUDIT.md：当前没有逐堆原始HP/数量/攻防速、稳定兵种ID和英雄施法状态；GNN丢弃部分边类型/属性；不能说完整英雄/战术状态已经实现。

同一held-out160场测试：原BattleAI对自身50%，启发式10.625%、随机合法1.25%。纯BC-GNN30%；三个独立PPO种子分别47.5%、53.125%、65%，均提高对应BC，平均55.2083%。同时重采训练种子与场景的bootstrap均值95%区间约42.3–71.3%，比BC改善的区间约+7.7–46.9个百分点，不能将最高65%当作稳定总体胜率。BC+PPO-MLP52.5%、Attention35%，后者本次单seed没有收益，不默认更大网络更强。

当前按验证集胜率、再按同场景真实损失数量打破平分选中 `{selection['name']}`（GNN21万参数）；不是按test挑65%模型。该候选held-out160场胜率{selection['summary']['win_rate']:.1%}，Wilson95%47.3–62.5%，非法动作0、截断0。vs StupidAI80场75%；vs随机合法80场72胜/8回合限制截断，总体90%，没有把72/72当100%。这个失败说明跨对手稳定性还不充分，不宣称全面超过BattleAI。

失败复现：随机对手的8截断集中在balanced-29/35（枯木卫士/弓箭手/狮鹫）；都射击12次，之后大量等待/移动。random-failure-diagnostic-29.json确认末局无弹药、双方仅剩地面单位、非终局而到30回合限制。不能证明无限死循环，但足以定位弹药耗尽后的进攻/追击课程不足。混合对手训练对随机对手95%、4截断，却把BattleAI测试降到39.375%；对手比例/难度要重新设计。

主要指标均为实际战斗胜数/总局数，不是Policy softmax或Value输出。Value预测折扣奖励，不能直接称胜率。每模型test为10场景×双侧×8引擎seed，battle均新进程；validation是另外6场景×双侧×4seed。测试场景军队数量/部署未用于训练，但同一固定平原和熟悉兵种，不能推广到攻城/魔法/全图。置信区间与逐场配对结果在research/GOAL_RESULTS.json。

GPU已接入真实训练和推理；当前执行路径仍是Python/PyTorch→v15合法动作→VCMI，未导出ONNX/C++产品部署。可读模型备份在models/selected-v3，训练器原模型在WSL。源代码为battle_features.py、decision_model.py、train-bc.py、masked_ppo.py、vector_env.py、train-ppo.py和评测脚本。
''')

publish('TEACHER_DATA_REPORT.md', f'''# 教师数据与质量验收

2026-10-14。当前主数据 `{quality['dataset']}`，约522MiB，只保留在WSL。36个同兵种、接近兵力且反向部署的军队场景，20训练/6验证/10测试；每场景双侧12场，共864场、20,415决策。仅普通兵堆、无主动施法/随机障碍/攻城/战争机器，包含飞行/双格/部分兵种被动效果，不代表全兵种。

训练480场11,124帧（9,496独立状态）、验证144场3,442帧（3,005）、测试240场5,849帧（5,165）；跨集合精确编码hash交集0。BC明确去重，原始数据保留。WAIT5858、MOVE2639、AMOVE7910、SHOOT4008、DEFEND0。不能把“不防御”当成模型已懂防御：已完成3场强制合法DEFEND后由教师正常打完的协议测试，PPO也实际探索DEFEND，但缺教师监督。

每步NPZ保存全部Observation节点/关系/索引、合法ID及全候选mask，JSON保存真实教师chosen action、语义描述、battle/scenario/seed/episode/side、地图hash、版本和服务器终局。标签来自BattleEvaluator.selectStackAction、原强度计算和原难度搜索步数；没有拿诊断策略作教师。初期hex/unit近战编码错位已用规则解析修复，失败数据保留teacher-v1，不静默删除。

有效采集映射失败0、非法标签0、非有限值0，战斗全部真实正常结束。重复编码发现{audit['conflicting_teacher_action_states']}个动作冲突组，共{audit['decisions_in_conflicting_groups']}帧（约0.03%）：分别不同移动落点、不同近战落点/目标，全部合法；具体根因尚未确定，可能是编码遗漏或启发式排序，不能断言等价。187组相同观测有不同未来胜负，符合随机未来的可能，也反映编码需要加强。当前去重历史实现取首个标签/结果，已明确记录，后续应保留多标签/估计平均Value；原数据没有删掉。

Action ID仅对应本状态，BC按候选位置建label。Teacher metadata、真实战前兵力和未来终局不能进入Policy输入；仅当前可见v15节点/边进入features。复活/召唤/镜像和完整冒险地图永久保存仍未验收，伤亡数量奖励只用于本无复活课程。

随机对手原回调每次调用random_device，不可复现；已修复实际connector为持久seeded mt19937，使用engine seed+100000。两独立进程轨迹/终局一致。首轮不可复现混合实验排除并保留，已从BC按同预算重新训练，不混入有效结果。

完整质量证据：datasets目录manifest.json、research/teacher-label-audit.json、scenarios-v2.json、random-opponent-replay.json、defend-protocol-probe.json。采集与审计脚本支持12worker、新目录及scenario manifest，不覆盖原训练数据。复杂数据扩展前优先追加逐堆HP/数量/攻防速和显式行动状态。
''')

old_parallel = [read('parallel-benchmark-v2.json'), read('parallel-benchmark-high.json')]
parallel_rows = ['| 环境 | decisions/s中位数 | 三次范围 | PSS峰值GiB |', '|---:|---:|---:|---:|']
for data in old_parallel:
    for s in data['summary']:
        parallel_rows.append(f"| {s['workers']} | {s['median_steps_per_second']:.1f} | {s['min_steps_per_second']:.1f}–{s['max_steps_per_second']:.1f} | {s['max_sampled_pss_mib']/1024:.2f} |")
publish('PARALLEL_BENCHMARK.md', '# 并行模拟与完整训练对照\n\n2026-10-14。保留上轮原始证据，生产配置按用户指定12；不把纯模拟最优直接套到PPO。\n\n' + '\n'.join(parallel_rows) + '''

同20对10弓箭手，无主动魔法/渲染，诊断合法攻击策略vsBattleAI；每点3次10秒，一场预热后同步开始，完整打完最后一场。336个worker退出0。PSS按共享页比例采样，每250ms；不等于系统总内存。4/8原基线500.2/811.4与复测488.2/813.3接近，桌面/频率波动未隔离。12纯环境约1011次/秒、3.50GiB；28为本测试范围最高纯模拟1394次/秒，CPU约96%逻辑容量，增量收益已小，没有继续无约束扩容。28/24仅采样峰值和短程稳定，不能宣称所有复杂场景的最优数。

已补全带模型/采样/PPO的4/8/12/16/20三设备模式、两次重复网格，同固定场景。范围内最佳并发/设备从training-device-grid-fixed.json读取；不等于跨全部课程全局最优。相同并发下GPU更新提升，游戏规则仍在CPU。用户选择12的生产配置保持不变。更复杂三兵堆GNN课程的速度不可直接比简单弓箭手，正式样本效率需看独立胜率而非steps/s。

绑核：默认调度。Windows CPU-set及P/E负载采样见core-type-telemetry.json；Linux看见14个虚拟核心/28线程，没有证据把guest CPU编号映射到主机8P+12E，因此未编造P/E绑核提升。CPU实时温度/频率未测；GPU遥测、可用内存和Swap保护已记录。无OOM或持续崩溃；截断另列，不当作崩溃。

原始证据parallel-benchmark-v2/high.json、environment-benchmark.json（旧1/2/4/8）、training-device-grid-fixed.json。早期模型网格混合场景随n变化，为探索性，最新版修复该工作量混杂。新worker为NumPy-only，降低CUDA/Torch复制内存。均明确稳态/含初始化口径，保留范围，未挑单次峰值。
''')

publish('UPDATED_ROADMAP.md', f'''# 本轮完成状态与下一阶段

2026-10-14。本轮goal完成的是主指令Task1–7的初期研发/训练/对照与验收报告，不是完整1VS7项目。

| 阶段 | 当前状态 |
|---|---|
| 工程环境、真实动作/终局/数据闭环 | 已完成固定v15/匹配fork，独立进程、mask/重播/退出、权威战损普通场景 |
| 并行与GPU/完整吞吐 | 纯环境4–28，完整4–20×三设备，padding对照、GPU正式训练已完成；正式12 |
| 模型BC/Masked PPO | 5个BC配置，10个等预算正式PPO配置共983040步，多seed、奖励/对手/rollout/batch/epoch/架构对照已完成 |
| 普通多兵种战斗 | 已具备真实合法操作与有限泛化收益；随机对手仍8/80回合限制失败，不能称全面验收通过 |
| 复杂战术/攻城/主动魔法 | 未实现完整课程和施法接口；部分v15技能flags可见不等于会用经典战术 |
| 地图战略/经济/英雄接力/飞跳回 | 未实现训练控制接口 |
| 完整1v1/1v3/1v7、人类挑战 | 未达到条件，不能由本battle胜率推算 |

关键实验结论：PPO相对BC提升在3个GNN种子都出现；平均55.2%而非只报65%。当前验证规则选中{selection['name']}，测试55%，并非按最高test选。Attention本次PPO无提升；较小MLP仍有竞争力，不默认扩大网络。搜索4回合测试45.625%vs原50%，暂无更深更好的证据。mixed对手改善随机完成率却牺牲BattleAI测试，不能按训练胜率选对手池。larger batch/少epoch更快但未稳定提高最终胜率，拒绝把高吞吐当高学习效率。

下一项最有信息价值的研发：精确记录逐堆数量/HP/攻防速、保持候选actor/target/landing实体embedding关联和重要边属性，再建立弹药耗尽后的推进/追击、等待/阻挡/双格专项。8个随机失败全在两个同类军队场景，有可重播轨迹；先排查观测/目标选择与回合预算，再做针对课程，不虚构更长战斗的胜利。

随后扩充障碍/攻城、多兵种与防御监督，增加更多独立布局和训练seed，按兵种真实价值/永久结算评估战损；复活/召唤专项验证后才加对应奖励。历史模型池/selfplay、主动法术合法目标和多阶段执行、宏观地图/迷雾接口仍是后续工程，不能只靠继续跑现有12环境训练完成。

交付五份主报告及GOAL_PROGRESS_AND_RESULTS.md、STATE_INTERFACE_AUDIT.md；研究代码/原始结果在research，模型/data在忽略目录，匹配runtime-manifest-v3与lab-v3-native.patch。Windows原游戏/官方VCMI源码没有修改。RUN_TRAINING.ps1可从已验证策略继续GPU训练，阶段和恢复范围明确。当前没有后台无限训练。
''')

publish('GOAL_PROGRESS_AND_RESULTS.md', f'''# 初期研发与训练goal结果

2026-10-14。这次完成了实际工程、训练和对照，不再只是一轮几分钟的最小smoke；仍只控制战斗，尚未具备完整地图玩家AI。

**GPU已使用。** 上一轮WSL只有CPU Torch，先验证闭环但尚未完成GPU对照。本轮新增匹配GPU环境，完成CPU/GPU微基准与完整PPO网格；10组正式实验使用12环境/GPU推理与更新。游戏规则模拟在CPU，小模型不需要填满16GB显存。固定小场景12环境CPU/GPU更新比全CPU更快；复杂课程每秒约几百个真实决策，不能与无模型简单场景1011混为一谈。

**50%到底是什么？** 是真实打完的胜数/全部测试局数，不是模型选择动作的概率。旧两场景兵力差异太大，很多策略都自然赢一边输一边，评价不敏感；已替换36近均衡军队场景。正式测试10个未训练场景×攻守×8个构造seed=每模型160局。BattleAI对自身50%是锚点，启发式10.625%、随机合法1.25%，说明新测试能区分强弱。

**学习结果：** 对应GNN-BC30%；PPO三个种子47.5/53.125/65%，均改善，平均55.2083%，跨种子/场景95%区间约42.3–71.3%。不能只挑65%宣称稳定超过BattleAI。按验证集胜率、损失数量选择的当前模型测试{selection['summary']['win_rate']:.1%}；未用test挑选。其他架构/参数实验逐项见TRAINING_THROUGHPUT，不掩盖35%/37.5%等负结果。

**本轮实际完成：** 匹配C++接口与教师映射，864场20415帧教师/去重/质量审计；MLP/Attention/GNN、width64及无Value头BC；10组等采样预算PPO983040步；3训练种子；奖励/对手/rollout/batch/epoch/架构消融；纯模拟4–28与完整4–20×三设备×重复；候选padding对照；真实MASK/GAE/截断/缓存/重播/退出与GPU恢复测试。所有有效正式trainer正常退出，测试无非法动作。

**仍存在真实失败：** 当前模型vs随机合法72胜/80，8局到30回合预算；vsStupidAI60胜/80。前者不是72/72=100%，没有隐藏截断。复现看到耗尽弹药后大量等待/移动，说明跨对手与残局追击尚不足。混合对手训练随机胜率95%/4截断，但BattleAI测试39.375%，显示不能靠增加弱对手就假定更强。教师DEFEND标签0、同码动作冲突2组6帧和缺逐堆HP等原始输入也明确保留。

**整个项目进度：** 环境/数据/普通战斗训练已经能跑；复杂战术、攻城、主动失明/复活/镜像、地图战略/经济/技能/飞跳回、完整1v7都还没完成。它们需要扩接口和课程，不是把本轮模型多训练几次就能获得。下一步应针对可复现失败补原始单位状态和候选关联、弹药/追击/等待课程，再拓展魔法和战略。

模型参数/代码/实测/不确定性/失败/下一阶段分别在五份主报告；全部原始比较见research/GOAL_RESULTS.json及ppo-research-suite.json。动态图/小网络只做结构化合法动作打分，没有LLM或商业API调用，没有改写资源/移动力/地图信息作弊。

![真实战斗对照](research/goal-battle-results.png)
''')

model_dir = root / 'models/selected-v3'
model_dir.mkdir(parents=True, exist_ok=True)
destination = model_dir / 'policy.pt'
shutil.copy2(selection['checkpoint'], destination)
assert hashlib.sha256(destination.read_bytes()).hexdigest() == hashlib.sha256(Path(selection['checkpoint']).read_bytes()).hexdigest()
(model_dir / 'manifest.json').write_text(json.dumps(dict(source=selection,
    copied_checkpoint_sha256=hashlib.sha256(destination.read_bytes()).hexdigest(),
    feature_version='lab-candidates-v1/vcmi-v15', scope='Ordinary battle validation candidate; random-opponent failures remain'), indent=2))
(research / 'formal-training-summary.json').write_text(json.dumps(rows, indent=2))
print('Published five reports, progress summary, and verified model copy')
