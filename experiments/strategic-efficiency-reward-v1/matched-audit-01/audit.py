"""Audit two actual saved CUDA branches, not a new optimizer or game."""
import hashlib,json,sys
from pathlib import Path
import torch
HERE=Path(__file__).resolve().parent;BRANCH=HERE.parent
BASE=BRANCH.parent/'strategic-typed-training-v1';sys.path.insert(0,str(BASE))
from model_io import read,tensor_sha
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def equal(a,b):
    if isinstance(a,torch.Tensor):return isinstance(b,torch.Tensor) and torch.equal(a.cpu(),b.cpu())
    if isinstance(a,dict):return isinstance(b,dict) and a.keys()==b.keys() and all(equal(a[k],b[k]) for k in a)
    if isinstance(a,(list,tuple)):return isinstance(b,type(a)) and len(a)==len(b) and all(equal(x,y) for x,y in zip(a,b))
    return a==b
def main():
    torch.set_num_threads(1)
    root=Path('/root/heroes3-ai-lab/evaluations')
    paths=[root/f'strategic-efficiency-{arm}-update-01/update-1.pt' for arm in ('control','treatment')]
    loaded=[read(p) for p in paths];a,b=[entry[0] for entry in loaded]
    target_path=root/'strategic-efficiency-targets-01/TARGETS.json';target=json.loads(target_path.read_text())
    configs=[]
    for arm,checkpoint in zip(('control','treatment'),(a,b)):
        assert checkpoint['complete_update_boundary'] and checkpoint['snapshot_device']=='cuda' and checkpoint['training_updates']==1
        assert checkpoint['parent_checkpoint_sha256']==target['parent_sha256'] and checkpoint['lineage']['explicit_optimizer_reset']
        config=json.loads(json.dumps(checkpoint['protocol']));derived=config['derived_reward'];assert derived.pop('arm')==arm
        assert derived['targets_sha256']==sha(target_path) and derived['shared_batch_sha256']==target['shared_batch_sha256']
        assert all(sha(p)==h for p,h in config['sources'].items());configs.append(config)
        progress=checkpoint['progress'];assert progress['completed'] and not progress['early_stop_kl']
        assert progress['weighting']['samples']==2111 and progress['weighting']['episodes']==8
        expected={e['episode_id']:e['targets'][arm] for e in target['episodes']}
        assert {e['episode_id']:e['reward'] for e in progress['weighting']['per_episode']}==expected
        assert all(float(v['step'])==132 for v in checkpoint['optimizer']['state'].values())
    assert configs[0]==configs[1],'More than the registered arm differs in the optimizer protocol'
    assert equal(a['rng'],b['rng']) and equal(a['collection_states'],b['collection_states'])
    assert a['parameter_groups']==b['parameter_groups'] and a['optimizer']['param_groups']==b['optimizer']['param_groups']
    assert a['optimizer_steps_total']==b['optimizer_steps_total']==132
    differences={}
    for group in ('actor','critic'):
        ds=[a['state_dict'][k].double()-b['state_dict'][k].double() for k in a['state_dict'] if k.startswith(group+'.')]
        differences[group]={'l2':sum(float(v.square().sum()) for v in ds)**.5,'max_abs':max(float(v.abs().max()) for v in ds)}
        assert differences[group]['l2']>0
    assert torch.equal(a['state_dict']['prior_scale'],b['state_dict']['prior_scale'])
    report={'passed':True,'actual_saved_branches':2,'cuda_steps_per_branch':132,'same_parent':True,'same_optimizer_config':True,
        'same_source_runtime_protocol_except_arm':True,'same_complete_shared_training_data':True,'saved_CPU_CUDA_Python_RNG_exact_between_branches':True,
        'saved_episode_sampling_states_exact_between_branches':True,'parameter_differences':differences,
        'checkpoint_sha256':dict(zip(('control','treatment'),(h for _,h in loaded))),
        'input_sha256':{str(p):sha(p) for p in (*paths,target_path,Path(__file__))},'audit_optimizer_steps':0,'new_games':0,
        'ability_improvement_claim':False,'scope':'Matched saved-state comparison. This verifies one-factor execution, not independent native strength or continuous-vs-split training equivalence.'}
    out=HERE/'AUDIT.json';assert not out.exists();out.write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if __name__=='__main__':main()
