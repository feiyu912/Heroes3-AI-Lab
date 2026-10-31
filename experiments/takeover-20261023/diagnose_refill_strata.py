"""Stratify original TRAIN chosen town moves by observed friendly stock only."""
import collections,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'experiments/strategic-learned-free-transfer-policy-v1'))
from load_admitted import load
from episode_balanced_ppo import prepare_batch
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    samples=[];es=[];jobs={};inputs={}
    train=Path('/root/heroes3-ai-lab/evaluations/strategic-learned-free-transfer-train-01')
    for n in range(8):
        p=train/f'cell-{n:02d}'/'admitted';ss,ee,_=load(p)
        samples+=ss;es+=ee;jobs.update({e['episode_id']:e['job'] for e in ee});inputs[str(p/'AUDIT.json')]=sha(p/'AUDIT.json')
    batch=prepare_batch(samples,episodes=es);groups=collections.defaultdict(list);details=[]
    for i,s in enumerate(samples):
        q=s['request'];c=q['candidates'][s['action']]
        if c['op']!='move' or c['kind']!=4:continue
        towns=[t for t in q['own_towns'] if t['position']==c['position']];assert len(towns)==1
        t=towns[0];ratio=t['army_value']/max(1,q['own_army_value'])
        group='empty' if t['army_value']==0 else 'stock_at_least_half_hero' if ratio>=.5 else 'smaller_stock'
        r=dict(episode_id=s['episode_id'],opponent=jobs[s['episode_id']]['opponent'],request_id=q['request_id'],day=q['day'],own_turn=q['own_turn'],hero_army=q['own_army_value'],town_army=t['army_value'],stock_ratio=ratio,path_cost=c['path_cost'],normalized_advantage=float(batch['advantages'][i]),actor_weight=float(batch['actor_weights'][i]),return_value=s['return'])
        details.append(r);groups[(r['opponent'],group)].append(r)
    summary=[]
    for (opponent,stock),rs in sorted(groups.items()):
        summary.append(dict(opponent=opponent,stock=stock,rows=len(rs),positive=sum(r['normalized_advantage']>0 for r in rs),negative=sum(r['normalized_advantage']<0 for r in rs),advantage_mean=sum(r['normalized_advantage'] for r in rs)/len(rs),weighted_advantage_sum=sum(r['normalized_advantage']*r['actor_weight'] for r in rs)))
    out=Path(__file__).parent/'refill-strata-01';out.mkdir(exist_ok=False)
    result=dict(passed=True,TRAIN_only=True,groups=summary,details=details,input_sha256=inputs,script_sha256=sha(__file__),limitations='Stock/hero army value is a visible-state stratification, not proof of actual eventual transfer, optimality or a teacher target. No DEV, native execution or gradient update.',optimizer_steps=0)
    (out/'AUDIT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
