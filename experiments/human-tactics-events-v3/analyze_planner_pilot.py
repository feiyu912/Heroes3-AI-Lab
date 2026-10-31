import gzip
import hashlib
import json
from pathlib import Path
from events_provenance import digest


def main():
    here=Path(__file__).resolve().parent/'planner-pilot-v1'
    pairs={};rows=[]
    for path in sorted((here/'runs/train').glob('*.json')):
        r=json.loads(path.read_text())
        if not r.get('completed'):
            continue
        assert digest(r['archive'])==r['archive_sha256']
        with gzip.open(r['archive'],'rt') as f:data=json.load(f)
        side=str(int(r['role']=='defender'))
        casualties=r['terminal_outcome']['casualties'][side]
        trace=[dict(observation=t['observation_before'],action=t['executed_action']) for t in data['transitions']]
        row=dict(file=str(path),scenario=r['scenario'],role=r['role'],seed=r['seed'],horizon=r['teacher_horizon'],
                 success=r['success'],main_loss=casualties.get('6',0),total_loss=sum(casualties.values()),
                 steps=r['steps'],normal=r['terminated'] and not r['truncated'] and r['terminal_outcome']['result_type']==0,
                 teacher_cpu_eval_total_us=r['teacher_cpu_eval_total_us'],
                 teacher_cpu_eval_mean_us=r['teacher_cpu_eval_mean_us'],
                 teacher_cpu_eval_p95_us=r['teacher_cpu_eval_p95_us'],
                 decision_trace_sha256=hashlib.sha256(json.dumps(trace,sort_keys=True,separators=(',',':')).encode()).hexdigest())
        rows.append(row);pairs.setdefault((r['scenario'],r['role'],r['seed']),{})[r['teacher_horizon']]=row
    paired=[]
    for k,p in sorted(pairs.items()):
        if 2 not in p or 4 not in p:
            continue
        a,b=p[2],p[4]
        paired.append(dict(scenario=k[0],role=k[1],seed=k[2],delta_main_loss=b['main_loss']-a['main_loss'],
                           delta_total_loss=b['total_loss']-a['total_loss'],delta_wins=int(b['success'])-int(a['success']),
                           identical_state_action_trace=a['decision_trace_sha256']==b['decision_trace_sha256'],
                           cpu_ratio=b['teacher_cpu_eval_total_us']/a['teacher_cpu_eval_total_us']))
    result=dict(episodes=len(rows),pairs=len(paired),normal=sum(r['normal'] for r in rows),
                mean_delta_main_loss=sum(p['delta_main_loss'] for p in paired)/len(paired) if paired else None,
                net_wins=sum(p['delta_wins'] for p in paired),
                identical_paired_traces=sum(p['identical_state_action_trace'] for p in paired),
                per_horizon={str(h):dict(total_search_us=sum(r['teacher_cpu_eval_total_us'] for r in rows if r['horizon']==h),
                    total_decisions=sum(r['steps'] for r in rows if r['horizon']==h)) for h in (2,4)},
                certified_stronger_teacher=False,bc_eligible=False,paired=paired,runs=rows)
    (here/'PAIRED_RESULTS.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k not in ('runs','paired')}))


if __name__=='__main__':
    main()
