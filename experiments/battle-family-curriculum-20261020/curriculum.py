"""Registered normal TRAIN-only families and transparent unfinished-fragment accounting."""
import collections,hashlib,json
from pathlib import Path
import numpy as np
SEED=2026102012
def family(case):return tuple(sorted(s['type'] for s in case['armies'][0] if s))
def registered(path,seed=SEED):
    assert seed==SEED;cases=json.loads(Path(path).read_text());pools=collections.defaultdict(list)
    for index,c in enumerate(cases):
        if c['split']!='train':continue
        assert 'tactic_id' not in c and c['id'].startswith('diverse-')
        a=sorted((s['type'],s['amount']) for s in c['armies'][0] if s);b=sorted((s['type'],s['amount']) for s in c['armies'][1] if s);assert a==b
        pools[family(c)].append(dict(index=index,case=c))
    assert len(pools)==6 and sum(map(len,pools.values()))==192
    rng=np.random.default_rng(seed);chosen=[]
    for fid,key in enumerate(sorted(pools)):
        pool=pools[key];c=pool[int(rng.integers(len(pool)))];chosen.append(dict(family=fid,species=list(key),scenario_index=c['index'],scenario_id=c['case']['id'],map=c['case']['map'],map_sha256=c['case']['sha256']))
    phases=[]
    for phase in range(2):
        raw=[]
        for c in chosen:
            opponent=['BattleAI','MMAI_MODEL'][(c['family']+phase)%2]
            for role in ('attacker','defender'):raw.append(dict(c,opponent=opponent,role=role))
        order=np.random.default_rng(seed+phase*1777).permutation(12);rows=[dict(raw[int(i)],slot=slot,seed=seed+phase*1000+slot) for slot,i in enumerate(order)];phases.append(rows)
    keys=[(r['family'],r['role'],r['opponent']) for rows in phases for r in rows]
    assert len(set(keys))==len(keys)==24
    return dict(schema='normal-TRAIN-six-family-24-cell-v1',seed=seed,families=chosen,phases=phases)
def configs(path,seed,phase,run):
    rows=registered(path,seed)['phases'][phase];out=[]
    for r in rows:
        p=Path('/root/heroes3-ai-lab/data/vcmi/Maps')/r['map'];assert hashlib.sha256(p.read_bytes()).hexdigest()==r['map_sha256']
        role=r['role'];opponent=r['opponent'];out.append(dict(map=r['map'],role=role,opponent=opponent,initial_reset_once=True,
            opponent_model='DATA/MMAI/models/lab-upstream-'+('defender' if role=='attacker' else 'attacker')+'.onnx' if opponent=='MMAI_MODEL' else None,
            seed=r['seed'],feature_version='upstream-graph-v15',step_cost=0.,family=r['family'],TRAIN_scenario_index=r['scenario_index'],
            worker_root=f'/root/heroes3-ai-lab/workers/family-{run}/{phase}-{r["slot"]}'))
    return out
def resource_gate():
    m={k:int(v.strip().split()[0]) for k,v in (line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines())}
    assert m['MemAvailable']>4*1024*1024 and m['SwapTotal']-m['SwapFree']<256*1024,'Insufficient memory reserve before 12-worker phase'
    return dict(available_mib=m['MemAvailable']/1024,swap_used_mib=(m['SwapTotal']-m['SwapFree'])/1024)
def close_evidence(phase,live_steps,configs,reason):
    assert len(live_steps)==len(configs)==12
    return dict(phase=phase,reason=reason,terminated=False,truncated=False,reward_assigned=False,
        unfinished_fragments=[dict(slot=i,owned_steps=n,family=configs[i]['family'],role=configs[i]['role'],opponent=configs[i]['opponent']) for i,n in enumerate(live_steps) if n>0],
        zero_step_post_reset_or_unacted_battles=sum(n==0 for n in live_steps),
        meaning='Close of native environments, not extra sampled transitions or outcomes; previous rollout returns already used valid bootstrap.')
