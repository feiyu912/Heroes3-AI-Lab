"""Independent prior0 single-factor and strict-arm CPU qualification."""
import argparse,ast,contextlib,hashlib,importlib.util,json,subprocess,sys
from pathlib import Path
ROOT=Path('/mnt/g/Heroes3-AI-Lab');EXP=ROOT/'experiments';BASE=EXP/'strategic-learned-recruitment-policy-v3';RUN=EXP/'strategic-learned-recruitment-run-v2';OLD=EXP/'strategic-learned-recruitment-policy-v2';OLDRUN=EXP/'strategic-learned-recruitment-run-v1';OUT=Path(__file__).parent
sys.path.insert(0,str(BASE));sys.path.insert(1,str(RUN))
import torch
torch.set_num_threads(1)
import model_io,qualification
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text())
initial=BASE/'initialization-02/recruitment-initialization.pt';oldinitial=OLD/'initialization-01/recruitment-initialization.pt'
model,bundle,digest=model_io.load_model(initial,'cpu');assert digest=='1510149ef1c2c896e3125e6468e9e58234a8bfc9e4278ad239f9d6840e1c62a1'
assert sha(oldinitial)=='b9ede0d158d113eff42d58cb8a844277b42e8a0820122d985299dfcf9cdb7b79'
oldbundle=torch.load(oldinitial,map_location='cpu',weights_only=True)
differences=[n for n,v in bundle['state_dict'].items() if not torch.equal(v,oldbundle['state_dict'][n])]
assert differences==['actor.recruit_bias'] and float(model.actor.recruit_bias.detach())==0 and float(oldbundle['state_dict']['actor.recruit_bias'])==-4
assert bundle['catalog_sha256']==oldbundle['catalog_sha256'] and bundle['architecture_version']==oldbundle['architecture_version'] and bundle['candidate_dim']==oldbundle['candidate_dim']==227
assert bundle['lineage']['migration_seed']==oldbundle['lineage']['migration_seed']==2026103900
assert bundle['lineage']['reset_optimizer'] and bundle['lineage']['reset_rng']
def body(path,name):
 tree=ast.parse(path.read_text());return ast.dump(next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name==name),include_attributes=False)
assert body(BASE/'model.py','forward')==body(OLD/'model.py','forward')
assert sha(BASE/'encoder.py')==sha(OLD/'encoder.py')
for name in ['prepare_batch','objective_terms','ppo_update']:
 assert body(BASE/'episode_balanced_ppo.py',name)==body(OLD/'episode_balanced_ppo.py',name),name
rejections=[]
for path in [oldinitial,Path('/root/heroes3-ai-lab/evaluations/strategic-learned-recruitment-train-20261023-01/update-01/update-1.pt')]:
 try:model_io.load_model(path,'cpu')
 except Exception as error:rejections.append(dict(path=str(path),rejected=True,error=type(error).__name__))
 else:raise AssertionError(('foreign/stale checkpoint accepted',str(path)))
code="import sys;sys.path.insert(0,sys.argv[1]);from model_io import load_model;load_model(sys.argv[2],'cpu')"
proc=subprocess.run(['/root/heroes3-ai-lab/venv/bin/python','-c',code,str(OLD),str(initial)],capture_output=True,text=True);assert proc.returncode!=0 and 'ValueError' in proc.stderr
rejections.append(dict(path=str(initial),old_strict_codec_rejected=True))
agent=Path('/root/heroes3-ai-lab/evaluations/strategic-learned-recruitment-mechanism-20261023-01/agent');checked=[]
for path in sorted(agent.glob('request-*.json')):
 q=load(path);batch=model_io.architecture.encoder.collate([q],'cpu')
 with torch.no_grad():l,v=model(**batch);l2,v2=model(**batch)
 assert torch.equal(l,l2) and torch.equal(v,v2) and torch.isfinite(l).all()
 checked.append(dict(request_id=q['request_id'],argmax=int(l.argmax()),op=q['candidates'][int(l.argmax())]['op']))
assert len(checked)==17
import pipeline_common
assert sha(BASE/'initialization-01/recruitment-initialization.pt')!=pipeline_common.INITIAL_SHA==digest
oldfreeze=load(OLDRUN/'SOURCE_FREEZE.json');assert all(sha(EXP/relative.replace('\\','/'))==h for relative,h in oldfreeze['files'].items())
sourcepaths={str(p) for p in pipeline_common.source_inputs()}
assert str(OLDRUN/'SOURCE_FREEZE.json') in sourcepaths and all(str(EXP/p.replace('\\','/')) in sourcepaths for p in oldfreeze['files'])
class StopBeforeResource(Exception):pass
@contextlib.contextmanager
def blocked():raise StopBeforeResource();yield
prelaunch=[]
for entry,arm,checkpoint,mapname,seed in [('collect_episode_v5','prior-zero',initial,'takeover-v2-train-01-mines',2026103900),('collect_cpu','prior-zero',initial,'takeover-v2-dev-01-river',2026104200),('collect_cpu','minus-four-control',oldinitial,'takeover-v2-dev-01-river',2026104200)]:
 spec=importlib.util.spec_from_file_location('_independent_zero_'+entry,RUN/(entry+'.py'));module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.owned_resources=blocked
 number=1
 while (OUT/f'priorzero-{entry}-{arm}-{number:02d}').exists():number+=1
 work=OUT/f'priorzero-{entry}-{arm}-{number:02d}'
 args=argparse.Namespace(load_save=None,capsule=pipeline_common.DEFAULT_CAPSULE,checkpoint=checkpoint,out=work,map=mapname,seed=seed,player=0,opponent='EmptyAI',logical_update=0,seconds=120,policy_epoch=arm,prepare_only=False)
 try:module.run(args)
 except StopBeforeResource:pass
 else:raise AssertionError('resource stop escaped')
 p=load(work/'PLAN.json')
 if entry=='collect_episode_v5':
  previous=load(Path('/root/heroes3-ai-lab/evaluations/strategic-learned-recruitment-train-20261023-01/cell-00/native/PLAN.json'))
  assert p['sampling_seed']==previous['sampling_seed'] and p['seed']==previous['seed']
 else:
  expected=OLD/'broker.py' if arm=='minus-four-control' else BASE/'broker.py'
  assert p['broker_path']==str(expected) and p['policy_epoch']==arm
 prelaunch.append(dict(entry=entry,arm=arm,inputs=len(p['hashes']),locks_acquired=False,native_runs=0,GPU_calls=0,sampling_seed=p['sampling_seed']))
out=dict(passed=True,initializer_sha256=digest,single_tensor_difference= differences,initial_bias=0.,old_initial_bias=-4.,architecture_forward_AST_exact=True,encoder_byte_exact=True,PPO_functions_AST_exact=True,old_frozen_source_unchanged=True,old_and_new_sources_closed=True,actual_requests_forward_recomputed=len(checked),requests=checked,strict_codec_rejections=rejections,prelaunch=prelaunch,source_sha256={str(p):sha(p) for p in sorted(list(BASE.glob('*.py'))+list(RUN.glob('*.py')))},native_runs=0,GPU_calls=0,optimizer_steps=0,locks_acquired=False)
(OUT/'PRIORZERO_CPU_AUDIT.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k not in ['source_sha256','requests']},indent=2))
