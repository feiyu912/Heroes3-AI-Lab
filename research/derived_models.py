"""Create auditable role combinations or weight interpolations, without training."""
import hashlib
import json
import os
from pathlib import Path
import torch
from lab_io import atomic_json


def checksum(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def materialize(kind,left,right,alpha=None):
    assert kind in ['roles','lerp']
    if kind=='lerp':assert 0.<alpha<1.
    torch.set_num_threads(1)
    recipe=dict(kind=kind,left=dict(path=str(left),sha256=checksum(left)),
                right=dict(path=str(right),sha256=checksum(right)),alpha=alpha)
    identity=hashlib.sha256(json.dumps(recipe,sort_keys=True).encode()).hexdigest()[:16]
    directory=Path(__file__).resolve().parents[1]/'models/derived-candidates'
    directory.mkdir(parents=True,exist_ok=True)
    checkpoint=directory/f'{kind}-{identity}.pt';manifest_path=checkpoint.with_suffix('.json')
    if checkpoint.exists() and manifest_path.exists():
        manifest=json.loads(manifest_path.read_text())
        assert manifest['recipe']==recipe and checksum(checkpoint)==manifest['sha256']
        return checkpoint,manifest_path
    a=torch.load(left,map_location='cpu',weights_only=True)
    b=torch.load(right,map_location='cpu',weights_only=True)
    models={}
    for role in ['attacker','defender']:
        first=a['models'][role];second=b['models'][role]
        assert first['metadata']==second['metadata']
        assert set(first['weights'])==set(second['weights'])
        weights={}
        for key,value in first['weights'].items():
            other=second['weights'][key]
            assert value.shape==other.shape and value.dtype==other.dtype==torch.float32
            weights[key]=(value if role=='attacker' else other).clone() if kind=='roles' else torch.lerp(value,other,alpha)
            assert torch.isfinite(weights[key]).all()
        models[role]=dict(metadata=first['metadata'],weights=weights)
    config=dict(a.get('config',{}));config.update(mode='all',seed=20261025,checkpoint=str(checkpoint),resume=False)
    payload=dict(models=models,finetuning_mode='derived',continuation_mode='all',completed_updates=0,
                 environment_steps=0,config=config,derivation=recipe,
                 source='Arithmetic combination of public-v15 PPO role weights; no optimizer updates in derivation')
    temporary=checkpoint.with_name(checkpoint.name+'.tmp-'+str(os.getpid()))
    try:
        torch.save(payload,temporary)
        with temporary.open('rb') as stream:os.fsync(stream.fileno())
        loaded=torch.load(temporary,map_location='cpu',weights_only=True)
        assert all(torch.equal(value,loaded['models'][role]['weights'][key])
                   for role in models for key,value in models[role]['weights'].items())
        os.replace(temporary,checkpoint)
    finally:
        if temporary.exists():temporary.unlink()
    atomic_json(manifest_path,dict(checkpoint=str(checkpoint),sha256=checksum(checkpoint),recipe=recipe,
        arithmetic_roundtrip_verified=True,normal_game_evaluation_required=True,
        optimizer_reset_on_continuation=True,
        explanation='Weights can be reloaded and all layers trained with a fresh optimizer. Parent checkpoints retain their own original optimizer histories; there is no fictitious combined optimizer trajectory.'))
    return checkpoint,manifest_path


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--kind',choices=['roles','lerp'],required=True)
    parser.add_argument('--left',required=True);parser.add_argument('--right',required=True)
    parser.add_argument('--alpha',type=float)
    arguments=parser.parse_args()
    paths=materialize(arguments.kind,arguments.left,arguments.right,arguments.alpha)
    print(json.dumps(dict(checkpoint=str(paths[0]),manifest=str(paths[1]))),flush=True)
