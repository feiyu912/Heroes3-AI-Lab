"""CPU inference on immutable admitted TRAIN requests and DEV q4. Zero optimization/teacher labels."""
import collections,hashlib,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;RUN=HERE.parent
sys.path.insert(0,str(RUN));import pipeline_common as common
sys.path.insert(0,str(common.BASE));import encoder
from model_io import load_model
import torch
torch.set_num_threads(1)
TRAIN=common.LAB/'evaluations/strategic-learned-free-transfer-train-01'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def rows(p):return [json.loads(s) for s in p.read_text().splitlines() if s]
def category(c):
 if c['op']!='move':return c['op']
 return 'own_town' if c['kind']==4 else ('mine' if c['kind']==2 else 'other_move')
KEYS=['own_town','mine','other_move','end_turn','build']
def evaluate(model,q):
 batch=encoder.collate([q],'cpu')
 with torch.no_grad():logits,value=model(**batch);prob=logits[0].softmax(-1)
 n=len(q['candidates']);return logits[0,:n],prob[:n],batch
def main():
 paths={'initial':common.DEFAULT_INITIAL,'updated':TRAIN/'update-01/update-1.pt'}
 models={k:load_model(p,'cpu')[0] for k,p in paths.items()};observations=[];bound=[]
 for cell in range(8):
  folder=TRAIN/f'cell-{cell:02d}/admitted';audit=read(folder/'AUDIT.json');assert audit['passed']
  assert all(sha(folder/p)==h for p,h in audit['output_sha256'].items())
  samples=rows(folder/'samples.jsonl');episode=read(folder/'episode.json');assert len(samples)==episode['decisions']
  for sample in samples:
   q=sample['request'];types=[category(c) for c in q['candidates']];both='own_town' in types and 'mine' in types
   result={}
   for name,model in models.items():
    logits,prob,batch=evaluate(model,q);ix=int(logits.argmax())
    result[name]=dict(argmax=types[ix],mass={k:float(prob[torch.tensor([t==k for t in types],dtype=torch.bool)].sum()) for k in KEYS})
   observations.append(dict(cell=cell,opponent=episode['job']['opponent'],request_id=q['request_id'],day=q['day'],both_town_mine=both,values=result))
  bound.append(dict(cell=cell,samples_sha256=sha(folder/'samples.jsonl'),episode_sha256=sha(folder/'episode.json')))
 assert len(observations)==2089
 groups={}
 for opponent in ['EmptyAI','Nullkiller2']:
  for subset in ['all','both_town_mine']:
   rs=[r for r in observations if r['opponent']==opponent and (subset=='all' or r['both_town_mine'])];n=len(rs)
   data=dict(rows=n,models={},transitions=dict(collections.Counter(r['values']['initial']['argmax']+'->'+r['values']['updated']['argmax'] for r in rs)))
   for name in models:
    data['models'][name]=dict(argmax_counts=dict(collections.Counter(r['values'][name]['argmax'] for r in rs)),mean_probability_mass={k:sum(r['values'][name]['mass'][k] for r in rs)/n if n else None for k in KEYS},mean_town_share_within_town_plus_mine=sum(r['values'][name]['mass']['own_town']/max(1e-30,r['values'][name]['mass']['own_town']+r['values'][name]['mass']['mine']) for r in rs)/n if n else None)
   groups[opponent+'/'+subset]=data
 pair=read(HERE/'PAIR06_EVIDENCE.json');q=pair['first_different_action_on_identical_request']['request'];detail=[];qscores={name:evaluate(model,q) for name,model in models.items()}
 for i,candidate in enumerate(q['candidates']):
  row=dict(index=i,candidate=candidate,models={})
  for name,model in models.items():
   logits,prob,batch=qscores[name];feature=float(batch['candidates'][0,i,13]);pureprior=float(model.prior_scale)*feature if candidate['op']=='move' else 0.
   row['models'][name]=dict(prior_feature=feature,prior_scale=float(model.prior_scale),prior_logit=pureprior,total_logit=float(logits[i]),probability=float(prob[i]),argmax=int(logits.argmax())==i)
  detail.append(row)
 report=dict(passed=True,train_rows=2089,train_source_bindings=bound,model_sha256={k:sha(p) for k,p in paths.items()},groups=groups,pair06_q4=dict(request=q,candidate_scores=detail),per_row_values=observations,limitation='CPU counterfactual policy inference on original admitted observations, not new on-policy/native rollouts or causal proof. No DEV observation is a teacher label.',new_optimizer_steps=0,new_gpu_runs=0,new_native_runs=0)
 (HERE/'PROBABILITY_COMPARISON.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(dict(train_rows=2089,groups=groups,q4_selected=[x for x in detail if any(v['argmax'] for v in x['models'].values())]),indent=2))
if __name__=='__main__':main()
