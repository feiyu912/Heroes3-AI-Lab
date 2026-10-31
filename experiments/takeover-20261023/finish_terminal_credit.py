"""Compose and archive completed recovered comparison, only after full96 raw/NN audit."""
import collections,hashlib,json,shutil
from pathlib import Path
HERE=Path(__file__).resolve().parent
OLD=Path('/root/heroes3-ai-lab/evaluations/battle-terminal-credit-01')
RUN=Path('/root/heroes3-ai-lab/evaluations/battle-terminal-credit-recovery-01')
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    result=read(RUN/'RESULT.json');assert result['passed'] and result['recovered_comparison'] and result['original_run_passed'] is False
    assert read(OLD/'RESULT.json')['passed'] is False
    recovery=read(HERE/'terminal-credit-recovery-review-01/AUDIT.json');assert recovery['recovery_boundary_verified'] and not recovery['original_resource_gate_passed']
    phases={};new_adam={};inputs={};total_native=0
    for arm in ('control','candidate'):
        stages=[OLD/(arm+'-micro'),OLD/'control-phase-1' if arm=='control' else RUN/'candidate-phase-1',RUN/(arm+'-phase-2'),RUN/(arm+'-phase-3')]
        phases[arm]=[];new_adam[arm]=0
        for phase,stage in enumerate(stages):
            if arm=='control' and phase==1:
                assert sha(stage/'update-64.pt')==recovery['boundaries']['64']['sha256']
                actual=recovery['boundaries']['64']['actual_Adam_steps']-7936;assert actual==256
                row=dict(phase=phase,admitted=1024,suffix=1024,native=2048,actual_Adam=actual,recovered_after_resource_failure=True,normal_stage_resource_pass=False,certificate=str(HERE/'terminal-credit-recovery-review-01/AUDIT.json'))
            else:
                d=read(stage/'RESULT.json');audit=read(stage/'AUDIT.json');assert d['passed'] and d['normal_workers_shutdown'] and audit['passed']
                assert [r['update'] for r in d['records']]==[61+phase*2,62+phase*2] and all(r['actual_Adam']==128 for r in d['records'])
                assert d['actual_Adam_steps']==7680+256*(phase+1)
                assert len(audit['phase_checks'])==1 and audit['phase_checks'][0]['phase']==phase
                c=audit['phase_checks'][0];assert c['admitted_observed_rows']==c['suffix_observed_rows']==1024 and c['suffix_loss_rows']==0 and c['all_journal_files']==256
                row=dict(phase=phase,admitted=1024,suffix=1024,native=2048,actual_Adam=sum(r['actual_Adam'] for r in d['records']),eligible_workers=c['eligible_workers'],target_reasons=dict(collections.Counter(c['reasons'])),certificate=str(stage/'AUDIT.json'))
                for name in ('RESULT.json','AUDIT.json','RESTORATION.json'):inputs[str(stage/name)]=sha(stage/name)
            new_adam[arm]+=row['actual_Adam'];total_native+=row['native'];phases[arm].append(row)
        assert new_adam[arm]==1024 and result['arms'][arm]['actual_Adam_steps']==8704
        assert result['arms'][arm]['admitted_stage_rows']==result['arms'][arm]['suffix_stage_rows']==4096
        assert sha(result['arms'][arm]['checkpoint'])==result['arms'][arm]['checkpoint_sha256']
    qualification=read(OLD/'qualification/AUDIT.json');assert qualification['passed'] and qualification['qualify_only']
    assert read(OLD/'qualification/RESULT.json')['new_Adam_steps']==0
    raw=read(RUN/'DEV-RAW-AUDIT.json');nn=read(RUN/'DEV-NN-REPLAY/AUDIT.json');dev=read(RUN/'DEV-RESULT.json')
    assert raw['passed'] and nn['passed'] and dev['passed'] and dev['raw96_recomputed'] and dev['full_NN_replayed']
    assert raw['DEV']['unique_games']==nn['unique_games']==96 and nn['actual_full_NN_CPU_probability_replay']
    for path,expected in raw['raw_artifact_sha256'].items():assert sha(path)==expected
    for path,expected in read(RUN/'FREEZE.json')['input_sha256'].items():assert sha(path)==expected
    comparisons={}
    for opp in ('BattleAI','MMAI_MODEL'):
        p=[r for r in raw['DEV']['control_vs_candidate_pairs'] if r['opponent']==opp];assert len(p)==16
        comparisons[opp]=dict(candidate_positive_flips=sum(r['win_delta']>0 for r in p),candidate_negative_flips=sum(r['win_delta']<0 for r in p),same_result=sum(r['win_delta']==0 for r in p),mean_candidate_minus_control_units_lost=sum(r['units_lost_delta'] for r in p)/16)
    memory=[json.loads(x) for x in (RUN/'MEMORY.jsonl').read_text().splitlines() if x.strip()]
    out=HERE/'terminal-credit-delivery-01';out.mkdir(exist_ok=False)
    files={}
    def copy(src,rel):
        target=out/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,target);assert sha(src)==sha(target);files[str(rel)]={'sha256':sha(target),'bytes':target.stat().st_size}
    for arm in ('control','candidate'):copy(Path(result['arms'][arm]['checkpoint']),Path(arm+'-update-68.pt'))
    for name in ('PLAN.json','FREEZE.json','RESULT.json','RESULT.partial.json','DEV-RESULT.json','DEV-RAW-AUDIT.json','MEMORY.jsonl','DEV-NN-REPLAY/AUDIT.json'):
        copy(RUN/name,Path('evidence')/name)
    for item in result['DEV']:copy(Path(item['report']),Path('evidence/dev')/(item['model']+'-'+item['opponent']+'.json'))
    copy(HERE/'terminal-credit-recovery-review-01/AUDIT.json',Path('evidence/CONTROL64_RECOVERY.json'))
    copy(HERE/'terminal-credit-independent-01/COMMON_FIRST_UPDATE.json',Path('evidence/COMMON_FIRST_UPDATE.json'))
    copy(HERE/'terminal-credit-independent-01/MICRO_TARGET_COMPARISON.json',Path('evidence/MICRO_TARGET_COMPARISON.json'))
    report={'passed':True,'scope':'Recovered bounded development comparison; original resource-stopped run remains failed. No promotion or population win-rate certification.',
        'original_run_passed':False,'recovered_comparison':True,'phases':phases,'new_Adam_per_arm':new_adam,'cumulative_Adam_each':8704,
        'training_admitted_rows_each':4096,'suffix_zero_loss_native_rows_each':4096,'native_training_transitions_both_arms':total_native,
        'additional_zero_optimizer_qualification_transitions':2048,'DEV_unique_games':96,'DEV_full_CPU_decisions_recomputed':nn['decisions'],
        'DEV_summary':raw['DEV']['summaries'],'candidate_vs_control':comparisons,
        'recovery_minimum_available_mib':min(r['available_mib'] for r in memory),'recovery_maximum_swap_mib':max(r['swap_used_mib'] for r in memory),
        'checkpoint_sha256':{arm:result['arms'][arm]['checkpoint_sha256'] for arm in ('control','candidate')},
        'raw_training_journals_preserved_WSL':str(OLD)+' and '+str(RUN),'full_training_journals_copied':False,
        'raw_DEV_artifacts_rehashed':len(raw['raw_artifact_sha256']),'stage_certificate_sha256':inputs,
        'model_promoted':False,'final_test_touched':False,'archive_files':files}
    (out/'AUDIT.json').write_text(json.dumps(report,indent=2))
    table=['| 模型 | BattleAI胜局/16 | BattleAI平均永久损兵 | MMAI胜局/16 | MMAI平均永久损兵 |','|---|---:|---:|---:|---:|']
    for model in ('parent60','control','candidate'):
        a=report['DEV_summary'][model+'/BattleAI'];b=report['DEV_summary'][model+'/MMAI_MODEL']
        table.append(f"| {model} | {a['wins']} | {a['mean_units_lost']:.4f} | {b['wins']} | {b['mean_units_lost']:.4f} |")
    text='''# 终局延伸：恢复后的有限战斗对照

终局延伸没有提高独立DEV胜局：两组BattleAI均15/16、MMAI均13/16；父模型MMAI为14/16。候选对控制在MMAI出现一正一负翻转，未获得净胜局收益，不晋升模型。

两臂均沿真实完整优化器链从control60继续到68，各新增1024次实际Adam，累计8704。
每臂4096条PPO准入、4096条零损失后缀原生观察；另有2048条零优化原生资格观察。
原始运行的资源门失败保持false；这是明确恢复后的比较，存在先前不对称资源停止，
不能写成原始全程协议通过。没有重跑control phase1、重置Adam、重播种或强制优化预算。

'''+ '\n'.join(table)+f'''

96局全部实际正常终局，独立复算全部原始证据，并完整CPU重放{nn['decisions']}次NN决策。
配对翻转和损兵差详见AUDIT.json。样本属于开发评估，不是总体稳定胜率认证；
没有模型自动升级，也未触碰final test。人类专家/视频理解或完整战略能力没有据此获证。

第61次更新后两臂完整模型、Adam和四RNG完全一致；第一阶段全部采样/后缀数据一致。
首次差异更新62中253条准入目标变化，最大绝对差0.9555967，182张量产生真实差异。
这证明该学习因素实际生效，收益仍以此处独立评估为准。

完整两份68检查点包含模型、命名Adam、计数及CPU/CUDA/Python/NumPy RNG，
每次更新读取回验和各阶段完整CPU恢复通过；control64另有实际CUDA重装证明。
检查点和报告复制到本目录并逐文件与原件SHA一致；全训练journal保留WSL原目录，
没有冒充已全部复制。冻结源码、原生库、地图和依赖仍按FREEZE路径复现。

恢复期间最低可用内存{report['recovery_minimum_available_mib']:.1f}MiB，最高swap
{report['recovery_maximum_swap_mib']:.1f}MiB；大型CPU分析在学习器停止后执行。
此前失败时的具体资源值没有保存，不能据后续成功证明唯一根因。
'''
    (out/'REPORT.md').write_text(text)
    print(json.dumps({k:v for k,v in report.items() if k not in ('archive_files','phases','stage_certificate_sha256')},indent=2))
if __name__=='__main__':main()
