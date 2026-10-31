"""Read-only TRAIN credit diagnosis; never derives a teacher target from DEV."""
import collections, hashlib, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT/'experiments/strategic-learned-free-transfer-policy-v1'
sys.path.insert(0, str(POLICY))
from load_admitted import load
from episode_balanced_ppo import prepare_batch

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    train=Path('/root/heroes3-ai-lab/evaluations/strategic-learned-free-transfer-train-01')
    samples=[]; episodes=[]; jobs={}; inputs={}
    for i in range(8):
        folder=train/f'cell-{i:02d}'/'admitted'
        rows, es, audit=load(folder)
        samples.extend(rows); episodes.extend(es)
        jobs.update({e['episode_id']:e['job'] for e in es})
        inputs[str(folder/'AUDIT.json')]=sha(folder/'AUDIT.json')
    prepared=prepare_batch(samples,episodes=episodes)
    groups=collections.defaultdict(list)
    for i,s in enumerate(samples):
        q=s['request']; c=q['candidates'][s['action']]
        kind=('own_town' if c.get('kind')==4 else 'mine' if c.get('kind')==2 else 'other_move') if c['op']=='move' else c['op']
        opponent=jobs[s['episode_id']]['opponent']
        groups[(opponent,kind)].append((i,s))
    out=[]
    for (opponent,kind),rows in sorted(groups.items()):
        ix=[i for i,s in rows]; adv=prepared['advantages'][ix]; weights=prepared['actor_weights'][ix]
        raw=[s['return']-s['old_value'] for i,s in rows]
        mass=float(weights.sum())
        out.append(dict(opponent=opponent,action=kind,rows=len(rows),episodes=len({s['episode_id'] for i,s in rows}),
            raw_advantage_mean=sum(raw)/len(raw),normalized_advantage_mean=float(adv.mean()),
            positive_normalized_rows=int((adv>0).sum()),negative_normalized_rows=int((adv<0).sum()),
            actor_mass=mass,weighted_normalized_advantage_sum=float((weights*adv).sum()),
            army_mean=sum(s['request']['own_army_value'] for i,s in rows)/len(rows)))
    result=dict(passed=True,scope='2089 original TRAIN observations only; no DEV targets, no causal attribution',
        samples=len(samples),episodes=len(episodes),ppo_metadata=prepared['metadata'],groups=out,input_sha256=inputs,
        native_games_started=0,optimizer_steps=0,
        interpretation='The sign is the actual initial PPO surrogate reinforcement direction, conditional on sampled actions. It is not a causal estimate of refill utility or the gradient of the final updated policy.')
    dest=Path(__file__).parent/'train-credit-01';dest.mkdir(exist_ok=False)
    (dest/'AUDIT.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
