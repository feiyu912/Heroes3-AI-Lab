"""Deliver complete fixed study after the independent raw and NN certificate."""
from pathlib import Path
import hashlib,json,os,shutil,time
HERE=Path(__file__).resolve().parent
SOURCE=Path('/root/heroes3-ai-lab/evaluations/strategic-active-learning-native-01')
PACKAGE=HERE.parent/'strategic-active-opponent-learning-20261024'
REVIEW=HERE/'active-learning-independent-01'
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    result=read(SOURCE/'RESULT.json');audit=read(REVIEW/'AUDIT.json');dev=read(SOURCE/'DEV/RESULT.json')
    assert result['passed'] and audit['passed'] and dev['passed'] and audit['unique_DEV_games']==24 and audit['raw_audits_reexecuted']==40
    assert dev['arm_wins']==audit['DEV_wins']
    freeze=read(PACKAGE/'SOURCE_FREEZE.json');assert all(sha(path)==h for path,h in freeze['files'].items())
    out=HERE/'active-learning-delivery-01';out.mkdir(exist_ok=False);entries={};links={};count=total=0;start=time.monotonic()
    def copy(p,rel):
        nonlocal count,total
        target=out/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
        digest=sha(p);assert digest==sha(target);entries[str(rel)]=dict(sha256=digest,bytes=p.stat().st_size);count+=1;total+=p.stat().st_size
        if count%1000==0:(out/'PROGRESS.json').write_text(json.dumps(dict(verified_files=count,bytes=total,final_certificate=False)))
    for arm in ('control','curriculum'):copy(Path(result['arms'][arm]['training']['checkpoint']),Path(arm+'-update-1.pt'))
    copy(REVIEW/'AUDIT.json',Path('INDEPENDENT_AUDIT.json'))
    for root,prefix in ((SOURCE,Path('native-study')),(REVIEW,Path('independent-review'))):
        for directory,dirs,files in os.walk(root,followlinks=False):
            for name in dirs+files:
                p=Path(directory)/name;rel=prefix/p.relative_to(root)
                if p.is_symlink():links[str(rel)]=os.readlink(p)
                elif p.is_file():copy(p,rel)
    for path in freeze['files']:
        p=Path(path);copy(p,Path('frozen-inputs')/p.relative_to('/'))
    copy(PACKAGE/'SOURCE_FREEZE.json',Path('SOURCE_FREEZE.json'))
    rows=['| 模型 | EmptyAI胜局/4 | Nullkiller2胜局/4 | 总胜局/8 |','|---|---:|---:|---:|']
    for arm in ('initial','control','curriculum'):
        wins={op:sum(pair['arms'][arm]['win'] for pair in dev['pairs'] if pair['job']['opponent']==op) for op in ('EmptyAI','Nullkiller2')}
        rows.append(f"| {arm} | {wins['EmptyAI']} | {wins['Nullkiller2']} | {audit['DEV_wins'][arm]} |")
    flips=[]
    for pair in dev['pairs']:
        c=pair['arms']['control']['win'];x=pair['arms']['curriculum']['win']
        if c!=x:flips.append(dict(job=pair['job'],control_win=c,curriculum_win=x))
    training=audit['training'];gain=audit['DEV_wins']['curriculum']-audit['DEV_wins']['control']
    text=f'''# 主动对手课程：单初始化有限学习对照

原始兵量DEV中，课程处理相对控制净胜局差为{gain:+d}/8。原始兵量训练组相对初始化多胜1局；这是单个固定开发格中的正观察，尚非稳定收益。此处仅报告一次预登记开发比较，不晋升模型，不触final test，不认证总体胜率。

'''+ '\n'.join(rows)+f'''

两组各使用同1510149e零先验初始化、各自新建Adam/RNG，完成8局全新随机on-policy TRAIN。
control全部原兵量；curriculum仅Nullkiller2格己方英雄初始兵量×4。相同schema6原生运行、网络、终局±1、等回合PPO/LR与4epoch/KL停止规则。
control实际{training['control']['samples']}条、{training['control']['actual_Adam']}次Adam、训练{training['control']['wins']}/8胜；
curriculum实际{training['curriculum']['samples']}条、{training['curriculum']['actual_Adam']}次Adam、训练{training['curriculum']['wins']}/8胜。
并非相同转移/优化器步数预算，不能将处理包差异单独归因于招募机制。两条新链也不能与既有248/208步或战斗计数相加冒充连续训练。

地图在私有目录使用相同规范源名，共同采样seed已逐格核验；策略分歧后没有逐动作/隐藏状态配对保证。
4个未改变处理的EmptyAI训练格，完整归档proposal流在两组间逐字节相同；主动对手格因军队处理而状态不同。
校准argmax轨迹未作PPO/专家样本，发展图失败完整保留，无追加重试/重播种或看分择模。
三模型24局在原始未增强DEV上独立运行；原8格DEV地图曾见过，仅seed为新，不能称全新地图泛化。
唯一胜负翻转为储备图/红方/Nullkiller2/seed2026104606：初始化负、控制胜、课程负，初始公开请求一致。三者分别16/23/13次建造、593/426/290次招募；学习改变了多个决策分支，不能单独归因于招募头或某个动作。该开发轨迹未作为教师数据。

全部16训练局严格原生资源/库存/军队/请求ACK/完整终局审计和完整CUDA随机采样重放准入；实际首回合己方军队与注册处理一致。
两份完整检查点分别实际CUDA恢复模型、命名Adam及CPU/CUDA/Python RNG，12类损坏状态拒绝且不污染活状态。
另独立重新执行40份完整原生审计，重放DEV全部{audit['DEV_full_CPU_proposals_recomputed']}次CPU完整proposal（概率/值/动作/请求/响应），逐项相等。
原始审计器及门不变，新包装器只缓存不可变日志的纯解析，已与最长校准局原无缓存完整报告比对一致。

完整普通运行文件、独立报告、两份恢复模型和冻结源输入已复制到此目录，逐文件与原件SHA一致。
外部Data/Mods/client等符号链接目标单独登记，不遍历复制，不声称离线免依赖。所有具体路径和哈希见ARCHIVE.json。
此处原生战斗仍由BattleAI代理，免费兵力转移仍为脚本；一般多英雄/城镇神经策略、学习招募的稳定收益与全游戏目标仍未完成。
'''
    (out/'REPORT.md').write_text(text)
    report=dict(passed=True,source=str(SOURCE),ordinary_files=count,bytes=total,seconds=time.monotonic()-start,all_copied_SHA_equal=True,files=entries,symlink_targets_not_traversed=links,training=training,DEV_wins=audit['DEV_wins'],curriculum_minus_control_net_wins=gain,control_vs_curriculum_flips=flips,independent_CPU_decisions=audit['DEV_full_CPU_proposals_recomputed'],model_promoted=False,final_test_touched=False)
    (out/'ARCHIVE.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k not in ('files','symlink_targets_not_traversed')},indent=2))
if __name__=='__main__':main()
