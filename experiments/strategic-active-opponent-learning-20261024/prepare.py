"""Derive a separate paired-learning epoch; never edit the protected parents."""
from pathlib import Path
import hashlib,json,shutil
HERE=Path(__file__).resolve().parent;EXP=HERE.parent
OLD=EXP/'strategic-learned-recruitment-run-v2'
POLICY=EXP/'strategic-active-opponent-policy-v4'
EPOCH='strategic-active-opponent-paired-learning-v1'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def once(s,a,b):
    assert s.count(a)==1,(a[:80],s.count(a));return s.replace(a,b,1)
def main():
    assert not (HERE/'pipeline_common.py').exists() and not POLICY.exists()
    POLICY.mkdir()
    sources={}
    for src in (EXP/'strategic-learned-recruitment-policy-v3').glob('*.py'):
        sources[str(src)]=sha(src)
        text=src.read_text().replace("'strategic-learned-recruitment-run-v2'",repr(HERE.name))
        if src.name=='model_io.py':
            text=once(text,"FORMAT='strategic-learned-recruitment-prior-zero-ppo-checkpoint-v1'", "FORMAT='strategic-active-opponent-paired-ppo-checkpoint-v1'")
            text=once(text,"protocol.get('schema')!='strategic-learned-recruitment-prior-zero-training-v1'",f"protocol.get('schema')!={EPOCH!r}")
        (POLICY/src.name).write_text(text)
    shutil.copy2(EXP/'strategic-learned-recruitment-policy-v3/creature_vocabulary.json',POLICY/'creature_vocabulary.json')
    for name in ('QUALIFICATION.json','audit_game_v6.py','pipeline_common.py','collect_episode_v5.py','collect_cpu.py'):
        sources[str(OLD/name)]=sha(OLD/name)
        text=(OLD/name).read_text().replace("'strategic-learned-recruitment-policy-v3'",repr(POLICY.name))
        (HERE/name).write_text(text)
    shutil.copy2(EXP/'battle-terminal-credit-native-20261023/leases.py',HERE/'leases.py')
    text=(HERE/'pipeline_common.py').read_text()
    text=once(text,"EPOCH='strategic-learned-recruitment-prior-zero-training-v1'",f'EPOCH={EPOCH!r}')
    text=once(text,"DEFAULT_INITIAL=BASE/'initialization-02/recruitment-initialization.pt'", "DEFAULT_INITIAL=EXP/'strategic-learned-recruitment-policy-v3/initialization-02/recruitment-initialization.pt'")
    text=once(text,"    b=require_qualification();native=Path(b['native_directory'])", "    verify_parent_freeze()\n    b=require_qualification();native=Path(b['native_directory'])")
    text=once(text,"    paths.update(control_policy_inputs())", "    paths.update(control_policy_inputs())\n    paths.update([HERE/'MAP_MANIFEST.json',OLD_RUN/'SOURCE_FREEZE.json'])\n    paths.update(Path(e['path']) for e in map_manifest()['variants'])\n    paths.update(Path(e['path']) for e in map_manifest()['sources'].values())\n    paths.add(DEFAULT_INITIAL.parent/'AUDIT.json')")
    text=once(text,"    if len(episodes)!=8", "    if len({e['job']['arm'] for e in episodes})!=1:raise ValueError('Mixed treatments')\n    for e in episodes:\n        j=e['job'];entry=training_variant(j['map'],j['owned_player'],j['opponent'],j['arm'])\n        index=list((m,o,p) for m in MAPS for o in ('EmptyAI','Nullkiller2') for p in (0,1)).index((j['map'],j['opponent'],j['owned_player']))\n        if j['seed']!=2026104400+index or j['logical_update']!=0 or j['multiplier']!=entry['multiplier']:raise ValueError('Unregistered TRAIN job')\n    if len(episodes)!=8")
    text+='''
OLD_RUN=EXP/'strategic-learned-recruitment-run-v2'
MAP_MANIFEST_SHA='88eae3414ec9d7d7dae9bd8390eb4bf3a6ae5dd59fcb87e807d7d45a51702327'
def verify_parent_freeze():
    freeze=OLD_RUN/'SOURCE_FREEZE.json'
    if sha(freeze)!='6c882b314cd69b526644e4730691f4b3e7979780ff3b6f6efce96abb68cbe827':raise ValueError('Frozen parent changed')
    if not all(sha(EXP/p.replace('\\\\','/'))==h for p,h in json.loads(freeze.read_text())['files'].items()):raise ValueError('Protected parent source changed')
def map_manifest():
    if sha(HERE/'MAP_MANIFEST.json')!=MAP_MANIFEST_SHA:raise ValueError('TRAIN map manifest changed')
    result=json.loads((HERE/'MAP_MANIFEST.json').read_text())
    if not result['passed'] or len(result['variants'])!=12:raise ValueError('Unqualified TRAIN variants')
    for e in list(result['sources'].values())+result['variants']:
        if sha(e['path'])!=e['sha256']:raise ValueError('TRAIN map bytes changed')
    return result
def training_variant(map_name,player,opponent,arm):
    if arm not in ('control','curriculum') or opponent not in ('EmptyAI','Nullkiller2'):raise ValueError('Unregistered treatment')
    multiplier=4 if arm=='curriculum' and opponent=='Nullkiller2' else 1
    found=[e for e in map_manifest()['variants'] if (e['source_map'],e['owned_player'],e['multiplier'])==(map_name,player,multiplier)]
    if len(found)!=1:raise ValueError('Wrong TRAIN map/role/treatment')
    return found[0]
'''
    (HERE/'pipeline_common.py').write_text(text)
    shutil.copy2(EXP/'strategic-active-opponent-curriculum-v2-20261023/MAP_MANIFEST.json',HERE/'MAP_MANIFEST.json')
    for name in ('collect_episode_v5.py','collect_cpu.py'):
        text=(HERE/name).read_text()
        text=once(text,'from contextlib import contextmanager','from contextlib import contextmanager\nfrom leases import stop_group')
        start=text.index('def stop(child):');end=text.index('\ndef run(args):',start)
        text=text[:start]+'''def stop(child):
    if child is not None:stop_group(child)
def interrupted(signum,frame):raise KeyboardInterrupt('Collector interrupted: '+str(signum))
signal.signal(signal.SIGTERM,interrupted)

'''+text[end:]
        text=once(text,'cwd=work,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)', 'cwd=work,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,pass_fds=lease_fds)')
        if name=='collect_episode_v5.py':
            text=once(text,'from pipeline_common import source_inputs','from pipeline_common import training_variant,source_inputs')
            text=once(text,"    source=LAB/('data/vcmi/Maps/adv/'+args.map+'.vmap')", "    variant=training_variant(args.map,args.player,args.opponent,args.arm)\n    source=Path(variant['path'])")
            text=once(text,"shutil.copy2(source,work/'data/vcmi/Maps/adv'/source.name)","shutil.copy2(source,work/'data/vcmi/Maps/adv'/(args.map+'.vmap'))")
            text=once(text,"dict(capsule=str(capsule)","dict(arm=args.arm,multiplier=variant['multiplier'],map_variant=variant,capsule=str(capsule)")
            text=once(text,"p.add_argument('--map',choices=", "p.add_argument('--arm',choices=['control','curriculum'],required=True);p.add_argument('--map',choices=")
        else:
            start=text.index("    policy_epoch=getattr");end=text.index('    capsule=capsule.resolve()',start)
            text=text[:start]+"    policy_epoch='active-opponent-paired';broker_path=BROKER\n"+text[end:]
            text=once(text,"p.add_argument('--policy-epoch',choices=['prior-zero','minus-four-control'],default='prior-zero');",'')
        (HERE/name).write_text(text)
    text=(POLICY/'admit_episode_v5.py').read_text()
    text=once(text,'from pipeline_common import source_inputs','from pipeline_common import training_variant,source_inputs')
    text=once(text,"    job={k:plan[k] for k in ['seed','map','owned_player','opponent','logical_update']}","    variant=training_variant(plan['map'],plan['owned_player'],plan['opponent'],plan['arm'])\n    assert plan['map_variant']==variant and plan['multiplier']==variant['multiplier']\n    assert sha(run/('data/vcmi/Maps/adv/'+plan['map']+'.vmap'))==variant['sha256']\n    material=json.dumps(dict(seed=plan['seed'],map=plan['map'],player=plan['owned_player'],opponent=plan['opponent'],logical_update=plan['logical_update']),sort_keys=True).encode()\n    assert plan['sampling_seed']==int.from_bytes(hashlib.sha256(material).digest()[:8],'little')%(2**63-1)\n    job={k:plan[k] for k in ['seed','map','owned_player','opponent','logical_update','arm','multiplier']}")
    (POLICY/'admit_episode_v5.py').write_text(text)
    text=(POLICY/'train_update_v3.py').read_text()
    text=once(text,'def protocol(capsule,purpose,seed):','def protocol(capsule,purpose,seed,arm):')
    text=once(text,'return dict(initial_manual_recruit_bias=0.', 'return dict(training_treatment=arm,initial_manual_recruit_bias=0.')
    text=once(text,"p.add_argument('--purpose',choices=", "p.add_argument('--arm',choices=['control','curriculum'],required=True);p.add_argument('--purpose',choices=")
    text=once(text,"    assert any(s['action_type']=='recruit'", "    assert all(e['job']['arm']==a.arm for e in episodes)\n    assert a.seed==2026104400\n    assert any(s['action_type']=='recruit'")
    text=once(text,'config=protocol(a.capsule,a.purpose,a.seed);','config=protocol(a.capsule,a.purpose,a.seed,a.arm);')
    (POLICY/'train_update_v3.py').write_text(text)
    (HERE/'DERIVATION.json').write_text(json.dumps(dict(parent_sha256=sources,epoch=EPOCH,changes=['isolated strict trained checkpoint format; accepts the same pinned zero initialization','TRAIN canonical map names seed both treatments; private map file contains registered x1/x4 bytes','candidate NK only x4; all8 cells retained','native inherits locks; owned session cleanup','actual admission binds arm, map, multiplier, sampling seed; training binds treatment'],native_changes=False,algorithm_changes=False),indent=2))
    (HERE/'PLAN.md').write_text('''# 主动对手课程：两种训练处理的有限比较

同一零招募先验初始化1510149e，新建各自Adam/RNG链。两组均8局完整新鲜随机on-policy TRAIN，原始两地图×EmptyAI/Nullkiller2×双方，logical_update=0，种子2026104400..4407。control全部×1；curriculum仅Nullkiller2对局己方英雄初始兵量×4，其他因素相同。复用已资格化schema6 capsule02，原生战斗仍由BattleAI代理。

固定4轮episode-balanced PPO、LR3e-4、原终局±1回报/等回合权重/KL停止规则，每组仅1次完整更新。实际样本、Adam次数和KL提前停止全部记录，不强行对齐步数。地图文件在各私有运行目录使用相同规范源地图名；随机种子按规范名/角色/对手/原生seed/update计算。共同seed不保证策略分歧后的逐动作配对或隐藏状态一致。

两组均完成后仅评估共享初始化和两份更新模型：原始未增强DEV河流/储备两图×两对手×双方，种子2026104600..4607，CPU argmax，共24局。无中途看分择模、不剔除失败格、不额外重试/重播种、不打开final test。校准argmax轨迹不准入PPO/专家数据。x4只在矿区校准获得成功，发展图失败仍完整保留；不可声称所有格难度合适。

原始冻结源码/模型/失败证据全部保留。严格GPU锁后pool锁，独占非阻塞；每次原生/采样进程继承锁并在放锁前退出。单GPU学习器；重CPU分析只在其停止后执行。任何无效完整回合/协议/源/资源/审计停止整项，保存失败，不替换seed或放宽闸门。

仅一个初始化、一个更新、8格DEV，结果用于方向判断，不能认证全游戏强度、一般多英雄神经策略或总体胜率。处理同时影响状态分布、回合长度和终局回报，不能把差异全归因于招募动作的正确性。
''')
    print(json.dumps(dict(prepared=True,epoch=EPOCH,policy=str(POLICY),native_runs=0,optimizer_steps=0)))
if __name__=='__main__':main()
