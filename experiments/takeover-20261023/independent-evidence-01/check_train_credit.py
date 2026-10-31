"""Separate standard-library implementation of sealed TRAIN PPO aggregation."""
import collections,hashlib,json,math,struct
from pathlib import Path
ROOT=Path('/mnt/g/Heroes3-AI-Lab');HERE=Path(__file__).parent
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
def load(p):return json.loads(Path(p).read_text())
def f32(x):return struct.unpack('f',struct.pack('f',x))[0]
samples=[];episodes={};bindings={}
for i in range(8):
 d=Path('/root/heroes3-ai-lab/evaluations/strategic-learned-free-transfer-train-01')/f'cell-{i:02d}'/'admitted'
 audit=load(d/'AUDIT.json');assert audit['passed'] and audit['replay_actions_logprobs_values_rng_exact']
 assert audit['pipeline_epoch']=='strategic-learned-free-transfer-training-v1'
 for name,h in audit['input_sha256'].items():assert sha(name)==h;bindings[name]=h
 for name,h in audit['output_sha256'].items():assert sha(d/name)==h;bindings[str(d/name)]=h
 e=load(d/'episode.json');assert sha(e['raw_audit_path'])==e['raw_audit_sha256'];raw=load(e['raw_audit_path']);assert raw['whole_game_valid'] and not raw['contract_errors']
 assert e['valid'] and e['native_consumption_verified'] and e['sampling_replay_exact'] and e['native']['completed'] and e['native']['inputs_unchanged']
 ss=[json.loads(line) for line in (d/'samples.jsonl').read_text().splitlines()];assert len(ss)==e['decisions']==audit['samples_admitted']
 assert all(s['episode_id']==e['episode_id'] and s['return']==e['reward'] for s in ss)
 assert e['episode_id'] not in episodes;episodes[e['episode_id']]=e;samples+=ss
N=len(samples);E=len(episodes);assert (N,E)==(2089,8)
lengths=collections.Counter(s['episode_id'] for s in samples);choices=collections.Counter(s['episode_id'] for s in samples if len(s['request']['candidates'])>1)
raw=[f32(f32(s['return'])-f32(s['old_value'])) for s in samples]
moments=[1/choices[s['episode_id']] if len(s['request']['candidates'])>1 else 0 for s in samples]
mean=math.fsum(w*a for w,a in zip(moments,raw))/math.fsum(moments)
variance=math.fsum(w*(a-mean)**2 for w,a in zip(moments,raw))/math.fsum(moments)
normalized=[f32((a-mean)/max(math.sqrt(variance),1e-6)) if w else 0 for a,w in zip(raw,moments)]
weights=[f32(N/E*w) for w in moments]
action_groups=collections.defaultdict(list);stock_groups=collections.defaultdict(list)
for i,s in enumerate(samples):
 q=s['request'];c=q['candidates'][s['action']];opp=episodes[s['episode_id']]['job']['opponent']
 kind=('own_town' if c.get('kind')==4 else 'mine' if c.get('kind')==2 else 'other_move') if c['op']=='move' else c['op']
 action_groups[(opp,kind)].append(i)
 if kind=='own_town':
  towns=[t for t in q['own_towns'] if t['position']==c['position']];assert len(towns)==1;t=towns[0]
  ratio=t['army_value']/max(1,q['own_army_value']);group='empty' if t['army_value']==0 else 'stock_at_least_half_hero' if ratio>=.5 else 'smaller_stock'
  stock_groups[(opp,group)].append(i)
def summarize(group):
 return [dict(opponent=k[0],group=k[1],rows=len(ix),positive=sum(normalized[i]>0 for i in ix),negative=sum(normalized[i]<0 for i in ix),normalized_advantage_mean=math.fsum(normalized[i] for i in ix)/len(ix),actor_mass=math.fsum(weights[i] for i in ix),weighted_normalized_advantage_sum=math.fsum(f32(weights[i]*normalized[i]) for i in ix)) for k,ix in sorted(group.items())]
credit=summarize(action_groups);strata=summarize(stock_groups)
root_credit=load(ROOT/'experiments/takeover-20261023/train-credit-01/AUDIT.json');root_strata=load(ROOT/'experiments/takeover-20261023/refill-strata-01/AUDIT.json')
comparisons=[]
for r in root_credit['groups']:
 v=next(x for x in credit if (x['opponent'],x['group'])==(r['opponent'],r['action']))
 assert v['rows']==r['rows'] and v['positive']==r['positive_normalized_rows'] and v['negative']==r['negative_normalized_rows']
 for k in ['normalized_advantage_mean','actor_mass','weighted_normalized_advantage_sum']:assert math.isclose(v[k],r[k],rel_tol=2e-6,abs_tol=1e-4),(k,v[k],r[k])
for r in root_strata['groups']:
 v=next(x for x in strata if (x['opponent'],x['group'])==(r['opponent'],r['stock']))
 assert (v['rows'],v['positive'],v['negative'])==(r['rows'],r['positive'],r['negative'])
 assert math.isclose(v['normalized_advantage_mean'],r['advantage_mean'],abs_tol=1e-6)
nk=next(x for x in strata if x['opponent']=='Nullkiller2' and x['group']=='stock_at_least_half_hero');assert nk['rows']==nk['negative']==11 and nk['positive']==0
mass=[dict(episode_id=k,opponent=episodes[k]['job']['opponent'],steps=lengths[k],free_choices=choices[k],actor_mass=math.fsum(weights[i] for i,s in enumerate(samples) if s['episode_id']==k),objective_mass_fraction=1/E if choices[k] else 0) for k in episodes]
out=dict(passed=True,scope='separate standard-library reconstruction of sealed TRAIN advantage normalization and groups; no DEV/native/GPU/NN replay',samples=N,episodes=E,source_bindings_checked=len(bindings),input_sha256=bindings,weighted_advantage_mean=mean,weighted_advantage_variance=variance,action_groups=credit,refill_strata=strata,episode_actor_mass=mass,root_reports_match=True,nk_stock_ge_half_hero_11_all_negative=True,native_runs=0,gpu_runs=0,NN_replays=0,optimizer_steps=0)
(HERE/'TRAIN_CREDIT_AUDIT.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(dict(passed=True,source_bindings=len(bindings),strata=strata,episode_actor_mass=mass),indent=2))
