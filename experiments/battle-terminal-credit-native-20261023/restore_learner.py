"""CPU-only, boundary-bound battle learner restoration. Does not create native environments."""
import copy,hashlib,importlib.util,io,json,math,random
from pathlib import Path
import numpy as np
import torch

ROOT=Path('/mnt/g/Heroes3-AI-Lab')
DEFAULT_CHECKPOINT=Path('/mnt/g/Heroes3-AI-Lab/experiments/battle-training-continuation-20261020/monitor-independent-01/user-pause-01/control-update-60.pt')
DEFAULT_SHA='443863dd26ea0daaed17cd01ab3dd44a6a16544efac73c96a89839f5b72c0e20'
def require(condition,message):
    if not condition:raise ValueError(message)
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def clone(value):
    if isinstance(value,torch.Tensor):return value.detach().cpu().clone()
    if isinstance(value,dict):return {k:clone(v) for k,v in value.items()}
    if isinstance(value,list):return [clone(v) for v in value]
    if isinstance(value,tuple):return tuple(clone(v) for v in value)
    return copy.deepcopy(value)
def digest(value):
    h=hashlib.sha256()
    def add(v):
        if isinstance(v,torch.Tensor):
            t=v.detach().cpu().contiguous();h.update(b'tensor');h.update(str(t.dtype).encode());h.update(str(tuple(t.shape)).encode());h.update(t.numpy().tobytes())
        elif isinstance(v,dict):
            h.update(b'dict')
            for k in sorted(v,key=lambda k:(type(k).__name__,str(k))):add(k);add(v[k])
        elif isinstance(v,(list,tuple)):
            h.update(type(v).__name__.encode());h.update(str(len(v)).encode())
            for x in v:add(x)
        elif isinstance(v,np.ndarray):
            h.update(b'numpy');h.update(str(v.dtype).encode());h.update(str(v.shape).encode());h.update(v.tobytes())
        elif type(v) in (str,int,float,bool) or v is None:
            require(not isinstance(v,float) or math.isfinite(v),'Nonfinite scalar payload')
            h.update(type(v).__name__.encode());h.update(repr(v).encode());h.update(b';')
        else:raise ValueError('Unsupported saved-state type '+type(v).__name__)
    add(value);return h.hexdigest()
def numpy_state_payload():
    n=np.random.get_state();return dict(engine=n[0],keys=n[1].tolist(),position=n[2],has_gauss=n[3],cached=n[4])
def numpy_state_tuple(p):
    require(isinstance(p,dict) and set(p)=={'engine','keys','position','has_gauss','cached'},'Malformed NumPy RNG fields')
    require(p['engine']=='MT19937' and isinstance(p['keys'],list) and len(p['keys'])==624,'Unsupported NumPy RNG engine/keys')
    require(all(type(x) is int and 0<=x<2**32 for x in p['keys']),'Invalid NumPy RNG key')
    require(type(p['position']) is int and 0<=p['position']<=624 and type(p['has_gauss']) is int and p['has_gauss'] in (0,1),'Invalid NumPy RNG cursor')
    require(isinstance(p['cached'],(int,float)) and math.isfinite(p['cached']),'Invalid NumPy cached Gaussian')
    result=(p['engine'],np.asarray(p['keys'],dtype=np.uint32),p['position'],p['has_gauss'],p['cached'])
    private=np.random.RandomState(1);private.set_state(result);return result
def weight_state(bundle):
    require(isinstance(bundle.get('models'),dict) and set(bundle['models'])=={'attacker','defender'},'Both role graphs required')
    return {'models.'+role+'.weights.'+name.replace('.','__'):value
        for role,item in bundle['models'].items() for name,value in item['weights'].items()}
def named_groups(model):
    heads=[];body=[]
    for name,p in model.named_parameters():
        if p.requires_grad:(heads if 'policy_head__' in name or 'value_head__' in name else body).append(name)
    return [heads,body] if body else [heads]
def optimizer_for(model,bundle):
    parameters=dict(model.named_parameters());names=named_groups(model);saved=bundle['optimizer_state_dict']['param_groups']
    require(len(names)==len(saved),'Optimizer group count differs')
    groups=[]
    for group_names,old in zip(names,saved):
        group={k:clone(v) for k,v in old.items() if k!='params'};group['params']=[parameters[n] for n in group_names];groups.append(group)
    return torch.optim.Adam(groups)
def live_named_groups(model,optimizer):
    names={id(p):n for n,p in model.named_parameters()}
    return [[names[id(p)] for p in g['params']] for g in optimizer.param_groups]

def prepare(checkpoint=DEFAULT_CHECKPOINT,expected_sha=DEFAULT_SHA):
    """Read an explicitly approved immutable saved boundary and derive named binding."""
    path=Path(checkpoint);raw=path.read_bytes();require(hashlib.sha256(raw).hexdigest()==expected_sha,'Approved boundary file SHA differs')
    bundle=torch.load(io.BytesIO(raw),map_location='cpu',weights_only=True)
    require(bundle.get('finetuning_mode')=='last' and bundle['config'].get('mode')=='last','Only the actual last-graph mode is supported')
    sources={}
    for p in (ROOT/'research/full_graph_policy.py',ROOT/'research/recovered-graph.py'):
        require(bundle['frozen_inputs']['input_sha256'].get(str(p))==sha(p),'Frozen graph source changed '+str(p));sources[str(p)]=sha(p)
    spec=importlib.util.spec_from_file_location('_battle_continuation_frozen_graph',ROOT/'research/full_graph_policy.py')
    graph=importlib.util.module_from_spec(spec);spec.loader.exec_module(graph)
    with torch.random.fork_rng(devices=[]):model=graph.FullGraphPair(path,'last').cpu().eval()
    optimizer=optimizer_for(model,bundle)
    names=named_groups(model);parameters=dict(model.named_parameters())
    reference=dict(checkpoint=str(path),checkpoint_sha256=expected_sha,bundle_digest=digest(bundle),
        mode='last',model_shapes={n:tuple(p.shape) for n,p in parameters.items()},model_dtypes={n:p.dtype for n,p in parameters.items()},
        trainable_names=[n for n,p in parameters.items() if p.requires_grad],named_parameter_groups=names,
        optimizer_groups=clone(bundle['optimizer_state_dict']['param_groups']),
        graph_metadata={r:clone(bundle['models'][r]['metadata']) for r in ('attacker','defender')},
        CPU_rng_bytes=bundle['torch_rng_state'].numel(),CUDA_rng_shapes=[tuple(v.shape) for v in bundle['cuda_rng_states']],source_sha256=sources)
    validate(bundle,reference)
    return model,optimizer,bundle,reference

def validate(bundle,reference):
    require(bundle.get('finetuning_mode')==reference['mode']=='last','Finetuning mode changed')
    require(bundle.get('complete_update_boundary') is True and bundle.get('native_environment_restorable') is False,'Complete learner-only boundary required')
    for key in ('completed_updates','environment_steps','actual_Adam_steps'):
        require(type(bundle.get(key)) is int and bundle[key]>=0,'Invalid saved '+key)
    states=weight_state(bundle);require(set(states)==set(reference['model_shapes']),'Architecture parameter names differ')
    for name,value in states.items():
        require(isinstance(value,torch.Tensor) and tuple(value.shape)==reference['model_shapes'][name] and value.dtype==reference['model_dtypes'][name],'Model tensor shape/dtype differs '+name)
        require(bool(torch.isfinite(value).all()),'Nonfinite model tensor '+name)
    require({r:bundle['models'][r]['metadata'] for r in ('attacker','defender')}==reference['graph_metadata'],'Role graph metadata differs')
    opt=bundle['optimizer_state_dict'];require(set(opt)=={'state','param_groups'},'Adam state structure differs')
    require(len(opt['param_groups'])==len(reference['named_parameter_groups']),'Adam group count differs')
    ids=[];steps=[]
    for index,(group,names,original) in enumerate(zip(opt['param_groups'],reference['named_parameter_groups'],reference['optimizer_groups'])):
        require(group==original,'Ordered Adam parameter IDs/hyperparameters changed in group '+str(index))
        require(len(group['params'])==len(names),'Adam named binding count differs')
        for identity,name in zip(group['params'],names):
            require(type(identity) is int and identity not in ids,'Duplicate/invalid Adam parameter ID');ids.append(identity)
            entry=opt['state'].get(identity);require(isinstance(entry,dict) and set(entry)=={'step','exp_avg','exp_avg_sq'},'Missing/unsupported actual Adam moments '+name)
            step=entry['step'];require(isinstance(step,torch.Tensor) and step.numel()==1 and bool(torch.isfinite(step).all()),'Malformed Adam step')
            number=float(step);require(number>=1 and number.is_integer() and number<=bundle['actual_Adam_steps'],'Adam step/counter mismatch');steps.append(int(number))
            for field in ('exp_avg','exp_avg_sq'):
                value=entry[field];require(isinstance(value,torch.Tensor) and tuple(value.shape)==reference['model_shapes'][name] and value.dtype==reference['model_dtypes'][name] and bool(torch.isfinite(value).all()),'Invalid '+field+' binding '+name)
    # Overall optimizer.step post-hook counts calls; conditional role graphs can
    # legitimately have fewer per-parameter steps. Never derive the call counter
    # from max(moment.step): dcaab has overall3840 vs role3833/3826.
    require(set(opt['state'])==set(ids) and max(steps)<=bundle['actual_Adam_steps'],'Actual Adam counter does not bound all named state')
    rng=bundle['torch_rng_state'];require(isinstance(rng,torch.Tensor) and rng.dtype==torch.uint8 and rng.ndim==1 and rng.numel()==reference['CPU_rng_bytes'],'Malformed CPU torch RNG')
    torch.Generator(device='cpu').set_state(rng.cpu())
    cuda=bundle['cuda_rng_states'];require(isinstance(cuda,list) and len(cuda)==len(reference['CUDA_rng_shapes']) and len(cuda)>0,'CUDA RNG payload missing')
    require(all(isinstance(v,torch.Tensor) and v.dtype==torch.uint8 and tuple(v.shape)==shape for v,shape in zip(cuda,reference['CUDA_rng_shapes'])),'CUDA RNG payload shape/dtype differs')
    private=random.Random(1)
    try:private.setstate(bundle['python_rng_state'])
    except (ValueError,TypeError) as error:raise ValueError('Malformed Python RNG') from error
    numpy_state_tuple(bundle['numpy_rng_state'])
    # Original checkpoint has no named optimizer manifest. Approved SHA plus exact
    # frozen trainer order and full canonical boundary digest bind same-shaped slots.
    require(digest(bundle)==reference['bundle_digest'],'Approved saved boundary content changed')
    return bundle

def install_counter(optimizer,start=0):
    require(type(start) is int and start>=0,'Invalid counter origin')
    counter={'steps':start}
    def increment(*unused):counter['steps']+=1
    optimizer.register_step_post_hook(increment)
    return counter

def restore_CPU(bundle,reference,model,optimizer,counter):
    """Restore saved learning state only. CUDA state is returned as validated payload."""
    validate(bundle,reference)
    require(all(p.device.type=='cpu' for p in model.parameters()),'This helper only restores actual CPU model state')
    live=dict(model.named_parameters())
    require(set(live)==set(reference['model_shapes']) and all(tuple(p.shape)==reference['model_shapes'][n] and p.dtype==reference['model_dtypes'][n] for n,p in live.items()),'Live model architecture/dtype differs')
    require(type(optimizer) is torch.optim.Adam,'Actual Adam required')
    require(live_named_groups(model,optimizer)==reference['named_parameter_groups'],'Live named Adam groups differ')
    require([n for n,p in model.named_parameters() if p.requires_grad]==reference['trainable_names'],'Live trainable mask differs')
    require(isinstance(counter,dict) and type(counter.get('steps')) is int,'Live counter missing')
    # All malformed boundary, identity, moment and RNG checks precede mutation.
    model.load_state_dict(weight_state(bundle),strict=True);optimizer.load_state_dict(clone(bundle['optimizer_state_dict']))
    torch.set_rng_state(bundle['torch_rng_state'].cpu());random.setstate(bundle['python_rng_state']);np.random.set_state(numpy_state_tuple(bundle['numpy_rng_state']))
    counter['steps']=bundle['actual_Adam_steps']
    return dict(previous_completed_updates=bundle['completed_updates'],previous_environment_steps=bundle['environment_steps'],
        actual_Adam_steps_restored=counter['steps'],CUDA_rng_payload=clone(bundle['cuda_rng_states']),CUDA_restore_executed=False,
        native_environment_restored=False,native_fresh_required=True,new_explicit_schedule_epoch_required=True,next_schedule_phase=None)

def restore_global_rng(bundle,reference,*,cuda=False):
    """Reapply boundary RNG immediately before sampling; cuda=True is root-only GPU work."""
    validate(bundle,reference)
    if cuda:
        require(torch.cuda.is_available() and torch.cuda.device_count()==len(bundle['cuda_rng_states']),'CUDA RNG device count differs')
        for index,state in enumerate(bundle['cuda_rng_states']):torch.Generator(device='cuda:'+str(index)).set_state(state.cpu())
    torch.set_rng_state(bundle['torch_rng_state'].cpu());random.setstate(bundle['python_rng_state']);np.random.set_state(numpy_state_tuple(bundle['numpy_rng_state']))
    if cuda:torch.cuda.set_rng_state_all(bundle['cuda_rng_states'])
    return dict(CUDA_restore_executed=bool(cuda),native_environment_restored=False)

def finalize_CUDA(bundle,reference,model,optimizer,counter):
    """After caller moves model to CUDA, load Adam using Torch's own casting rules.

    Do not manually move Adam scalar step tensors: noncapturable Adam preserves
    CPU step counters while exp_avg/exp_avg_sq follow CUDA parameters.
    This entry point is not executed by CPU audits.
    """
    validate(bundle,reference)
    require(all(p.device.type=='cuda' for p in model.parameters()),'Caller must construct/move the actual CUDA model first')
    require(type(optimizer) is torch.optim.Adam and live_named_groups(model,optimizer)==reference['named_parameter_groups'],'CUDA Adam named identity differs')
    require(digest(model.state_dict())==digest(weight_state(bundle)),'CUDA model does not match approved boundary')
    require(counter['steps']==bundle['actual_Adam_steps'],'Actual optimizer call counter was not restored')
    optimizer.load_state_dict(clone(bundle['optimizer_state_dict']))
    require(digest(optimizer.state_dict())==digest(bundle['optimizer_state_dict']),'CUDA Adam values differ')
    require(all(v['exp_avg'].device.type=='cuda' and v['exp_avg_sq'].device.type=='cuda' for v in optimizer.state.values()),'Adam moments not on actual CUDA parameters')
    restore_global_rng(bundle,reference,cuda=True)
    return dict(CUDA_restore_executed=True,actual_Adam_steps_restored=counter['steps'],native_environment_restored=False)
