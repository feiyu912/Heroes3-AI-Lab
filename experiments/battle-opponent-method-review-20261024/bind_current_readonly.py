from pathlib import Path
import json,hashlib,collections
OUT=Path('/mnt/g/Heroes3-AI-Lab/experiments/battle-opponent-method-review-20261024')
root=Path('/root/heroes3-ai-lab/evaluations');current=root/'battle-terminal-credit-recovery-01';historical=root/'battle-terminal-credit-recovery-20261023-02'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
result={'correction':'Earlier SOURCE_EVIDENCE and MiniMax input read historical recovery-20261023-02, not current recovery-01. They are distinct runs even where aggregate scores agree. Original MiniMax materials remain unchanged.','current_run':str(current),'historical_run':str(historical),'certificates':{},'identity_comparison':{},'model_files':[],'source_checks':[]}
for folder in [current,historical]:
 for name in ['PLAN.json','FREEZE.json','RESULT.json','DEV-RESULT.json','DEV-RAW-AUDIT.json','control-phase-3/phase-3/WORKERS.json','candidate-phase-3/phase-3/WORKERS.json']:
  p=folder/name
  if p.exists():result['certificates'][str(p)]={'sha256':sha(p),'data':json.loads(p.read_text())}
for name in ['PLAN.json','FREEZE.json','RESULT.json']:
 a=current/name;b=historical/name;result['identity_comparison'][name]={'current_sha256':sha(a),'historical_sha256':sha(b),'same_bytes':sha(a)==sha(b)}
f=json.loads((current/'FREEZE.json').read_text())['input_sha256']
for row in json.loads((OUT/'SOURCE_EVIDENCE.json').read_text())['source_files']:
 p=Path(row['path']);h=sha(p);expected=f.get(str(p));result['source_checks'].append({'path':str(p),'sha256':h,'current_freeze_sha256':expected,'matches':h==expected if expected else None})
for role in ['attacker','defender']:
 p=Path('/root/heroes3-ai-lab/data/vcmi/Data/MMAI/models')/('lab-upstream-'+role+'.onnx');h=sha(p);result['model_files'].append({'path':str(p),'sha256':h,'current_freeze_match':h==f.get(str(p))})
for arm in ['control','candidate']:
 p=current/arm.replace(arm,arm+'-phase-3')/'phase-3/WORKERS.json';d=json.loads(p.read_text());result[arm+'_worker_summary']={'count':len(d['worker_PIDs']),'torch_imported':d['torch_imported'],'counts':dict(collections.Counter(c['opponent']+'/'+c['role'] for c in d['configs']))}
(OUT/'CURRENT_RUN_BINDING.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps(result['identity_comparison'],indent=2));print(result['control_worker_summary']);print(result['candidate_worker_summary'])
