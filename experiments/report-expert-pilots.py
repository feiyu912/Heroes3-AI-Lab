"""Publish actual completed pilot comparisons, including negative results."""
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent


def read(path): return json.loads(path.read_text(encoding='utf-8-sig'))
def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    human_path = HERE/'human-tactics-v1/pilot-comparison.json'
    wait_path = HERE/'expert-knowledge-v1/wait-variant-v2/source-bc-heldout.json'
    retention_path = HERE/'expert-retention-v1/development-results.json'
    for path,flag in [(human_path,'completed'),(wait_path,'complete'),(retention_path,'complete')]:
        if not path.exists() or not read(path).get(flag):
            print('Pending real completed evidence: '+str(path))
            return 2
    human,wait,retention = [read(path) for path in [human_path,wait_path,retention_path]]
    assert {name:row['battles'] for name,row in human['groups'].items()}=={'baseline':12,'bc':12}
    assert len(wait['results'])==8 and len(retention['results'])==6
    wait_groups = {}
    for label in ['baseline','source-bc']:
        rows = [row for row in wait['results'] if row['policy']==label]
        assert len(rows)==4
        for row in rows:
            raw = read(Path(row['report']))
            assert raw['completed'] and raw['terminated'] and not raw['truncated']
            assert raw['terminal_outcome']['result_type']==0 and raw['invalid_actions']==0
            assert digest(raw['model_checkpoint'])==raw['model_sha256']
            assert raw['success']==row['success'] and raw['permanent_units_lost']==row['loss']
        wait_groups[label]=dict(battles=4,wins=sum(row['success'] for row in rows),
            first_wait=sum(row['first_action']==0 for row in rows),
            actual_windows=sum(row['window_verified'] for row in rows),
            mean_ghost_dragons_lost=sum(row['loss'] for row in rows)/4)
    lines = ['# 专家课程试点：实际完成结果','',
        '本报告汇总冻结模型后的专项测试，以及另行执行的普通开发集回退检查。真人操作轨迹数为0。整体胜率目标仍未达到。','',
        '|试验|模型|胜局|平均阵亡数量|','|---|---|---:|---:|']
    for name,row in human['groups'].items():
        assert row['truncations']==0 and row['invalid_actions']==0 and row['unknown_final_losses']==0
        lines.append(f'|185条Q2脚本标签|{name}|{row["wins"]}/{row["battles"]}|{row["mean_permanent_units_lost"]:.3f}|')
    for name,row in wait_groups.items():
        lines.append(f'|4条来源支持WAIT标签|{name}|{row["wins"]}/4|{row["mean_ghost_dragons_lost"]:.3f}条幽灵龙|')
    lines += ['', 'WAIT首步及真实跨轮窗口：', '']
    for name,row in wait_groups.items():
        lines.append(f'- {name}：首步WAIT {row["first_wait"]}/4，真实窗口 {row["actual_windows"]}/4。')
    lines += ['', '普通开发集对照（每项96局，固定48场景、双角色、同种子；不是新的独立确认）：','',
        '|模型|对手|胜局|截断|非法动作|','|---|---|---:|---:|---:|']
    for item in retention['results']:
        summary=item['summary'];assert summary['battles']==96
        assert digest(item['report'])==item['report_sha256']
        lines.append(f'|{item["model"]}|{item["opponent"]}|{summary["wins"]}/96|{summary["truncated"]}|{summary["invalid_actions"]}|')
    lines += ['', '训练拟合、合法动作、机制窗口、独立战损和普通胜率是不同证据。WAIT仍限同兵种家族和固定回应，老化及随机伤害尚未隔离；Q2整局动作未被认证最优。覆盖关系不能当实际伤害或战术成功率。不同兵种的阵亡数量不是等价值军力损失。',
        '', '不根据这些专项测试继续挑选或调参后重称独立；进一步调整使用训练/开发数据，最终能力需要新冻结模型与新确认集。']
    report=dict(complete=True,goal_achieved=False,human=human,source_wait=wait_groups,retention=retention,
        evidence_sha256={str(path):digest(path) for path in [human_path,wait_path,retention_path]})
    (HERE/'EXPERT_PILOT_RESULTS.json').write_text(json.dumps(report,indent=2)+'\n')
    (HERE/'EXPERT_PILOT_RESULTS.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps(dict(human=human['groups'],source_wait=wait_groups),indent=2))
    return 0


if __name__=='__main__':sys.exit(main())
