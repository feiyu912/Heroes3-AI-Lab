"""Count actual move-choice opportunities; no counterfactual rewards or admitted rows."""
import collections,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=Path('/root/heroes3-ai-lab/evaluations/typed-curriculum-paired-dev-02')
result=json.loads((ROOT/'RESULT.json').read_text());assert result['passed']
groups={};inputs={}
for arm in ('a','b'):
    counts=collections.Counter();by_pair=[]
    for i in range(8):
        path=ROOT/f'pair-{i:02d}/{arm}/native/agent/typed-broker.jsonl'
        rows=[json.loads(x) for x in path.read_text().splitlines()];local=collections.Counter()
        inputs[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
        for p in rows:
            q=p['request'];n=sum(c['op']=='move' for c in q['candidates'])
            key='no_move' if n==0 else 'one_move_plus_stop' if n==1 else 'multiple_move_choices'
            local[key]+=1
            if q['visible_threats']:
                local['visible_threat_rows']+=1
                if n==1:local['visible_threat_one_move_rows']+=1
            chosen=q['candidates'][p['response']['selected_index']]
            if chosen['op']=='end_turn':local['policy_stop']+=1
        counts.update(local);by_pair.append(dict(pair=i,rows=len(rows),counts=dict(local)))
    total=sum(counts[k] for k in ['no_move','one_move_plus_stop','multiple_move_choices'])
    groups[arm]=dict(rows=total,counts=dict(counts),one_move_fraction=counts['one_move_plus_stop']/total,
        multi_move_fraction=counts['multiple_move_choices']/total,by_pair=by_pair)
out=HERE/'action-opportunity-audit-01';out.mkdir(exist_ok=False)
report=dict(passed=True,groups=groups,input_sha256=inputs,optimizer_steps=0,native_games=0,training_samples=0,
    limitation='A one-move candidate set is observed evidence; it does not alone prove commitment pruning caused that row. Move-plus-stop is mathematically a free PPO row, but offers no alternative destination. No proposal to remove target commitment without a looping regression.')
(out/'AUDIT.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:{n:v for n,v in g.items() if n!='by_pair'} for k,g in groups.items()},indent=2))
