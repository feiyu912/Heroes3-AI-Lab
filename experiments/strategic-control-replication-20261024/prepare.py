"""Separate, fixed follow-up for the single positive active-opponent DEV cell."""
from pathlib import Path
import json,shutil
HERE=Path(__file__).resolve().parent;PARENT=HERE.parent/'strategic-active-opponent-learning-20261024'
def once(s,a,b):assert s.count(a)==1,(a,s.count(a));return s.replace(a,b,1)
def main():
    assert not (HERE/'collect_cpu.py').exists()
    for name in ('leases.py','audit_game_v6.py'):shutil.copy2(PARENT/name,HERE/name)
    s=(HERE.parent/'strategic-sampler-calibration-diagnostic-20261024/pipeline_common.py').read_text()
    s=s.replace('Only TRAIN diagnostic','Fixed active-opponent DEV follow-up').replace("EPOCH='strategic-sampler-calibration-TRAIN-diagnostic-v1'","EPOCH='strategic-control-replication-DEV-v1'")
    s=s.replace('TRAIN_only=True,sampler_diagnostic_only=True','DEV_only=True,replication_only=True')
    s=s.replace("[freeze,HERE/'PLAN.md',HERE/'COLLECTOR_DERIVATION.json']", "[freeze,HERE/'PLAN.md',HERE/'COLLECTOR_DERIVATION.json',CONTROL_CHECKPOINT]")
    s+='''
CONTROL_CHECKPOINT=LAB/'evaluations/strategic-active-learning-native-01/control/update-01/update-1.pt'
CONTROL_CHECKPOINT_SHA='b52ac74ad3b0ba6860e57be0a6b2deed9d8c88f14e140b59bd2c61e8b1f739fc'
'''
    (HERE/'pipeline_common.py').write_text(s)
    s=(PARENT/'collect_cpu.py').read_text()
    s=once(s,'from pipeline_common import source_inputs','from pipeline_common import INITIAL_SHA,CONTROL_CHECKPOINT_SHA,source_inputs')
    s=once(s,'checkpoint=checkpoint.resolve();assert checkpoint.is_file()',"checkpoint=checkpoint.resolve();assert checkpoint.is_file() and sha(checkpoint) in (INITIAL_SHA,CONTROL_CHECKPOINT_SHA)")
    s=once(s,"LOCAL/'collect_episode_v5.py'","LOCAL/'COLLECTOR_DERIVATION.json'")
    (HERE/'collect_cpu.py').write_text(s)
    (HERE/'COLLECTOR_DERIVATION.json').write_text(json.dumps(dict(parent=str(PARENT/'collect_cpu.py'),changes=['DEV-only replication metadata','fixed original initialization and original x1-trained control checkpoint only','complete frozen source closure includes new controller and current checkpoint'],native_changes=False,optimizer_steps=0),indent=2))
    (HERE/'PLAN.md').write_text('''# 原始兵量训练模型：主动对手开发复核

触发证据：前一预登记24DEV中的initial4/8、control5/8、curriculum4/8，40原始重审+16871完整CPU proposal重算通过。唯一正翻转是储备图红方seed2026104606；这不能认证稳定提升，也不能独归因招募。本项明确为见到该开发结果后的有限后续验证，不冒充事先登记的确认试验。

锁定同一原始初始化1510149e和原始兵量训练control b52ac74a，不再训练/改权重/挑模型；不含表现较差的课程臂。本问题仅检验此控制模型对主动对手的改善能否在新seed重复。
保留原始未加兵DEV河流/储备两图、双方、Nullkiller2，共4格，固定两组全新seed：2026108802/8803/8806/8807和2026108902/8903/8906/8907。两模型每格同native seed，合计16局。CPU argmax，完整终局/原生审计/每一次完整CPU proposal重算，记录初始公开请求是否相同。

全部格与负例保留；无重试、重播种、追加格、看分停止或提升模型，无任何PPO/专家数据准入、不触finaltest。既有DEV地图/对手已见过，只是seed新，仍为开发研究；共同seed/公开初始请求不保证完整隐藏状态相等。

原生复用不变schema6 capsule02，战斗仍委托BattleAI；两模型不同实际PPO策略处理，无法将收益独归因某招募动作。16局样本不认证总体稳定胜率或全游戏能力。严格GPU锁→pool锁、非阻塞、单原生会话进程继承锁并退出后释放；阶段前后内存>2GiB/swap<256MiB。原模型、epoch和finaltest封存。
''')
    print(json.dumps(dict(prepared=True,native_games=0,optimizer_steps=0)))
if __name__=='__main__':main()
