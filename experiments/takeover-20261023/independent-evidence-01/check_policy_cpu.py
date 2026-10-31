"""Independent prelaunch CPU checks. No CUDA calls, native, optimizer step, or file mutation outside review."""
import argparse,contextlib,copy,hashlib,importlib.util,json,random,sys
from pathlib import Path
ROOT=Path('/mnt/g/Heroes3-AI-Lab');BASE=ROOT/'experiments/strategic-learned-recruitment-policy-v2';RUN=ROOT/'experiments/strategic-learned-recruitment-run-v1';OUT=Path(__file__).parent
sys.path.insert(0,str(BASE));sys.path.insert(1,str(RUN))
import torch
torch.set_num_threads(1)
import model_io,qualification
from episode_balanced_ppo import prepare_batch,PROTOCOL
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
binding=qualification.require_qualification();catalog=qualification.qualified_catalog();assert len(catalog['ids'])==150
initial=BASE/'initialization-01/recruitment-initialization.pt';model,initial_bundle,initialsha=model_io.load_model(initial,'cpu')
assert initialsha=='b9ede0d158d113eff42d58cb8a844277b42e8a0820122d985299dfcf9cdb7b79'
assert initial_bundle['lineage']['parent_checkpoint_sha256']=='83319be8bde5d94eea839b1a889821449a7c1492c65da7ca6cde2deb63aab25a'
parentpath=ROOT/'experiments/strategic-learned-free-transfer-policy-v1/initialization-01/free-transfer-initialization.pt'
spec=importlib.util.spec_from_file_location('_independent_parent_io',parentpath.parent.parent/'model_io.py');oldio=importlib.util.module_from_spec(spec);spec.loader.exec_module(oldio)
parent,pbundle,psha=oldio.load_model(parentpath,'cpu');assert psha==initial_bundle['lineage']['parent_checkpoint_sha256']
for key,value in parent.state_dict().items():assert torch.equal(value,model.state_dict()[key]),key
assert not bool(model.recruit_actor.weight.ne(0).any()) and not bool(model.recruit_critic.weight.ne(0).any()) and float(model.actor.recruit_bias.detach())==-4
raw=Path('/root/heroes3-ai-lab/evaluations/strategic-learned-recruitment-mechanism-20261023-01/agent')
requests=[json.loads(p.read_text()) for p in sorted(raw.glob('request-*.json'))];assert len(requests)==17
replayed=[]
for q in requests:
 model_io.architecture.encoder.validate(q)
 batch=model_io.architecture.encoder.collate([q],'cpu')
 with torch.no_grad():
  l,v=model(**batch);l2,v2=model(**batch)
 assert torch.equal(l,l2) and torch.equal(v,v2) and torch.isfinite(l).all() and torch.isfinite(v).all()
 # Project actual same request into original action space and verify exact migration.
 q0=model_io.architecture.encoder.project(q);q0.pop('creature_catalog_sha256',None)
 qn=copy.deepcopy(q);qn['candidates']=[c for c in q['candidates'] if c['op']!='recruit']
 with torch.no_grad():
  oldlog,oldvalue=parent(**oldio.architecture.encoder.collate([q0],'cpu'))
  newlog,newvalue=model(**model_io.architecture.encoder.collate([qn],'cpu'))
 assert torch.equal(oldlog,newlog) and torch.equal(oldvalue,newvalue)
 replayed.append(dict(request_id=q['request_id'],recruit_candidates=sum(c['op']=='recruit' for c in q['candidates']),argmax=int(l.argmax()),legacy_logits_and_value_exact=True))
protocol=dict(catalog_sha256=catalog['sha256'],schema='strategic-learned-recruitment-training-v1',action_schema='strategy-candidates-v6',economy_epoch='learned-economy-build-recruit-v1',contract_sha256=model_io.CONTRACT_SHA256,flow_contract_sha256=model_io.FLOW_CONTRACT_SHA256,architecture_version=model_io.architecture.ARCHITECTURE_VERSION,threat_replan='off',native_flow_epoch='learned-economy-build-recruit-v1')
optimizer=torch.optim.Adam(model.parameters(),lr=3e-4);assert not optimizer.state
bundle=model_io.make_bundle(model,optimizer,training_updates=0,complete=True,protocol=protocol,parent_sha=initialsha,lineage={'test_only':True},collection_states={},purpose='cpu_codec_test',progress={})
destination=OUT/'independent-policy-cpu-codec.pt';model_io.atomic_save(bundle,destination,allow_test=True)
loaded,h=model_io.read(destination,allow_test=True);assert model_io.tensor_sha(loaded['state_dict'])==model_io.tensor_sha(model.state_dict())
def fingerprint():return (model_io.tensor_sha(model.state_dict()),model_io.digest_json(model_io.cpu_tree(optimizer.state_dict())),torch.get_rng_state().clone(),random.getstate())
checks=[]
def rejected_without_pollution(name,mutate):
 bad=copy.deepcopy(bundle);mutate(bad);before=fingerprint()
 try:model_io.restore_training(bad,model,optimizer,protocol_sha=model_io.digest_json(protocol),device='cpu',allow_test=True)
 except Exception as error:
  after=fingerprint();assert before[0:2]==after[0:2] and torch.equal(before[2],after[2]) and before[3]==after[3],('state polluted',name)
  checks.append(dict(name=name,rejected_without_pollution=True,error=type(error).__name__));return
 raise AssertionError(('bad state accepted',name))
rejected_without_pollution('invalid_python_rng',lambda b:b['rng'].__setitem__('python',('bad',)))
rejected_without_pollution('invalid_CPU_rng_length',lambda b:b['rng'].__setitem__('torch',torch.zeros(2,dtype=torch.uint8)))
rejected_without_pollution('Adam_counter_mismatch',lambda b:b.__setitem__('optimizer_steps_total',1))
rejected_without_pollution('parameter_order',lambda b:b['parameter_groups'][0].reverse())
rejected_without_pollution('Adam_learning_rate',lambda b:b['optimizer']['param_groups'][0].__setitem__('lr',.1))
rejected_without_pollution('partial_update',lambda b:b.__setitem__('complete_update_boundary',False))
def bad_moment_shape(b):
 identity=b['optimizer']['param_groups'][0]['params'][0]
 b['optimizer']['state'][identity]=dict(step=torch.tensor(1.),exp_avg=torch.zeros(1),exp_avg_sq=torch.zeros(1))
 b['optimizer_steps_total']=1
rejected_without_pollution('synthetic_bad_moment_shape',bad_moment_shape)
def bad_model_shape(b):
 key=next(iter(b['state_dict']));b['state_dict'][key]=torch.zeros(1,2,3);b['policy_tensor_sha256']=model_io.tensor_sha(b['state_dict'])
rejected_without_pollution('wrong_model_shape',bad_model_shape)
prelaunch=[]
class StoppedBeforeResources(Exception):pass
@contextlib.contextmanager
def blocked_resources():
 raise StoppedBeforeResources('independent CPU preparation stops before resource acquisition/native/GPU')
 yield
for module_name,mapname,seed in [('collect_episode_v5','takeover-v2-train-01-mines',2026103900),('collect_cpu','takeover-v2-dev-01-river',2026104000)]:
 spec=importlib.util.spec_from_file_location('_independent_prelaunch_'+module_name,RUN/(module_name+'.py'));module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 module.owned_resources=blocked_resources
 number=1
 while (OUT/(module_name+f'-cpu-prelaunch-{number:02d}')).exists():number+=1
 work=OUT/(module_name+f'-cpu-prelaunch-{number:02d}')
 args=argparse.Namespace(load_save=None,capsule=Path(binding['capsule_directory']),checkpoint=initial,out=work,map=mapname,seed=seed,player=0,opponent='EmptyAI',logical_update=0,seconds=120)
 try:module.run(args)
 except StoppedBeforeResources:
  prepared=json.loads((work/'PLAN.json').read_text());assert prepared['action_schema']=='strategy-candidates-v6' and prepared['checkpoint']==str(initial)
  prelaunch.append(dict(entrypoint=module_name,prepared_input_hashes=len(prepared['hashes']),stopped_before_resources=True,native_runs=0,GPU_calls=0))
 else:raise AssertionError('prelaunch escaped resource guard')
result=dict(passed=True,scope='independent CPU qualification/migration/actual17-request forward replay and codec negatives only',native_runs=0,GPU_calls=0,optimizer_steps=0,catalog_species=len(catalog['ids']),initialization_sha256=initialsha,parent_tensors_exact=True,actual_native_requests_replayed=len(replayed),legacy_projection_exact=True,requests=replayed,resume_negative_cases=checks,prelaunch=prelaunch,source_sha256={str(p):sha(p) for p in sorted(list(BASE.glob('*.py'))+list(RUN.glob('*.py')))},CPU_codec_file=str(destination),CPU_codec_never_training=True)
(OUT/'POLICY_CPU_AUDIT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['requests','source_sha256']},indent=2))
