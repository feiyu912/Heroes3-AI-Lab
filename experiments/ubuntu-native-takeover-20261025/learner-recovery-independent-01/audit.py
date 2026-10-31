"""Independent CPU data audit; no optimizer construction, CUDA or native calls."""
import hashlib
import json
import math
import random
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[2]
TAKEOVER=HERE.parent
sys.path[:0]=[str(PROJECT/'research'),str(PROJECT/'experiments/battle-terminal-credit-native-20261023')]
import numpy as np
import torch
import full_graph_policy as graph
import restore_learner as restore
from observation_digest import update as graph_digest_update

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def read(path):return json.loads(Path(path).read_text())
def write(path,data):Path(path).write_text(json.dumps(data,indent=2)+'\n')

def direct_equal(a,b):
    assert type(a) is type(b)
    if isinstance(a,torch.Tensor):
        assert a.shape==b.shape and a.dtype==b.dtype and torch.equal(a,b)
    elif isinstance(a,np.ndarray):
        assert a.shape==b.shape and a.dtype==b.dtype and np.array_equal(a,b)
    elif isinstance(a,dict):
        assert a.keys()==b.keys()
        for key in a:direct_equal(a[key],b[key])
    elif isinstance(a,(list,tuple)):
        assert len(a)==len(b)
        for x,y in zip(a,b):direct_equal(x,y)
    else:assert a==b

def main():
    torch.set_num_threads(2)
    assert not torch.cuda.is_initialized()
    before_rng=torch.get_rng_state().clone()
    python_rng=random.getstate();numpy_rng=np.random.get_state()
    assert sha(restore.__file__)=='e06151039e1665742897e9381cab1f51b3598d51db1e2f050d4315b0de5b7df9'
    controller_path=TAKEOVER/'LEARNER_RECOVERY_CONTROLLER.json';controller=read(controller_path)
    command=controller['command']
    option=lambda key:Path(command[command.index(key)+1])
    original=option('--checkpoint');prefix_path=option('--prefix');result_dir=option('--out')
    assert sha(original)=='5cd856b3221342c283899df126f4c50116d7779b3e0ea3b8d90125e243310354'
    assert sha(prefix_path)=='fd86a735a7e8597fd3329c999169dfb538cb484743b952bbced04f39751b0d16'
    result_path=result_dir/'RESULT.json';producer=read(result_path)
    assert controller['passed'] and controller['worker_exit']==0 and controller['owned_group_drained']
    assert sha(result_path)==controller['result_sha256']
    assert sha(TAKEOVER/'run_learner_recovery.py')==controller['controller_sha256']
    assert command[1]==str(TAKEOVER/'learner-recovery-v2/qualify.py')
    source_dir=Path(command[1]).parent;source_freeze=read(source_dir/'SOURCE_FREEZE.json')
    assert sha(source_dir/'SOURCE_FREEZE.json')==producer['source_freeze_sha256']
    assert all(sha(source_dir/name)==expected for name,expected in source_freeze['files'].items())
    assert sha(source_dir/'leases.py')==sha(TAKEOVER/'leases.py')
    profile_certificate=read(option('--profile-certificate'))
    assert profile_certificate['passed'] and profile_certificate['wheel_record_audit_passed'] and profile_certificate['packages']==41
    assert Path(profile_certificate['environment_root']).resolve()==Path(sys.prefix).resolve()
    assert sha(option('--profile-certificate'))==producer['Python_profile']['certificate_sha256']
    assert sha(profile_certificate['audit_path'])==profile_certificate['audit_sha256']==producer['Python_profile']['audit_sha256']
    assert sha(profile_certificate['details_path'])==profile_certificate['details_sha256']
    roundtrip=Path(producer['roundtrip_checkpoint'])
    assert roundtrip==result_dir/'zero-update-roundtrip.pt'
    assert sha(roundtrip)==producer['roundtrip_sha256']=='939eb65da3d335a1b928ae6ddb193e68ab73df66bb4f8c6817920d096e84bdb3'
    old=torch.load(original,map_location='cpu',weights_only=True)
    new=torch.load(roundtrip,map_location='cpu',weights_only=True)
    direct_equal(old,new)
    complete_digest=restore.digest(old)
    assert restore.digest(new)==complete_digest==producer['complete_original_payload_digest']==producer['reload_complete_payload_digest']
    assert (old['completed_updates'],old['actual_Adam_steps'],old['environment_steps'])==(62,7936,31744)
    assert old['complete_update_boundary'] is True and old['native_environment_restorable'] is False
    assert old['terminal_credit_experiment']['arm']=='mc_fragment_lambda1'
    excluded={'models','optimizer_state_dict','torch_rng_state','cuda_rng_states','python_rng_state','numpy_rng_state',
              'completed_updates','actual_Adam_steps','environment_steps'}
    metadata={key:value for key,value in old.items() if key not in excluded}
    new_metadata={key:value for key,value in new.items() if key not in excluded}
    direct_equal(metadata,new_metadata)
    for source in (PROJECT/'research/full_graph_policy.py',PROJECT/'research/recovered-graph.py'):
        assert old['frozen_inputs']['input_sha256']['/mnt/g/Heroes3-AI-Lab/research/'+source.name]==sha(source)
    with torch.random.fork_rng(devices=[]):model=graph.FullGraphPair(original,'last').cpu().eval()
    named=dict(model.named_parameters())
    names=[[name for name,p in named.items() if p.requires_grad and ('policy_head__' in name or 'value_head__' in name)],
           [name for name,p in named.items() if p.requires_grad and 'policy_head__' not in name and 'value_head__' not in name]]
    groups=old['optimizer_state_dict']['param_groups'];assert len(groups)==len(names)==2
    slots=[];identities=[]
    for index,(group,group_names) in enumerate(zip(groups,names)):
        assert len(group['params'])==len(group_names)
        for identity,name in zip(group['params'],group_names):
            assert type(identity) is int and identity not in identities;identities.append(identity)
            state=old['optimizer_state_dict']['state'][identity]
            assert set(state)=={'step','exp_avg','exp_avg_sq'}
            step=float(state['step']);assert step.is_integer() and 0<step<=7936
            for key in ('exp_avg','exp_avg_sq'):
                assert state[key].shape==named[name].shape and state[key].dtype==named[name].dtype
                assert bool(torch.isfinite(state[key]).all())
            direct_equal(state,new['optimizer_state_dict']['state'][identity])
            slots.append(dict(group=index,name=name,saved_parameter_ID=identity,shape=list(named[name].shape),
                              dtype=str(named[name].dtype),per_parameter_Adam_step=int(step),
                              moments_digest=restore.digest(state)))
    assert set(identities)==set(old['optimizer_state_dict']['state'])
    model_digest=restore.digest(model.state_dict())
    assert model_digest==restore.digest(restore.weight_state(old))==producer['model_digest']
    adam_digest=restore.digest(old['optimizer_state_dict'])
    assert adam_digest==restore.digest(new['optimizer_state_dict'])==producer['named_Adam_digest']
    write(HERE/'NAMED_ADAM_BINDING.json',dict(passed=True,scope='Mapping derives from frozen FullGraphPair last-mode order; no Adam object created',slots=slots))
    rng=lambda bundle:dict(CPU=bundle['torch_rng_state'],CUDA=bundle['cuda_rng_states'],Python=bundle['python_rng_state'],NumPy=bundle['numpy_rng_state'])
    rng_digest=restore.digest(rng(old));assert rng_digest==restore.digest(rng(new))==producer['four_RNG_actual_draw_recovery']['full_rng_digest']
    assert all(x.dtype==torch.uint8 and x.ndim==1 and x.numel()>0 for x in [old['torch_rng_state']]+old['cuda_rng_states'])
    assert len(old['cuda_rng_states'])==1
    old_gen=torch.Generator(device='cpu').set_state(old['torch_rng_state']);new_gen=torch.Generator(device='cpu').set_state(new['torch_rng_state'])
    assert torch.equal(torch.rand(13,generator=old_gen),torch.rand(13,generator=new_gen))
    old_python=random.Random(1);old_python.setstate(old['python_rng_state'])
    new_python=random.Random(1);new_python.setstate(new['python_rng_state'])
    assert [old_python.random() for _ in range(5)]==[new_python.random() for _ in range(5)]
    old_numpy=np.random.RandomState(1);old_numpy.set_state(restore.numpy_state_tuple(old['numpy_rng_state']))
    new_numpy=np.random.RandomState(1);new_numpy.set_state(restore.numpy_state_tuple(new['numpy_rng_state']))
    assert np.array_equal(old_numpy.rand(5),new_numpy.rand(5))
    prefix=torch.load(prefix_path,map_location='cpu',weights_only=False);samples=prefix['raw']['samples'][:8]
    assert len(samples)==8
    graphs=[]
    for sample in samples:
        digest=hashlib.sha256();graph_digest_update(digest,sample)
        graphs.append(dict(side=int(sample['lab_side']),graph_sha256=digest.hexdigest(),legal_actions=len(sample['active_action_ids'])))
    archive_path=result_dir/'NN_COMPARISON.pt';archive=torch.load(archive_path,map_location='cpu',weights_only=True)
    assert archive['source_prefix_sha256']==sha(prefix_path)
    batch=graph.collate(samples,'cpu');mask=batch[-1]
    assert torch.equal(mask,archive['mask'])
    with torch.inference_mode():live_logits,live_values=model(*batch)
    for key in ('CPU_logits','CUDA_logits'):
        torch.testing.assert_close(live_logits,archive[key],atol=2e-4,rtol=0.)
    for key in ('CPU_values','CUDA_values'):
        torch.testing.assert_close(live_values,archive[key],atol=2e-4,rtol=0.)
    logit_error=float((archive['CPU_logits'][mask]-archive['CUDA_logits'][mask]).abs().max())
    value_error=float((archive['CPU_values']-archive['CUDA_values']).abs().max())
    assert logit_error==producer['CPU_CUDA_NN_comparison']['maximum_logit_error']
    assert value_error==producer['CPU_CUDA_NN_comparison']['maximum_value_error']
    assert logit_error<=2e-4 and value_error<=2e-4
    leases=controller['leases'];assert leases==producer['resource_lease']['entries']
    assert len(leases)==2 and len({entry['fd'] for entry in leases})==2
    assert [Path(entry['path']).name for entry in leases]==['.gpu-learner-lock','.pool-lock']
    for entry in leases:
        stat=Path(entry['path']).stat();assert (stat.st_dev,stat.st_ino)==(entry['device'],entry['inode'])
    resources=[json.loads(line) for line in (result_dir/'RESOURCES.jsonl').read_text().splitlines()]
    assert [row['phase'] for row in resources]==['before_restore','after_roundtrip']
    for index,row in enumerate(resources):
        assert row['available_mib']>(4096 if index==0 else 2048)
        assert row['swap_mib']<256 and row['gpu_temperature']<86 and row['gpu_memory_mib']<14000
    assert producer['passed'] and producer['optimizer_step_calls']==controller['optimizer_step_calls']==0
    assert producer['actual_Adam_steps']==7936
    assert restore.digest(model.state_dict())==model_digest
    assert torch.equal(before_rng,torch.get_rng_state()) and random.getstate()==python_rng
    now_numpy=np.random.get_state();assert now_numpy[0]==numpy_rng[0] and np.array_equal(now_numpy[1],numpy_rng[1]) and now_numpy[2:]==numpy_rng[2:]
    assert all(parameter.grad is None for parameter in model.parameters()) and not torch.cuda.is_initialized()
    native_path=TAKEOVER/'battle-independent-01/AUDIT.json';native=read(native_path)
    assert native['passed'] and native['games']==4 and native['decisions']==102
    bound_paths=[original,roundtrip,prefix_path,archive_path,result_path,controller_path,TAKEOVER/'run_learner_recovery.py',
                 source_dir/'SOURCE_FREEZE.json',result_dir/'RESOURCES.jsonl',option('--profile-certificate'),native_path,
                 Path(command[0]),Path(command[0]).with_name('env.sh'),Path(restore.__file__),PROJECT/'research/full_graph_policy.py',PROJECT/'research/recovered-graph.py']
    audit=dict(passed=True,scope='Independent CPU load/digest/tree/NN recomputation of completed zero-update GPU recovery; no second GPU execution.',
               source_checkpoint_sha256=sha(original),roundtrip_checkpoint_sha256=sha(roundtrip),
               full_payload_direct_tree_exact=True,complete_payload_digest=complete_digest,model_digest=model_digest,
               named_Adam_digest=adam_digest,named_Adam_slots=len(slots),metadata_digest=restore.digest(metadata),
               metadata_keys=sorted(metadata),counters=dict(completed_updates=62,actual_Adam_steps=7936,environment_steps=31744),
               four_RNG_payload_digest=rng_digest,four_RNG_payloads_exact=True,
               independently_replayed_private_RNGs=['Torch CPU 13','Python 5','NumPy 5'],
               CUDA_RNG_bytes_checked_without_GPU=True,TRAIN_graphs=graphs,
               NN=dict(CPU_recomputed_graphs=8,attacker=4,defender=4,absolute_tolerance=2e-4,relative_tolerance=0.,
                       stored_CPU_CUDA_max_logit_error=logit_error,stored_CPU_CUDA_max_value_error=value_error,
                       fresh_CPU_vs_stored_CPU_max_logit_error=float((live_logits[mask]-archive['CPU_logits'][mask]).abs().max()),
                       fresh_CPU_vs_stored_CUDA_max_logit_error=float((live_logits[mask]-archive['CUDA_logits'][mask]).abs().max())),
               historical_lease_metadata_consistent=True,current_lock_inodes_retained=True,
               source_freeze_files_checked=len(source_freeze['files']),controller_normal_exit_and_group_drained=True,
               resource_samples=resources,resources_scope='Two endpoint samples only, not a continuous peak measurement.',
               actual_GPU_execution_evidence='Frozen v2 source performs CUDA object placement, inference, synchronization, real CUDA RNG draws and reload; completed worker RESULT/controller/telemetry agree. Auditor did not initialize CUDA or repeat GPU execution.',
               lease_scope='Worker historical inherited-FD proof matches controller lease metadata and current retained inode. Dead worker FDs were not reinspected and locks were not reacquired by this auditor.',
               native_regression_reference=dict(path=str(native_path),sha256=sha(native_path),games=4,decisions=102,scope=native['scope']),
               source_files_sha256={str(path.resolve()):sha(path) for path in bound_paths},
               audit_script_sha256=sha(__file__),optimizer_objects_created=0,optimizer_steps=0,new_native_games=0,
               GPU_operations=0,CUDA_initialized=False,DEV_rows_used=0,final_test_touched=False,
               canonical_digest_scope='Checks original helper canonical value/type/key/tensor shape-dtype-content identity; serialization bytes differ and native in-flight game state is not restored.')
    write(HERE/'AUDIT.json',audit)
    print(json.dumps({key:value for key,value in audit.items() if key not in ('source_files_sha256','TRAIN_graphs','resource_samples','metadata_keys')},indent=2))

if __name__=='__main__':main()
