"""Build experiment reports from recorded measurements, preserving old reports."""
from pathlib import Path
import json
import statistics

root = Path('/mnt/g/Heroes3-AI-Lab')
research = root / 'research'


def read(name):
    return json.loads((research / name).read_text(encoding='utf-8-sig'))


def write(name, content):
    (root / name).write_text(content, encoding='utf-8')


parallel = [read('parallel-benchmark-v2.json'), read('parallel-benchmark-high.json')]
summaries = [s for group in parallel for s in group['summary']]
baseline = summaries[0]['median_steps_per_second']
rows = ['| 环境数 | 总 decisions/s 中位数 | 三次范围 | 单环境 decisions/s | 相对4环境扩展效率 | PSS峰值 GiB | 逻辑核心当量 |',
        '|---:|---:|---:|---:|---:|---:|---:|']
for s in summaries:
    n, speed = s['workers'], s['median_steps_per_second']
    rows.append(f"| {n} | {speed:.1f} | {s['min_steps_per_second']:.1f}–{s['max_steps_per_second']:.1f} | {speed/n:.1f} | {100*speed/baseline/(n/4):.1f}% | {s['max_sampled_pss_mib']/1024:.2f} | {s['median_cpu_core_equivalents']:.2f} |")
write('PARALLEL_BENCHMARK.md', '# 并行环境扩展实测\n\n日期：2026-10-14。所有数字来自实际运行，保留上一轮 `research/environment-benchmark.json`。\n\n' + '\n'.join(rows) + '''

固定负载是20对10弓箭手，无魔法、障碍、攻城、神经网络。每组3次10秒，同种子20261013，先完成一场预热，再统一开始；最后一场打完后结束。decisions/s统计Python合法动作step，不统计BattleAI内部决策。计时含reset和诊断策略，不含启动和关闭。PSS每250ms采样，不等于整个Windows/WSL内存。336个worker全部正常退出。

与上一轮相比，8环境813.3与811.4接近，4环境488.2比500.2低约2.4%；桌面负载、时钟和运行波动未隔离，不能解释为代码退化。20环境比8环境吞吐高59.3%，24/28继续增加的收益已小，28环境约占可见逻辑CPU容量96%。不继续测试更高数量。28是本次测试中的最高纯模拟吞吐，不是经完整训练证明的最优并行数。

**用户指定后续采用12环境。** 不再把4/8作为人为限制。12环境纯模拟约1011 decisions/s、PSS约3.50GiB；模型接入的真实数据见TRAINING_THROUGHPUT.md，不能用纯环境数字推算PPO速度。

CPU调度为默认，无绑核。BLAS/OMP线程1；未改引擎TBB线程策略。WSL暴露14个虚拟核心、每核2线程，不能直接映射主机8P+12E；当前没有可靠核型映射、温度或频率传感器，未声称已完成P/E affinity比较或锁竞争定位。24/28组WSL最低可用内存约6.74GiB，Swap始终0。4–20组未保存完整系统内存时间序列，单步分位数仅24/28组保存于worker_records。Windows主机内存仅零散查询，不能当成完整峰值测量。

原始结果：research/parallel-benchmark-v2.json、research/parallel-benchmark-high.json。24/28组新增延迟采样与内存保护，监测开销略有差异；微小吞吐差距需更长随机顺序实验才能确定。

复跑：`wsl -d Ubuntu-22.04 -- python3 /mnt/g/Heroes3-AI-Lab/research/benchmark-environments.py`。可使用--workers、--repeats、--seconds、--output控制实验。WSL可用内存低于2GiB或Swap使用超过256MiB时失败并清理整个worker进程组。
''')

quality = read('teacher-quality-v1.json')
write('TEACHER_DATA_REPORT.md', f'''# 真实BattleAI教师数据

日期：2026-10-14。12个环境并行采集，数据在 `{quality['dataset']}`，体积约81MiB，不放入Git。

- 12个多兵种、无魔法场景，攻守两侧，每组20场：{quality['episodes']}场、{quality['steps']}决策。
- 按Scenario ID分为8个训练场景、2个验证场景、2个测试场景；同场战斗和同场景两侧不跨集合。
- 训练2007帧/320场、验证501帧/80场、测试711帧/80场。
- 精确独立状态数分别728、229、243。跨集合完整节点/边状态hash交集均0；集合内有大量重复，不能把3219帧当成3219个独立局面。
- WAIT1140、MOVE796、AMOVE859、SHOOT424、DEFEND0。防御监督缺失，是当前数据局限；PPO可合法探索防御，不代表已学会合理防御。
- 完成数据中映射失败0、非法标签0、非正常终局0、截断0。每个数组检查有限值，mask/候选/标签匹配。

教师实际调用训练fork的BattleEvaluator.selectStackAction，复用BattleAI原有getStrengthRatio和按难度选搜索步数的函数。没有用诊断策略生成教师标签。当前教师是无主动魔法/撤退/战争机器条件下的BattleAI兵堆行动选择，不冒充全功能教师。

首次采集失败保留在 `/root/heroes3-ai-lab/datasets/teacher-v1`。原因是近战目标分别以hex和unit编码。修复通过BattleAction.getTarget和battleGetUnitByPos解析，比较起步格、目标兵堆和返回位置，不猜伤害规则。当前课程不含龙喷吐/尸巫范围攻击；不能把“同一目标兵堆”扩大解释为所有特殊攻击的等价行动。修复后的数据另存teacher-v2，未覆盖失败证据。

每场保存NPZ完整Observation（节点、关系和索引）、合法ID、全候选mask，JSON保存Chosen Action、可读引擎动作、Battle ID、Scenario ID、引擎构造seed、episode序号、双方、地图hash、teacher版本、终局结果和schema。Action ID只在对应状态内有效，不当作跨状态固定标签。训练按候选位置取label。真实战前军队/终局结果和教师标签仅作为元数据或监督目标，绝不作为模型输入。

同一进程reset继续引擎随机序列；构造seed和episode序号共同定义轨迹。独立模型对战测试为每场新进程、同构造seed配对，避免宣称reset(seed)已重置引擎。

证据：research/teacher-quality-v1.json、scenarios-v1.json。完整源补丁为research/lab-v2-native.patch（含此前终局与目录隔离改动），搭配原兼容补丁并重新构建engine/connector。旧runtime-manifest.json保持历史证据，新版本使用runtime-manifest-v2.json。

复跑：先make-training-maps.py；然后teacher-pipeline.py --workers 12 --episodes 20 --dataset <新的目录>，脚本拒绝覆盖已有数据。后续优先补防御/障碍课程、更多场景、训练集去重和多个引擎seed；不把重复极小场景当作成熟教师数据。
''')

bc = read('bc-baseline-v1.json')
rows = ['| 模型 | 参数量 | 初始验证Top-1 | BC验证Top-1 | 测试Top-1 | 测试Top-3 | 测试masked CE | 最佳epoch | 训练秒 |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
for r in bc['results']:
    rows.append(f"| {r['architecture']} | {r['parameter_count']:,} | {r['initial_validation']['top1']:.1%} | {r['validation']['top1']:.1%} | {r['test']['top1']:.1%} | {r['test']['top3']:.1%} | {r['test']['masked_cross_entropy']:.3f} | {r['best_epoch']} | {r['training_seconds']:.1f} |")
write('DECISION_MODEL_BASELINE.md', '# Decision Model最小闭环\n\n日期：2026-10-14。已完成真实教师采集→BC→验证选checkpoint→重新加载→真实战斗执行。\n\n' + '\n'.join(rows) + '''

三模型使用同一数据、seed20261014、width128、16epochs、batch32、Adam3e-4、梯度裁剪1.0；按验证masked CE选择checkpoint。单次训练seed和很小的场景集不足以给架构排名置信区间。Value以同场教师轨迹的终局+1/-1监督，权重0.1；不是动作胜率。

公共输入为v15 Global/Player/Unit/Hex实体，各类型padding到35维并加类型编码。候选特征包含原始动作编码、执行单位、落点、目标、阻挡单位及引擎关系伤害属性。状态只编码一次。MLP池化、两层attention和两层普通图消息传递对照；无需torch-geometric。实体pooling与候选共享评分，Policy给合法候选logits，Value评估局面。Mask仅由引擎合法候选生成，padding概率为0。没有用非法动作惩罚代替规则mask。

本轮PPO先接小型MLP，便于控制CPU推理成本；GNN验证CE略好、MLP教师Top-1较好，复杂网络尚无足够实际收益证据。三模型保存/重载得分完全一致；合批padding不改变单个局面输出、候选重排对应重排logits、只采合法动作的测试通过。

真实对战：两个完全未见训练场景、攻守两侧、每侧5个独立引擎seed。BattleAI教师、诊断启发式、BC-MLP和BC-attention各20场，全部正常结束且非法动作0。各自胜率均50%，Wilson95%约[29.9%,70.1%]。这组测试兵力差异较大，胜率敏感性不足，不能宣布模型等于或超过BattleAI。平均永久损失单位数：教师20.70、启发式24.05、BC-MLP24.70、BC-attention24.95；不同兵种不能仅用数量汇总比较价值。保留逐场结果供分析。

代码：research/decision_model.py、train-bc.py、evaluate-policy.py、evaluate-battles.py、test-training-contracts.py。checkpoint在 /root/heroes3-ai-lab/models/bc-v1/{mlp,attention,gnn}.pt；参数、数据manifest hash和训练信息嵌入checkpoint，文件hash在research/bc-baseline-v1.json。当前部署是Python/PyTorch通过合法VCMI动作接口，尚未导出ONNX或原生C++推理。

缺口：DEFEND教师监督、障碍/攻城/主动魔法、复杂永久战损、丰富的均衡测试场景；当前编码复用v15，尚未补全兵种ID和特殊技能原始属性。改进搜索教师尚未实测。先扩数据和公平评测，再根据证据升级网络。
''')

short = read('ppo-short-v1.json')
pilot = read('ppo-pilot-v1.json')
assert pilot['completed'], 'Do not report unfinished training as complete'
training_runs = [short, pilot]
rows = ['| 实验 | 并行环境 | 采样步数 | 更新次数 | 训练墙钟秒（不含启动/关闭） | 端到端steps/s | PSS采样峰值GiB |',
        '|---|---:|---:|---:|---:|---:|---:|']
for label, run in zip(['短程验证', '续训pilot'], training_runs):
    count = sum(r['steps'] for r in run['records'])
    rows.append(f"| {label} | {run['config']['workers']} | {count} | {len(run['records'])} | {run['wall_seconds']:.2f} | {count/run['wall_seconds']:.1f} | {run['sampled_peak_total_pss_mib']/1024:.2f} |")
write('TRAINING_THROUGHPUT.md', '# 12环境端到端训练实测\n\n日期：2026-10-14。用户指定12环境，本轮固定此配置，未重新进行4/8/16/20全训练配置搜索。\n\n' + '\n'.join(rows) + f'''

算法：BC初始化Masked PPO，Actor/Critic、GAE(gamma0.99,lambda0.95)、优势归一化、clip0.2、entropy0.01、value系数0.5、梯度裁剪0.5、KL阈值0.03，Adam1e-4。每次rollout32×12=384步、batch64、最多3epochs。采样与更新使用同一份保存的候选顺序/掩码；每次更新前重算log-prob并校验与采样值一致。

只用权威正常终局胜负+1/-1，普通步0；不使用旧Gym伤害奖励或未经验证的永久战损塑形。terminated不bootstrap；truncated bootstrap最终状态且切断GAE，不连接下一episode；相应测试通过。Value/梯度/概率检查有限值。

12个独立VCMI进程，各有独立资源/日志目录；中央训练器批量CPU推理和更新。仿真、特征抽取和IPC时间会重叠，记录的environment_ipc_seconds是父进程等待墙钟，不能拆成纯引擎开销。每步当前实现还单独推理next value，后续可缓存以省开销。所有worker带Torch模块依赖，增加内存；后续可把轻量特征抽取与Torch解耦。

纯环境约1011 decisions/s与这里约240–260 steps/s负载不同：训练是多兵种课程，另有特征/IPC、Policy推理、bootstrap及PPO更新。不能把差距全部归因于模型。GPU未参与，没有GPU推理/更新速度、显存或CPU-vs-GPU对照结论；小型网络先CPU闭环，后续按同负载比较。

短程474场战斗、续训{pilot['records'][-1]['episodes_total']}场，均未出现截断；12进程全部exit0。续训采样到最低WSL可用内存{pilot['records'][-1]['wsl_min_available_mib']/1024:.2f}GiB，Swap峰值{pilot['records'][-1]['wsl_max_swap_used_mib']:.0f}MiB。PSS含父训练器和12个worker，采样未覆盖所有瞬时峰值。Windows内存/CPU时间序列在research/windows-training-telemetry.json；CPU温度与P/E核型监控尚不可用，不能宣称通过温度压力验收。

已经完成8+64=72次优化更新、3072+24576=27648采样步。续训恢复optimizer与PyTorch RNG，但环境以保存seed重新启动；不宣称从中断战斗逐字节恢复。每次更新保存latest，续训每16次保存独立策略快照。pilot最终checkpoint：`{pilot['checkpoint']}`。训练胜率来自固定课程，不能当独立测试胜率。

证据：research/ppo-short-v1.json、ppo-pilot-v1.json、training-contract-tests.json；代码为vector_env.py、masked_ppo.py、train-ppo.py。资源保护：可用内存2GiB、Swap256MiB、持续异常/worker超时或明显增加的截断会失败并清理进程。不留后台无上限训练器。
''')

evaluation = read('battle-evaluation-ppo-pilot.json')
model_eval = next(r for r in evaluation['summary'] if r['policy'] == 'model')
write('UPDATED_ROADMAP.md', f'''# 根据实测更新的研发路线

日期：2026-10-14。已从预研进入可运行训练，默认12环境（用户指定）。

1. **已完成**：4/8/12/16/20及24/28扩展实测；真实BattleAI兵堆教师、合法映射、480场课程数据；MLP/Attention/GNN的BC训练与保存加载；真实VCMI动作执行；Masked PPO短程与有限续训，总27648步/72更新。
2. **独立评测**：BC-MLP/attention各20场，模型与教师胜率均50%。pilot PPO {model_eval['battles']}场，胜率{model_eval['win_rate']:.1%}、截断{model_eval['truncated']}、非法动作{model_eval['invalid_actions']}。样本小且兵力不均衡，不能证明RL已经提高胜率；不根据课程内胜率作提升结论。
3. **下一优先项**：新增至少一组更均衡且策略敏感的测试场景，覆盖DEFEND、阻挡、射手被贴身、双格/飞行与等待次序；增加独立seed、训练去重、逐动作族评测。比较多个训练seed，保留BC锚点与失败轨迹。先改善评测信息量，再决定更大训练预算。
4. **性能**：在用户指定12环境下比较单步/批量推理、缓存next value和更紧凑IPC；保留CPU基线，再实测GPU。暂不声称12是PPO全局最优，亦不因为28纯模拟较快就改变用户配置。
5. **算法**：目前MLP较小且可运行；Attention/GNN没有稳定收益证明。改进传统搜索、无Value头对照、BC+PPO多seed和奖励消融仍未完成。纯胜负奖励优先；复活/召唤结算验证前不加永久战损奖励。
6. **后续阶段**：主动魔法与合法多目标schema→复杂战术→战略接口→完整1v1/1v3/1v7。当前没有这些能力的完成证据，不修改游戏规则或绕过合法接口。

交付：PARALLEL_BENCHMARK.md、TEACHER_DATA_REPORT.md、DECISION_MODEL_BASELINE.md、TRAINING_THROUGHPUT.md及本文件。历史预研与上一轮实测不覆盖，新证据与复现补丁按版本并存。正式长训练应先扩大测试课程和稳定性范围，记录温度/主机压力、固定模型/内容版本和完整训练配置；当前仅完成有限pilot。
''')
print('Wrote five V2 reports')
