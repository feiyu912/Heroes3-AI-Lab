"""Strict new weights-only format; no old Adam/rollout/RNG resume claim."""
import hashlib,importlib.util,io,os,tempfile
from pathlib import Path
import torch
import model as architecture
FORMAT='strategic-learned-build-exploration-initialization-v1'
KEYS={'format','schema','encoder_version','architecture_version','state_dim','candidate_dim','hidden','prior_config','state_dict','lineage','policy_tensor_sha256'}
_path=Path(__file__).resolve().parent.parent/'strategic-learned-economy-policy-v1/model_io.py'
if hashlib.sha256(_path.read_bytes()).hexdigest()!='76ae0e1ae586a2a0178b5694e6b975f847305dd90663750d1bc8ea8db23037a3':raise RuntimeError('Frozen parent codec changed')
_spec=importlib.util.spec_from_file_location('_build_exploration_parent_codec',_path)
parent_io=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(parent_io)
tensor_sha=parent_io.tensor_sha

def from_bundle(bundle,device='cpu'):
    if (not isinstance(bundle,dict) or set(bundle)!=KEYS or bundle['format']!=FORMAT
            or bundle['schema']!=architecture.encoder.SCHEMA or bundle['encoder_version']!=architecture.ENCODER_VERSION
            or bundle['architecture_version']!=architecture.ARCHITECTURE_VERSION
            or bundle['state_dim']!=35 or bundle['candidate_dim']!=43):raise ValueError('New exploration weights-only format required')
    lineage=bundle['lineage']
    if (not all(lineage.get(k) is True for k in ('reset_optimizer','reset_rng','discard_rollout','weights_only'))
            or lineage.get('new_gradient_steps')!=0 or lineage.get('new_epoch')!=architecture.EPOCH):raise ValueError('Explicit exploration initialization reset required')
    if tensor_sha(bundle['state_dict'])!=bundle['policy_tensor_sha256']:raise ValueError('Policy digest differs')
    if not all(bool(torch.isfinite(v).all()) for v in bundle['state_dict'].values()):raise ValueError('Nonfinite weights')
    with torch.random.fork_rng(devices=[]):model=architecture.PriorCandidateActorCritic(bundle['hidden'],**bundle['prior_config'])
    model.load_state_dict(bundle['state_dict'],strict=True)
    if float(model.actor.build_bias.detach())!=bundle['prior_config']['build_bias'] or float(model.prior_scale)!=bundle['prior_config']['prior_scale']:raise ValueError('Offset/prior config differs')
    return model.to(device).eval()

def load_model(path,device='cpu'):
    raw=Path(path).read_bytes();bundle=torch.load(io.BytesIO(raw),map_location='cpu',weights_only=True)
    return from_bundle(bundle,device),bundle,hashlib.sha256(raw).hexdigest()

def save_initialization(bundle,path):
    from_bundle(bundle);path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():raise FileExistsError(path)
    fd,tmp=tempfile.mkstemp(prefix=path.name+'.',suffix='.tmp',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as stream:torch.save(bundle,stream);stream.flush();os.fsync(stream.fileno())
        os.replace(tmp,path)
        fd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(fd)
        finally:os.close(fd)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)
    return hashlib.sha256(path.read_bytes()).hexdigest()
