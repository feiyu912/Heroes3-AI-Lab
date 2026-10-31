"""Lightweight JSON/process monitor; never imports a neural runtime."""
import argparse,json
from pathlib import Path
def read(p):return json.loads(p.read_text())
def main():
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);a=p.parse_args();r=a.run;out={}
    if (r/'RESULT.json').exists():
        d=read(r/'RESULT.json');out.update(passed=d['passed'],error=d.get('error'))
    if (r/'PROGRESS.json').exists():
        d=read(r/'PROGRESS.json');out.update(current_arm=d.get('arm'),completed_cells=len(d.get('completed',[])),finished_arms=list(d.get('finished_arms',{})))
    out['cells']=[]
    for arm in ('control','curriculum'):
        for cell in sorted((r/arm).glob('cell-*')):
            data=dict(cell=str(cell.relative_to(r)),prepared=(cell/'native/PLAN.json').exists(),completed=False,audited=(cell/'raw-audit/AUDIT.json').exists(),admitted=(cell/'admitted/AUDIT.json').exists())
            if (cell/'native/EXECUTION.json').exists():data['completed']=read(cell/'native/EXECUTION.json')['game_completed']
            elif (cell/'native/strategy-trace.jsonl').exists():
                with (cell/'native/strategy-trace.jsonl').open('rb') as f:
                    f.seek(0,2);end=f.tell();f.seek(max(0,end-65536));lines=f.read().splitlines()
                for line in reversed(lines):
                    try:q=json.loads(line);data['last_event']=q['event'];data['last_day']=q.get('day');break
                    except (ValueError,KeyError):pass
            out['cells'].append(data)
        if (r/arm/'update-01/RESULT.json').exists():
            q=read(r/arm/'update-01/RESULT.json');out[arm+'_training']={k:q.get(k) for k in ('completed_update','samples','cuda_optimizer_steps','training_wins','training_losses','error')}
    if (r/'DEV/PROGRESS.json').exists():out['DEV_pairs']=len(read(r/'DEV/PROGRESS.json')['pairs'])
    if (r/'DEV/RESULT.json').exists():out['DEV']={k:v for k,v in read(r/'DEV/RESULT.json').items() if k not in ('pairs','completed_pairs')}
    print(json.dumps(out))
if __name__=='__main__':main()
