"""Predeclared 60 normal TRAIN maps x two sides x two actual native opponents."""
import collections,hashlib,json,shutil
from pathlib import Path
import numpy as np
SEED=2026102016
WORKERS=16
PHASES=15
SCHEDULE_EPOCH='candidate57-resume-fresh-phase13-20261023-v1'
NATIVE_SEED_BASE=2026103800
CASES_PER_FAMILY=10
def family(case):return tuple(sorted(s['type'] for s in case['armies'][0] if s))
def registered(path,seed=SEED):
    assert seed==SEED;cases=json.loads(Path(path).read_text());pools=collections.defaultdict(list)
    for index,c in enumerate(cases):
        if c['split']!='train':continue
        assert 'tactic_id' not in c and c['id'].startswith('diverse-')
        a=sorted((s['type'],s['amount']) for s in c['armies'][0] if s);b=sorted((s['type'],s['amount']) for s in c['armies'][1] if s);assert a==b
        pools[family(c)].append(dict(index=index,case=c))
    assert len(pools)==6 and sum(map(len,pools.values()))==192
    rng=np.random.default_rng(seed);chosen_by_family=[];families=[]
    for fid,key in enumerate(sorted(pools)):
        pool=pools[key];assert len(pool)>=CASES_PER_FAMILY
        drawn=rng.choice(len(pool),size=CASES_PER_FAMILY,replace=False);selected=[]
        for choice in drawn:
            c=pool[int(choice)];selected.append(dict(family=fid,species=list(key),scenario_index=c['index'],scenario_id=c['case']['id'],map=c['case']['map'],map_sha256=c['case']['sha256']))
        chosen_by_family.append(selected);families.append(dict(family=fid,species=list(key),TRAIN_pool_size=len(pool),selected=selected))
    # Round-robin families covers all six in each six-map block. Each four-map
    # phase exposes the SAME cases to every role/opponent, avoiding case bias.
    chosen=[chosen_by_family[f][case] for case in range(CASES_PER_FAMILY) for f in range(6)]
    assert len({c['scenario_index'] for c in chosen})==60
    phases=[]
    for phase in range(PHASES):
        raw=[]
        for c in chosen[phase*4:(phase+1)*4]:
            for opponent in ('BattleAI','MMAI_MODEL'):
                for role in ('attacker','defender'):raw.append(dict(c,opponent=opponent,role=role))
        order=np.random.default_rng(seed+phase*1777).permutation(WORKERS)
        rows=[dict(raw[int(i)],slot=slot,seed=NATIVE_SEED_BASE+phase*1000+slot) for slot,i in enumerate(order)];phases.append(rows)
    keys=[(r['scenario_index'],r['role'],r['opponent']) for rows in phases for r in rows];assert len(set(keys))==len(keys)==240
    count=collections.Counter((r['family'],r['role'],r['opponent']) for rows in phases for r in rows);assert len(count)==24 and set(count.values())=={10}
    return dict(schema='normal-TRAIN-60case-240-slot-v1',seed=seed,selected_cases=60,cases_per_family=10,families=families,phases=phases)
def configs(path,seed,phase,run):
    assert type(phase) is int and 0<=phase<PHASES
    rows=registered(path,seed)['phases'][phase];out=[]
    for r in rows:
        p=Path('/root/heroes3-ai-lab/data/vcmi/Maps')/r['map'];assert hashlib.sha256(p.read_bytes()).hexdigest()==r['map_sha256']
        role=r['role'];opponent=r['opponent'];out.append(dict(map=r['map'],role=role,opponent=opponent,initial_reset_once=True,
            opponent_model='DATA/MMAI/models/lab-upstream-'+('defender' if role=='attacker' else 'attacker')+'.onnx' if opponent=='MMAI_MODEL' else None,
            seed=(2026105800+phase*1000+r['slot'] if phase==13 else r['seed']),feature_version='upstream-graph-v15',step_cost=0.,family=r['family'],TRAIN_scenario_index=r['scenario_index'],
            worker_root=f'/root/heroes3-ai-lab/workers/continuation-{run}/{phase}-{r["slot"]}'))
    return out
def resource_gate():
    m={k:int(v.strip().split()[0]) for k,v in (line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines())};disk=shutil.disk_usage('/root/heroes3-ai-lab')
    assert m['MemAvailable']>4*1024*1024 and m['SwapTotal']-m['SwapFree']<256*1024,'Insufficient memory reserve before 16-worker phase'
    assert disk.free>10*1024**3,'Less than 10GiB disk reserve before phase'
    return dict(available_mib=m['MemAvailable']/1024,swap_used_mib=(m['SwapTotal']-m['SwapFree'])/1024,disk_free_gib=disk.free/1024**3)
def close_evidence(phase,live_steps,configs,reason):
    assert len(live_steps)==len(configs)==WORKERS
    return dict(phase=phase,reason=reason,terminated=False,truncated=False,reward_assigned=False,
        unfinished_fragments=[dict(slot=i,owned_steps=n,family=configs[i]['family'],scenario_index=configs[i]['TRAIN_scenario_index'],role=configs[i]['role'],opponent=configs[i]['opponent']) for i,n in enumerate(live_steps) if n>0],
        zero_step_post_reset_or_unacted_battles=sum(n==0 for n in live_steps),
        meaning='Close of native environments, not extra sampled transitions or outcomes; previous rollout returns already used valid bootstrap.')
