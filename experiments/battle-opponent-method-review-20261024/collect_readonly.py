from pathlib import Path
import json,hashlib,collections
OUT=Path('/mnt/g/Heroes3-AI-Lab/experiments/battle-opponent-method-review-20261024')
SRC=Path('/mnt/g/Heroes3-AI-Lab');LAB=Path('/root/heroes3-ai-lab')
NATIVE=LAB/'evaluations/battle-terminal-credit-native-20261023-01'
REC=LAB/'evaluations/battle-terminal-credit-recovery-20261023-02'
FREEZE=json.loads((NATIVE/'FREEZE.json').read_text())['input_sha256']
RF=json.loads((REC/'FREEZE.json').read_text())['input_sha256']
files={
'plan':(SRC/'experiments/battle-terminal-credit-native-20261023/APPROVED_PLAN.md',[(7,15),(54,62)]),
'learner':(SRC/'experiments/battle-terminal-credit-native-20261023/learner_impl.py',[(35,42),(87,94)]),
'worker':(SRC/'experiments/battle-terminal-credit-native-20261023/recorded_vector.py',[(12,20),(27,31),(46,51)]),
'env_factory':(SRC/'research/lab-env.py',[(1,12)]),
'prepare':(SRC/'research/prepare-worker.py',[(5,18)]),
'upstream_manifest':(SRC/'research/upstream-model-manifest.json',[(1,16)]),
'vcmi_env':(LAB/'src/gym/vcmi_gym/envs/v15/vcmi_env.py',[(339,346),(357,378),(430,437)]),
'connector':(LAB/'src/gym/vcmi_gym/connectors/v15/threadconnector.h',[(170,179)]),
'onnx_factory':(LAB/'src/gym/vcmi/AI/MMAI/BAI/factory.cpp',[(39,53),(86,93),(99,106)]),
'router':(LAB/'src/gym/vcmi/AI/MMAI/BAI/router.cpp',[(48,72)]),
'model_sampler':(LAB/'src/gym/vcmi/AI/MMAI/BAI/v15/nn_model_v15.cpp',[(230,253),(633,651)]),
'controller':(SRC/'experiments/battle-terminal-credit-native-20261023/run.py',[(20,26)]),
}
manifest=[];excerpts=[]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for name,(p,ranges) in files.items():
 b=p.read_bytes();h=hashlib.sha256(b).hexdigest();a=b.decode().splitlines();row={'label':name,'path':str(p),'sha256':h,'bytes':len(b),'original_freeze_sha256':FREEZE.get(str(p)),'recovery_freeze_sha256':RF.get(str(p)),'ranges':ranges};row['original_freeze_match']=h==row['original_freeze_sha256'] if row['original_freeze_sha256'] else None;row['recovery_freeze_match']=h==row['recovery_freeze_sha256'] if row['recovery_freeze_sha256'] else None;manifest.append(row)
 text='## '+name+' '+str(p)+' SHA256='+h+'\n'+'\n'.join(f'{i}: {a[i-1]}' for lo,hi in ranges for i in range(lo,min(hi,len(a))+1))+'\n'
 excerpts.append(text)
regpath=SRC/'experiments/battle-terminal-credit-native-20261023/REGISTERED_CURRICULUM.json';reg=json.loads(regpath.read_text()); registry=[]
for phase,rows in enumerate(reg['phases']):
 registry.append({'phase':phase,'slots':len(rows),'opponent_role_counts':dict(collections.Counter(r['opponent']+'/'+r['role'] for r in rows)),'admitted_per_cell':sorted(set(r['admitted_transitions'] for r in rows)),'suffix_per_cell':sorted(set(r['suffix_native_transitions'] for r in rows))})
certs={}
for p in [NATIVE/'PLAN.json',NATIVE/'FREEZE.json',REC/'PLAN.json',REC/'FREEZE.json',REC/'DEV-RESULT.json',REC/'DEV-RAW-AUDIT.json',REC/'DEV-NN-REPLAY/RESULT.json',REC/'control-phase-3/phase-3/WORKERS.json',REC/'candidate-phase-3/phase-3/WORKERS.json']:
 if p.exists():
  h=sha(p);d=json.loads(p.read_text());certs[str(p)]={'sha256':h,'data':d}
models=[]
for role in ['attacker','defender']:
 p=LAB/f'data/vcmi/Data/MMAI/models/lab-upstream-{role}.onnx';h=sha(p);models.append({'role':role,'path':str(p),'sha256':h,'original_freeze_match':h==FREEZE.get(str(p)),'recovery_freeze_match':h==RF.get(str(p)),'bytes':p.stat().st_size})
result={'source_files':manifest,'registry':{'path':str(regpath),'sha256':sha(regpath),'original_freeze_match':sha(regpath)==FREEZE.get(str(regpath)),'phases':registry},'models':models,'certificates':certs,'scope':'read-only hash/source/certificate review; no native/GPU/compiler/import of game or torch; no finaltest read'}
(OUT/'SOURCE_EVIDENCE.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
(OUT/'SOURCE_EXCERPTS.md').write_text('\n'.join(excerpts))
print('sources',len(manifest),'excerpts_bytes',(OUT/'SOURCE_EXCERPTS.md').stat().st_size,'models',models)
print('freeze_mismatches',[(r['label'],r['original_freeze_match'],r['recovery_freeze_match']) for r in manifest if r['original_freeze_match'] is False or r['recovery_freeze_match'] is False])
print('registry',registry)
