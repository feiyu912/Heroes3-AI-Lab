"""One-shot file status; no process polling, native or GPU work."""
import argparse,json
from pathlib import Path
def main():
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,default=Path('/root/heroes3-ai-lab/evaluations/battle-continuation-lr-paired-01'));a=p.parse_args();arms={}
    for name in ('control','candidate'):
        path=a.run/name/'training.json'
        if not path.exists():arms[name]=dict(state='not_yet_reported',parent_historical_Adam=3840,new_Adam_steps_observed=0);continue
        d=json.loads(path.read_text());records=d.get('records',[]);r=records[-1] if records else {}
        total=d.get('actual_Adam_steps',r.get('actual_Adam_steps_total',3840))
        arms[name]=dict(state='completed' if d.get('completed') else 'failed' if d.get('error') else 'running',global_update=r.get('update',30),stage_updates=len(records),parent_historical_Adam=3840,cumulative_Adam_steps=total,new_Adam_steps_observed=total-3840,new_samples=sum(r['samples'] for r in records),normal_terminals=r.get('episodes',0),wins=r.get('wins',0),truncations=r.get('truncations',0),last_complete_checkpoint=d.get('checkpoint'),error=d.get('error'))
    result_path=a.run/'RESULT.json';result=json.loads(result_path.read_text()) if result_path.exists() else None
    print(json.dumps(dict(arms=arms,controller_result_exists=result is not None,controller_passed=result.get('passed') if result else False,final_DEV_reports=len(result.get('DEV',[])) if result else 0,
        limitation='File observation only. Historical3840 is not new training; two arms are distinct models, do not combine their Adam counts as one model.'),indent=2))
if __name__=='__main__':main()
