"""Root-authorized CUDA historical-state reconstruction, reference check and MC probe."""
import os,sys,json,argparse,random,signal,subprocess
from pathlib import Path
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG',':4096:8')
import leases
LEASE_PROOF=leases.verify_pair()
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent.parent;NATIVE=HERE.parent/'battle-terminal-credit-native-20261023'
sys.path[:0]=[str(NATIVE),str(ROOT/'research'),'/root/heroes3-ai-lab/src/gym']
import numpy as np
import torch
import restore_learner as restore
import legacy_support as support
import full_graph_policy as graph
import decision_model
from masked_ppo import distribution,update
from observation_digest import update as digest_obs
SOURCE=Path('/root/heroes3-ai-lab/evaluations/battle-terminal-credit-01/candidate-micro')
PARENT=SOURCE/'update-61.pt';REFERENCE=SOURCE/'update-62.pt'
def read(p):return json.loads(Path(p).read_text())
def write(p,v):Path(p).write_text(json.dumps(v,indent=2)+'\n')
def payload(p):return torch.load(p,map_location='cpu',weights_only=False)
def rng_state():return dict(CPU=torch.get_rng_state(),CUDA=torch.cuda.get_rng_state_all(),Python=random.getstate(),NumPy=restore.numpy_state_payload())
def bundle_rng(b):return dict(CPU=b['torch_rng_state'],CUDA=b['cuda_rng_states'],Python=b['python_rng_state'],NumPy=b['numpy_rng_state'])
def obs_sha(o):h=__import__('hashlib').sha256();digest_obs(h,o);return h.hexdigest()
def resource(out,phase,start=False):
    m={k:int(v.split()[0]) for k,v in (line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines())}
    gpu=subprocess.check_output(['nvidia-smi','--query-gpu=temperature.gpu,memory.used','--format=csv,noheader,nounits'],text=True).splitlines()[0].split(',')
    row=dict(phase=phase,available_mib=m['MemAvailable']/1024,swap_mib=(m['SwapTotal']-m['SwapFree'])/1024,gpu_temperature=float(gpu[0]),gpu_memory_mib=float(gpu[1]))
    with (out/'RESOURCES.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
    assert row['available_mib']>(4096 if start else 2048) and row['swap_mib']<256 and row['gpu_temperature']<86 and row['gpu_memory_mib']<14000
def replay_history(model,bundle,spec,opt,counter,prefix,saved):
    model.load_state_dict(restore.weight_state(bundle),strict=True);counter['steps']=bundle['actual_Adam_steps'];model.zero_grad(set_to_none=True)
    proof=restore.finalize_CUDA(bundle,spec,model,opt,counter)
    model_hash=restore.digest(model.state_dict());adam_hash=restore.digest(opt.state_dict())
    assert model_hash==saved['behavior_model_digest'] and adam_hash==saved['Adam_digest']
    maximum=0.;previous=None
    for tick in range(32):
        items=prefix['journal'][tick*2:tick*2+2]
        for item in items:assert restore.sha(item['path'])==item['sha256']
        d,r=[payload(item['path']) for item in items];obs=d['obs'];responses=r['responses']
        if previous is not None:assert [obs_sha(o) for o in obs]==[obs_sha(o) for o in previous]
        assert all(obs_sha(prefix['raw']['samples'][tick*16+i])==obs_sha(o) for i,o in enumerate(obs))
        with torch.inference_mode():
            batch=graph.collate(obs,'cuda');logits,values=model(*batch)
            torch.testing.assert_close(logits.cpu(),d['logits'],atol=2e-4,rtol=0.)
            torch.testing.assert_close(values.cpu(),d['values'],atol=2e-4,rtol=0.)
            # Exact archived behavior logits reconstruct the historical sampler
            # state. Fresh NN outputs are independently checked above/below.
            dist=distribution(d['logits'].cuda(),batch[-1]);chosen=dist.sample();assert torch.equal(chosen.cpu(),d['actions'])
            old_logp=torch.tensor(prefix['raw']['old_logp'][tick*16:(tick+1)*16])
            live_logp=distribution(logits,batch[-1]).log_prob(chosen).cpu()
            maximum=max(maximum,float((live_logp-old_logp).abs().max()));torch.testing.assert_close(live_logp,old_logp,atol=2e-4,rtol=0.)
            previous=[x['features'] for x in responses];_,nv=model(*graph.collate(previous,'cuda'));nv=nv.cpu().numpy().copy()
            for i,x in enumerate(responses):
                if x['truncated'] and not x['terminated']:
                    _,v=model(*graph.collate([x['final_features']],'cuda'));nv[i]=float(v)
            np.testing.assert_allclose(nv,prefix['arrays']['next_value'][tick],atol=2e-4,rtol=0.)
    reconstructed=restore.digest(rng_state())
    assert reconstructed==saved['learning_RNG_before_suffix']==saved['learning_RNG_after_suffix'] and saved['global_RNG_unchanged']
    assert restore.digest(model.state_dict())==model_hash and restore.digest(opt.state_dict())==adam_hash
    return dict(full_CUDA_restore=proof,decisions_replayed=512,bootstrap_observations_recomputed=512,maximum_NN_oldlogp_error=maximum,all_actions_exact=True,all_four_learning_RNG_digest_exact=reconstructed,model_Adam_unchanged=True,new_native_calls=0)
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();out=a.out
    freeze=read(HERE/'SOURCE_FREEZE.json');assert all(restore.sha(p)==h for p,h in freeze['input_sha256'].items())
    resource(out,'start',True);torch.set_num_threads(2);torch.use_deterministic_algorithms(True)
    prefix=payload(SOURCE/'phase-0/admitted-1.pt');saved=payload(SOURCE/'phase-0/TARGETS.pt');targets=payload(HERE/'MC_TARGETS.pt')
    assert prefix['behavior_checkpoint_sha256']==targets['behavior_sha256']==restore.sha(PARENT)
    model,cpuopt,b,spec=restore.prepare(PARENT,restore.sha(PARENT));cpu_counter=restore.install_counter(cpuopt);proof=restore.restore_CPU(b,spec,model,cpuopt,cpu_counter);proof.pop('CUDA_rng_payload')
    assert (b['completed_updates'],b['actual_Adam_steps'],b['environment_steps'])==(61,7808,31232)
    model.cuda().eval();opt=restore.optimizer_for(model,b);counter=restore.install_counter(opt,b['actual_Adam_steps']);decision_model.collate=graph.collate
    result=dict(passed=False,new_native_games=0,reference_reproduction_Adam=0,MC_new_branch_Adam=0,model_promoted=False,final_test_touched=False,resource_lease=LEASE_PROOF,CPU_restoration=proof)
    try:
        raw=prefix['raw'];kwargs=dict(epochs=2,batch_size=8,entropy_coef=.005,target_kl=.02,recompute_atol=2e-4,recompute_rtol=0.,recompute_batch_size=16)
        replay=replay_history(model,b,spec,opt,counter,prefix,saved);write(out/'REFERENCE_REPLAY.json',replay);resource(out,'before_reference')
        refmetrics=update(model,opt,raw['samples'],raw['actions'],raw['old_logp'],prefix['arrays']['value'].reshape(-1),targets['reference_advantages'].reshape(-1),targets['reference_returns'].reshape(-1),**kwargs)
        result['reference_reproduction_Adam']=counter['steps']-7808
        reference=torch.load(REFERENCE,map_location='cpu',weights_only=True)
        exact=dict(model=restore.digest(model.state_dict())==restore.digest(restore.weight_state(reference)),Adam=restore.digest(opt.state_dict())==restore.digest(reference['optimizer_state_dict']),four_RNG=restore.digest(rng_state())==restore.digest(bundle_rng(reference)),counter=counter['steps']==reference['actual_Adam_steps']==7936)
        write(out/'REFERENCE_REPRODUCTION.json',dict(exact=exact,metrics=refmetrics,actual_Adam=result['reference_reproduction_Adam'],reference_sha256=restore.sha(REFERENCE)))
        assert all(exact.values()) and result['reference_reproduction_Adam']==128,'Reference reproduction differs; MC prohibited'
        del reference;resource(out,'reference_exact')
        replay2=replay_history(model,b,spec,opt,counter,prefix,saved);assert replay2['all_four_learning_RNG_digest_exact']==replay['all_four_learning_RNG_digest_exact'];write(out/'MC_REPLAY.json',replay2)
        metrics=update(model,opt,raw['samples'],raw['actions'],raw['old_logp'],prefix['arrays']['value'].reshape(-1),targets['mc_advantages'].reshape(-1),targets['mc_returns'].reshape(-1),**kwargs)
        actual=counter['steps']-7808;result['MC_new_branch_Adam']=actual;assert 0<actual<=128
        resource(out,'MC_complete');assert all(restore.sha(p)==h for p,h in freeze['input_sha256'].items())
        path=out/'MC-update-62.pt'
        model.save(path,finetuning_mode='last',completed_updates=62,environment_steps=31744,config=dict(mode='last',experiment='observed-terminal-MC-fragment-probe-v1'),optimizer_state_dict=opt.state_dict(),torch_rng_state=torch.get_rng_state(),cuda_rng_states=torch.cuda.get_rng_state_all(),python_rng_state=random.getstate(),numpy_rng_state=support.numpy_rng(),actual_Adam_steps=counter['steps'],complete_update_boundary=True,frozen_inputs=freeze,native_environment_restorable=False,rollout_evidence=dict(path=str(SOURCE/'phase-0/admitted-1.pt'),sha256=restore.sha(SOURCE/'phase-0/admitted-1.pt')),terminal_credit_experiment=dict(arm='mc_fragment_lambda1',phase=0,half=1,phase_complete=True,parent60_sha256=b['terminal_credit_experiment']['parent60_sha256'],parent61_sha256=restore.sha(PARENT),admitted_stage_rows=1024,suffix_stage_rows=1024,total_native_stage_rows=2048,registered_factor='MC-only-last-observed-terminal-fragments',source_targets_sha256=restore.sha(HERE/'MC_TARGETS.pt'),new_native_games=0,MC_new_Adam=actual))
        readback=support.check_readback(path,model,opt,graph,counter['steps'])
        cm,co,cb,cs=restore.prepare(path,restore.sha(path));cc=restore.install_counter(co);cpu_restore=restore.restore_CPU(cb,cs,cm,co,cc);cpu_restore.pop('CUDA_rng_payload');del cm,co
        cuda_restore=restore.finalize_CUDA(cb,cs,model,opt,counter)
        expected=(torch.rand(13),torch.rand(13,device='cuda').cpu(),[random.random() for _ in range(5)],np.random.rand(5))
        restore.restore_global_rng(cb,cs,cuda=True)
        assert torch.equal(expected[0],torch.rand(13)) and torch.equal(expected[1],torch.rand(13,device='cuda').cpu()) and expected[2]==[random.random() for _ in range(5)] and np.array_equal(expected[3],np.random.rand(5))
        restore.restore_global_rng(cb,cs,cuda=True);resource(out,'restoration_complete')
        result.update(passed=True,checkpoint=str(path),checkpoint_sha256=restore.sha(path),actual_Adam_steps=counter['steps'],completed_updates=62,reference_reproduction_exact=True,MC_metrics=metrics,checkpoint_readback=readback,complete_CPU_restore=cpu_restore,complete_CUDA_restore=cuda_restore,four_RNG_draw_recovery_exact=True,equal_optimizer_budget=actual==128,old_continuation_arm_rejected=True,ability_improvement_claim=False)
    except BaseException as error:
        result.update(error=repr(error),actual_counter=counter['steps']);raise
    finally:write(out/'RESULT.json',result)
if __name__=='__main__':main()
