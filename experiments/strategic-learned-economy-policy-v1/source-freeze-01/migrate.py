"""Explicit named-column migration, not an optimizer step or native qualification."""
import argparse,hashlib,importlib.util,json
from pathlib import Path
import torch
import model_io

HERE=Path(__file__).resolve().parent
PARENT=HERE.parent/'strategic-learning-mainline-20261020/temperature-initialization-01/temperature-2-initialization.pt'
PARENT_SHA='d5908330038444107ed9ba00585fb068e453a5d1636856ba994d9aa3eb68df72'

def migrate(parent=PARENT):
    parent=Path(parent); digest=hashlib.sha256(parent.read_bytes()).hexdigest()
    if digest!=PARENT_SHA: raise ValueError('This migration is preregistered only for frozen d590 T2 initialization')
    spec=importlib.util.spec_from_file_location('_frozen_schema4_model_io',HERE.parent/'strategic-typed-training-v1/model_io.py')
    oldio=importlib.util.module_from_spec(spec);spec.loader.exec_module(oldio)
    old,source,_=oldio.load_model(parent,'cpu')
    with torch.random.fork_rng(devices=[]):
        new=model_io.architecture.PriorCandidateActorCritic(old.hidden,prior_scale=float(old.prior_scale),stop_bias=float(old.actor.stop_bias))
    src=old.state_dict();dst=new.state_dict()
    # [old state27, candidate move23, op2] -> [state35, move23,economy17,op3]
    mapping={i:i for i in range(27)}
    mapping.update({27+i:35+i for i in range(23)})
    mapping.update({50:75,51:76})
    for key,value in dst.items():
        if key in ('actor.0.weight','critic.0.weight'):
            value.zero_()
            for before,after in mapping.items():value[:,after]=src[key][:,before]
        else:value.copy_(src[key])
    new.load_state_dict(dst,strict=True)
    lineage=dict(reset_optimizer=True,reset_rng=True,discard_rollout=True,weights_only=True,new_gradient_steps=0,
        parent_checkpoint_sha256=digest,new_epoch=model_io.architecture.encoder.EPOCH,
        migration='named old state27 + move23 + move/end onehot; zero all new state/economy/build columns; all deeper weights/biases retained',
        old_to_new_first_layer_columns={str(k):v for k,v in mapping.items()},
        behavior_preservation='when build masked, original nonbuild logits/critic mathematically retained; finite CPU rounding tolerance audited',
        build_initialization='no invented movement prior, no build bias; build residual from retained shared actor; probability risk must be audited before native collection')
    bundle=dict(format=model_io.INITIAL_FORMAT,schema=new.encoder.SCHEMA if hasattr(new,'encoder') else model_io.architecture.encoder.SCHEMA,
        encoder_version=model_io.architecture.ENCODER_VERSION,state_dim=35,candidate_dim=43,hidden=new.hidden,
        prior_config=dict(prior_scale=float(new.prior_scale),prior_feature_index=13),state_dict=model_io.cpu_tree(new.state_dict()),
        lineage=lineage,contract_sha256=model_io.CONTRACT_SHA256,policy_tensor_sha256=model_io.tensor_sha(new.state_dict()))
    model_io.initialization_model(bundle)
    return old,new,bundle

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    if args.out.exists():raise FileExistsError(args.out)
    _,_,bundle=migrate();digest=model_io.save_initialization(bundle,args.out)
    print(json.dumps({'path':str(args.out),'sha256':digest,'gradient_steps':0,'native_games':0,'lineage':bundle['lineage']},indent=2))
