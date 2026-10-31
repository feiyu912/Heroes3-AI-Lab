"""Distinct resumable typed-training format; historical initialization format stays strict."""
import copy,hashlib,importlib.util,io,json,os,random,tempfile
from pathlib import Path
from qualification import qualified_catalog,require_qualification
import torch
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('_typed_checkpoint_architecture',HERE/'model.py')
architecture=importlib.util.module_from_spec(spec);spec.loader.exec_module(architecture)
FORMAT='strategic-active-opponent-paired-ppo-checkpoint-v1'
INITIAL_FORMAT='strategic-learned-recruitment-prior-zero-initialization-v1'
INITIAL_KEYS={'format','schema','encoder_version','state_dim','candidate_dim','catalog_sha256','hidden','prior_config','state_dict','lineage','contract_sha256','policy_tensor_sha256'}
CONTRACT_SHA256='1f3a9d3c0777e31787df5e8cd2a2af1614d326a04f9b0f85ac0e83c3e42d15a3'
FLOW_CONTRACT_SHA256=CONTRACT_SHA256

def initialization_model(bundle,device='cpu'):
    keys={'format','schema','encoder_version','architecture_version','state_dim','candidate_dim','catalog_sha256','hidden','prior_config','state_dict','lineage','policy_tensor_sha256'}
    if (not isinstance(bundle,dict) or set(bundle)!=keys or bundle['format']!=INITIAL_FORMAT
            or bundle['schema']!=architecture.encoder.SCHEMA or bundle['encoder_version']!=architecture.ENCODER_VERSION
            or bundle['architecture_version']!=architecture.ARCHITECTURE_VERSION
            or bundle['state_dim']!=35 or bundle['candidate_dim']!=architecture.CANDIDATE_DIM+len(qualified_catalog()['ids'])):raise ValueError('Distinct same-architecture recruitment initialization required')
    if bundle['catalog_sha256']!=qualified_catalog()['sha256']:raise ValueError('Checkpoint actual catalog mismatch')
    if bundle['prior_config'].get('catalog_size')!=len(qualified_catalog()['ids']):raise ValueError('Actual vocabulary width differs')
    lineage=bundle['lineage']
    if (not all(lineage.get(k) is True for k in ('reset_optimizer','reset_rng','discard_rollout','weights_only'))
            or lineage.get('new_gradient_steps')!=0 or lineage.get('new_epoch')!='strategic-learned-recruitment-prior-zero-training-v1'
            or lineage.get('threat_replan')!='off'):raise ValueError('Explicit new recruitment epoch reset required')
    if lineage.get('parent_checkpoint_sha256')!='83319be8bde5d94eea839b1a889821449a7c1492c65da7ca6cde2deb63aab25a':raise ValueError('Unregistered migration parent')
    if lineage.get('manual_recruit_prior')!=0. or lineage.get('manual_prior_is_learning') is not False or bundle['prior_config'].get('recruit_bias')!=0.:raise ValueError('Registered manual zero prior initialization required')
    if float(bundle['state_dict']['actor.recruit_bias'])!=0. or any(bool(bundle['state_dict'][name].ne(0).any()) for name in ('recruit_actor.weight','recruit_critic.weight')):raise ValueError('Manual zero initialization must have zero new residuals')
    if tensor_sha(bundle['state_dict'])!=bundle['policy_tensor_sha256'] or any(not bool(torch.isfinite(v).all()) for v in bundle['state_dict'].values()):raise ValueError('Invalid recruitment weights')
    with torch.random.fork_rng(devices=[]):model=architecture.PriorCandidateActorCritic(bundle['hidden'],**bundle['prior_config'])
    model.load_state_dict(bundle['state_dict'],strict=True)
    if float(model.prior_scale)!=bundle['prior_config']['prior_scale'] or float(model.actor.build_bias.detach())!=bundle['prior_config']['build_bias']:raise ValueError('Recruitment prior metadata differs')
    return model.to(device).eval()

def save_initialization(bundle,path):
    initialization_model(bundle)
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix=path.name+'.',suffix='.tmp',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as stream: torch.save(bundle,stream);stream.flush();os.fsync(stream.fileno())
        os.replace(name,path)
        folder=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(folder)
        finally:os.close(folder)
    finally:
        if os.path.exists(name):os.unlink(name)
    return hashlib.sha256(path.read_bytes()).hexdigest()
KEYS={'format','schema','encoder_version','architecture_version','state_dim','candidate_dim','catalog_sha256','hidden','prior_config','state_dict','optimizer',
      'optimizer_kind','parameter_groups','optimizer_steps_total','training_updates','complete_update_boundary','protocol',
      'protocol_sha256','parent_checkpoint_sha256','lineage','rng','collection_states','snapshot_device','purpose','progress','policy_tensor_sha256'}
def digest_json(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def tensor_sha(state):
    h=hashlib.sha256()
    for name,value in sorted(state.items()):
        t=value.detach().cpu().contiguous();h.update(name.encode());h.update(str(t.dtype).encode());h.update(str(tuple(t.shape)).encode());h.update(t.numpy().tobytes())
    return h.hexdigest()
def cpu_tree(value):
    if isinstance(value,torch.Tensor):return value.detach().cpu().clone()
    if isinstance(value,dict):return {k:cpu_tree(v) for k,v in value.items()}
    if isinstance(value,list):return [cpu_tree(v) for v in value]
    if isinstance(value,tuple):return tuple(cpu_tree(v) for v in value)
    return copy.deepcopy(value)
def steps(state):
    values=[]
    for entry in state['state'].values():
        raw=float(entry['step'])
        if not __import__('math').isfinite(raw) or raw<0 or not raw.is_integer():raise ValueError('Invalid Adam step')
        values.append(int(raw))
    return max(values,default=0)
def groups(model,optimizer):
    names={id(p):n for n,p in model.named_parameters()}
    return [[names[id(p)] for p in group['params']] for group in optimizer.param_groups]
def validate(bundle,*,resume=False,allow_test=False):
    if not isinstance(bundle,dict) or set(bundle)!=KEYS or bundle['format']!=FORMAT:raise ValueError('Distinct typed-training checkpoint required')
    if bundle['catalog_sha256']!=qualified_catalog()['sha256']:raise ValueError('Checkpoint actual catalog mismatch')
    if bundle['architecture_version']!=architecture.ARCHITECTURE_VERSION:raise ValueError('Explicit exploration architecture required')
    if (bundle['schema']!=architecture.encoder.SCHEMA or bundle['encoder_version']!=architecture.ENCODER_VERSION or
        bundle['state_dim']!=architecture.STATE_DIM or bundle['candidate_dim']!=architecture.CANDIDATE_DIM+len(qualified_catalog()['ids'])):raise ValueError('Typed architecture mismatch')
    if type(bundle['complete_update_boundary']) is not bool or any(type(bundle[k]) is not int or bundle[k]<0 for k in ['optimizer_steps_total','training_updates']):raise ValueError('Malformed update boundary/count')
    if resume and not bundle['complete_update_boundary']:raise ValueError('Partial update is never resumable')
    if bundle['purpose'] not in ('engineering_boundary','curriculum_training','cpu_codec_test') or (bundle['purpose']=='cpu_codec_test' and not allow_test):raise ValueError('CPU codec test cannot become a delivered training model')
    if bundle['protocol_sha256']!=digest_json(bundle['protocol']):raise ValueError('Protocol digest mismatch')
    protocol=bundle['protocol']
    if protocol.get('initial_manual_recruit_bias')!=0.:raise ValueError('Distinct manual zero prior training protocol required')
    if protocol.get('catalog_sha256')!=bundle['catalog_sha256']:raise ValueError('Training catalog binding differs')
    if (protocol.get('action_schema')!=architecture.encoder.SCHEMA or protocol.get('economy_epoch')!=architecture.encoder.EPOCH
            or protocol.get('contract_sha256')!=CONTRACT_SHA256):raise ValueError('Schema6 build protocol/contract binding required')
    if protocol.get('schema')!='strategic-active-opponent-paired-learning-v1' or protocol.get('architecture_version')!=architecture.ARCHITECTURE_VERSION:raise ValueError('Exploration training epoch required')
    if protocol.get('training_treatment') not in ('control','curriculum'):raise ValueError('Explicit registered training treatment required')
    if protocol.get('threat_replan')!='off' or protocol.get('native_flow_epoch')!='learned-economy-build-recruit-v1':raise ValueError('Qualified free-stock/off protocol required')
    if protocol.get('flow_contract_sha256')!=FLOW_CONTRACT_SHA256:raise ValueError('Exact v2 flow contract required')
    if tensor_sha(bundle['state_dict'])!=bundle['policy_tensor_sha256']:raise ValueError('Model tensor digest mismatch')
    if steps(bundle['optimizer'])!=bundle['optimizer_steps_total']:raise ValueError('Adam step metadata mismatch')
    if bundle['optimizer_kind'] not in ('Adam','AdamW') or bundle['snapshot_device'] not in ('cpu','cuda'):raise ValueError('Unsupported optimizer/device')
    if any(not isinstance(v,torch.Tensor) or not bool(torch.isfinite(v).all()) for v in bundle['state_dict'].values()):raise ValueError('Nonfinite model state')
    # Validation must not advance live CPU RNG while saving a checkpoint.
    with torch.random.fork_rng(devices=[]):
        probe=architecture.PriorCandidateActorCritic(bundle['hidden'],**bundle['prior_config'])
        probe.load_state_dict(bundle['state_dict'],strict=True)
    if float(probe.prior_scale)!=bundle['prior_config']['prior_scale']:raise ValueError('Prior metadata differs')
    if probe.catalog_size!=len(qualified_catalog()['ids']) or float(probe.actor.recruit_bias.detach())!=bundle['prior_config'].get('recruit_bias'):raise ValueError('Recruit vocabulary/prior metadata differs')
    if float(probe.actor.build_bias.detach())!=bundle['prior_config'].get('build_bias'):raise ValueError('Build offset metadata differs')
    shapes={n:tuple(p.shape) for n,p in probe.named_parameters()}
    names=[n for group in bundle['parameter_groups'] for n in group]
    if len(names)!=len(set(names)) or set(names)!=set(shapes):raise ValueError('Optimizer parameter binding differs')
    if len(bundle['parameter_groups'])!=len(bundle['optimizer']['param_groups']):raise ValueError('Optimizer group mismatch')
    identities=[identity for group in bundle['optimizer']['param_groups'] for identity in group['params']]
    if any(type(identity) is not int for identity in identities) or len(identities)!=len(set(identities)):raise ValueError('Optimizer parameter IDs must be globally unique')
    if not set(bundle['optimizer']['state']).issubset(set(identities)):raise ValueError('Unbound optimizer state ID')
    for named,group in zip(bundle['parameter_groups'],bundle['optimizer']['param_groups']):
        if len(named)!=len(group['params']):raise ValueError('Optimizer group length mismatch')
        for name,identity in zip(named,group['params']):
            entry=bundle['optimizer']['state'].get(identity)
            if entry is None:continue
            for field in ('exp_avg','exp_avg_sq'):
                v=entry[field]
                if tuple(v.shape)!=shapes[name] or not bool(torch.isfinite(v).all()):raise ValueError('Invalid Adam moment '+name)
    if set(bundle['rng'])!={'torch','python','cuda'}:raise ValueError('Exact RNG snapshot required')
    if not isinstance(bundle['rng']['torch'],torch.Tensor) or bundle['rng']['torch'].dtype!=torch.uint8:raise ValueError('CPU RNG missing')
    try:
        torch.Generator(device='cpu').set_state(bundle['rng']['torch'].cpu())
        random.Random().setstate(bundle['rng']['python'])
    except Exception as error:raise ValueError('Malformed CPU/Python RNG snapshot') from error
    if not isinstance(bundle['rng']['cuda'],list) or any(not isinstance(t,torch.Tensor) or t.dtype!=torch.uint8 or t.ndim!=1 for t in bundle['rng']['cuda']):raise ValueError('Malformed CUDA RNG snapshot')
    if bundle['snapshot_device']=='cuda' and not bundle['rng']['cuda']:raise ValueError('Actual CUDA RNG missing')
    for group in bundle['optimizer']['param_groups']:
        for field in ('lr','eps','weight_decay'):
            value=group[field]
            if isinstance(value,bool) or not isinstance(value,(int,float)) or not __import__('math').isfinite(value) or value<0:raise ValueError('Invalid Adam hyperparameter '+field)
        if len(group['betas'])!=2 or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not 0<=v<1 for v in group['betas']):raise ValueError('Invalid Adam betas')
        if group['lr']!=protocol.get('learning_rate',3e-4):raise ValueError('Adam LR differs from frozen protocol')
    return bundle
def make_bundle(model,optimizer,*,training_updates,complete,protocol,parent_sha,lineage,collection_states,purpose,progress):
    device=next(model.parameters()).device.type
    state=cpu_tree(model.state_dict());opt=cpu_tree(optimizer.state_dict())
    bundle=dict(format=FORMAT,schema=architecture.encoder.SCHEMA,encoder_version=architecture.ENCODER_VERSION,architecture_version=architecture.ARCHITECTURE_VERSION,
        state_dim=architecture.STATE_DIM,candidate_dim=model.candidate_dim,catalog_sha256=qualified_catalog()['sha256'],hidden=model.hidden,
        prior_config=dict(prior_scale=float(model.prior_scale.detach().cpu()),prior_feature_index=13,build_bias=float(model.actor.build_bias.detach().cpu()),recruit_bias=float(model.actor.recruit_bias.detach().cpu()),catalog_size=model.catalog_size),state_dict=state,
        optimizer=opt,optimizer_kind=type(optimizer).__name__,parameter_groups=groups(model,optimizer),optimizer_steps_total=steps(opt),
        training_updates=training_updates,complete_update_boundary=complete,protocol=protocol,protocol_sha256=digest_json(protocol),
        parent_checkpoint_sha256=parent_sha,lineage=lineage,rng=dict(torch=torch.get_rng_state().clone(),
            cuda=[t.cpu().clone() for t in torch.cuda.get_rng_state_all()] if device=='cuda' else [],python=random.getstate()),
        collection_states=cpu_tree(collection_states),snapshot_device=device,purpose=purpose,progress=cpu_tree(progress),policy_tensor_sha256=tensor_sha(state))
    validate(bundle,allow_test=purpose=='cpu_codec_test');return bundle
def atomic_save(bundle,path,*,allow_test=False,fail_before_replace=False):
    validate(bundle,allow_test=allow_test);path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix=path.name+'.',suffix='.tmp',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as stream:torch.save(bundle,stream);stream.flush();os.fsync(stream.fileno())
        if fail_before_replace:raise RuntimeError('Explicit checkpoint pre-rename fault injection')
        os.replace(name,path)
        folder=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(folder)
        finally:os.close(folder)
    finally:
        if os.path.exists(name):os.unlink(name)
    return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path,*,allow_test=False,require_complete=True):
    raw=Path(path).read_bytes();bundle=torch.load(io.BytesIO(raw),map_location='cpu',weights_only=True)
    validate(bundle,resume=require_complete,allow_test=allow_test)
    return bundle,hashlib.sha256(raw).hexdigest()
def load_model(path,device='cpu',*,allow_test=False):
    raw=Path(path).read_bytes();bundle=torch.load(io.BytesIO(raw),map_location='cpu',weights_only=True)
    digest=hashlib.sha256(raw).hexdigest()
    if bundle.get('format')==INITIAL_FORMAT:return initialization_model(bundle,device),bundle,digest
    validate(bundle,resume=True,allow_test=allow_test)
    with torch.random.fork_rng(devices=[]):model=architecture.PriorCandidateActorCritic(bundle['hidden'],**bundle['prior_config'])
    model.load_state_dict(bundle['state_dict'],strict=True);return model.to(device).eval(),bundle,digest
def restore_training(bundle,model,optimizer,*,protocol_sha,device='cpu',allow_test=False):
    validate(bundle,resume=True,allow_test=allow_test)
    if bundle['protocol_sha256']!=protocol_sha:raise ValueError('Resume protocol/source/runtime changed')
    if device=='cuda' and (bundle['snapshot_device']!='cuda' or not bundle['rng']['cuda']):raise ValueError('CPU checkpoint cannot claim CUDA RNG recovery')
    if groups(model,optimizer)!=bundle['parameter_groups'] or type(optimizer).__name__!=bundle['optimizer_kind']:raise ValueError('Optimizer binding changed')
    # Validate on scratch objects before touching any caller-owned live state.
    for live,saved in zip(optimizer.state_dict()['param_groups'],bundle['optimizer']['param_groups']):
        if {k:v for k,v in live.items() if k!='params'}!={k:v for k,v in saved.items() if k!='params'}:raise ValueError('Optimizer hyperparameters changed')
    with torch.random.fork_rng(devices=[]):probe=architecture.PriorCandidateActorCritic(bundle['hidden'],**bundle['prior_config'])
    probe.load_state_dict(bundle['state_dict'],strict=True)
    parameters=dict(probe.named_parameters())
    scratch_groups=[dict(**{k:v for k,v in saved.items() if k!='params'},params=[parameters[name] for name in names])
        for saved,names in zip(bundle['optimizer']['param_groups'],bundle['parameter_groups'])]
    scratch=type(optimizer)(scratch_groups,lr=bundle['optimizer']['param_groups'][0]['lr'])
    scratch.load_state_dict(bundle['optimizer'])
    if device=='cuda':
        if len(bundle['rng']['cuda'])!=torch.cuda.device_count():raise ValueError('CUDA RNG device count changed')
        for index,state in enumerate(bundle['rng']['cuda']):
            try:torch.Generator(device=f'cuda:{index}').set_state(state.cpu())
            except Exception as error:raise ValueError('Malformed CUDA RNG state') from error
    model.load_state_dict(bundle['state_dict'],strict=True);optimizer.load_state_dict(bundle['optimizer'])
    torch.set_rng_state(bundle['rng']['torch'].cpu());random.setstate(bundle['rng']['python'])
    if device=='cuda':torch.cuda.set_rng_state_all([t.cpu() for t in bundle['rng']['cuda']])
    return bundle['training_updates']




