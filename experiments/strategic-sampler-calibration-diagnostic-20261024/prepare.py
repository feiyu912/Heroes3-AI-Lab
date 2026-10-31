"""Pre-register a TRAIN-only mode diagnostic; no new PPO or source mutation."""
from pathlib import Path
import json,shutil
HERE=Path(__file__).resolve().parent;PARENT=HERE.parent/'strategic-active-opponent-learning-20261024'
def once(s,a,b):assert s.count(a)==1,(a[:60],s.count(a));return s.replace(a,b,1)
def main():
    assert not (HERE/'collect_cpu.py').exists()
    shutil.copy2(PARENT/'leases.py',HERE/'leases.py')
    shutil.copy2(PARENT/'audit_game_v6.py',HERE/'audit_game_v6.py')
    (HERE/'pipeline_common.py').write_text('''"""Only TRAIN diagnostic, bound to the immutable completed learning epoch."""
import importlib.util,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;PARENT=HERE.parent/'strategic-active-opponent-learning-20261024'
spec=importlib.util.spec_from_file_location('_frozen_learning_support',PARENT/'pipeline_common.py')
parent=importlib.util.module_from_spec(spec);spec.loader.exec_module(parent)
for key in ('BASE','LAB','NATIVE','MARKER','DEFAULT_CAPSULE','DEFAULT_INITIAL','INITIAL_SHA','CONTROL_POLICY','CONTROL_SHA','require_qualification','sha','capsule_inputs','validate_capsule','clean_environment','training_variant'):
    globals()[key]=getattr(parent,key)
AUDITOR=HERE;EPOCH='strategic-sampler-calibration-TRAIN-diagnostic-v1'
def audit_metadata():return dict(parent.audit_metadata(),pipeline_epoch=EPOCH,TRAIN_only=True,sampler_diagnostic_only=True)
def source_inputs():
    freeze=PARENT/'SOURCE_FREEZE.json'
    if sha(freeze)!='c19ac372d22b3156172f02a65f8ad1ef4dc635a15737775eb8cf98c3b31467f7':raise ValueError('Frozen paired study changed')
    if not all(sha(path)==h for path,h in json.loads(freeze.read_text())['files'].items()):raise ValueError('Frozen paired source changed')
    return sorted(set(parent.source_inputs()+[freeze,HERE/'PLAN.md',HERE/'COLLECTOR_DERIVATION.json']+list(HERE.glob('*.py'))),key=str)
def validate_native_epoch(native,plan,execution):
    for obj in (native,plan,execution):
        if not all(obj.get(k)==v for k,v in audit_metadata().items()):raise ValueError('Diagnostic-only epoch required')
    if not native['whole_game_valid'] or not native['native_game_completed'] or not native['transport_drained']:raise ValueError('Invalid diagnostic game')
def validate_cells(*args):raise ValueError('Diagnostic observations cannot become new PPO admissions')
''')
    s=(PARENT/'collect_cpu.py').read_text()
    s=once(s,'from pipeline_common import source_inputs','from pipeline_common import training_variant,INITIAL_SHA,source_inputs')
    s=once(s,'assert args.map in ("takeover-v2-dev-01-river","takeover-v2-dev-02-reserves"),"Only the two registered DEV maps"','assert args.map in ("takeover-v2-train-01-mines","takeover-v2-train-02-development"),"TRAIN-only diagnostic"')
    s=once(s,'checkpoint=checkpoint.resolve();assert checkpoint.is_file()',"checkpoint=checkpoint.resolve();assert checkpoint.is_file() and sha(checkpoint)==INITIAL_SHA")
    s=once(s,"source=LAB/('data/vcmi/Maps/adv/'+args.map+'.vmap')", "variant=training_variant(args.map,args.player,args.opponent,'curriculum')\n    assert args.opponent=='Nullkiller2' and variant['multiplier']==4\n    source=Path(variant['path'])")
    s=once(s,"shutil.copy2(source,work/'data/vcmi/Maps/adv'/source.name)","shutil.copy2(source,work/'data/vcmi/Maps/adv'/(args.map+'.vmap'))")
    s=once(s,"LOCAL/'collect_episode_v5.py'","LOCAL/'COLLECTOR_DERIVATION.json'")
    s=once(s,'dict(policy_epoch=policy_epoch,broker_path=',"dict(map_variant=variant,multiplier=4,policy_epoch=policy_epoch,broker_path=")
    s=once(s,"choices=['takeover-v2-dev-01-river','takeover-v2-dev-02-reserves'],default='takeover-v2-dev-01-river'", "choices=['takeover-v2-train-01-mines','takeover-v2-train-02-development'],default='takeover-v2-train-01-mines'")
    (HERE/'collect_cpu.py').write_text(s)
    (HERE/'COLLECTOR_DERIVATION.json').write_text(json.dumps(dict(parent=str(PARENT/'collect_cpu.py'),changes=['only canonical original TRAIN names admitted','fixed initial1510149e only; NK and curriculum x4 only','same private canonical map basename/bytes as archived stochastic cells','zero optimization/admission; independent diagnostic metadata'],native_runtime_unchanged=True),indent=2))
    (HERE/'PLAN.md').write_text('''# TRAIN采样方式配对诊断（零新增优化）

触发：已完成课程TRAIN的四个主动对手格全败，旧CPU argmax校准×4为2/4胜。旧校准种子4300..4303与训练4402/4403/4406/4407不同，不能据此归因采样。该诊断在当前24DEV完成前登记，选择不依赖DEV结果；必须等现有研究结束且学习器退出后才运行。

只补4次CPU argmax原生对局：同一1510149e初始化、同×4地图字节、私有规范地图名、相同角色/Nullkiller2/种子2026104402、4403、4406、4407，对照已经保存的4次真实CUDA multinomial TRAIN轨迹。不重跑随机臂、不重播种、不追加格、不改兵量，不新增任何PPO准入/专家标签/优化。已有随机轨迹此前确已用于当前研究，本诊断只读复用，绝不冒充新的训练数据。

全部正常完整终局、原生资源/库存/军队/ACK审计、首军队绑定、逐决策CPU proposal复算；比较初始公开请求、直到首次不同的完整公开请求和动作。相同seed不能保证隐藏状态/随机对手序列，首次不同若先为观察差异则注明无法严格隔离；CPU/CUDA数值/推断设备与决策规则共同变化，不能据一次结果宣称唯一采样因果。GPU采样的值/logp已有原研究完整CUDA重放证据；后续可在相同公开请求上比较CPU数值，不能把公开前缀等同完整引擎前缀。

无论4局是否显示差异均保留并报告；若没有差异，不追加seed追求预期。结果只用于判断旧校准能否代表实际训练分布，不能证明招募动作正确、需要更多兵量、一般强度或适合直接教师学习。完整目标及原评估不改，finaltest始终封存。

继承GPU锁→pool锁、非阻塞、原生继承锁后独立会话清理；阶段前后可用内存>2GiB、swap<256MiB。所有父epoch字节不变。
''')
    print(json.dumps(dict(prepared=True,new_native_games=0,new_optimizer_steps=0)))
if __name__=='__main__':main()
