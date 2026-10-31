"""Actual control60 CPU restore and synthetic math contracts; no native/GPU."""
import importlib.util,json,random,sys
from pathlib import Path
import numpy as np
import torch
from credit_extension import PREFIX,DRAIN,WORKERS,target,gae,Budget
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent.parent;sys.path[:0]=[str(ROOT/'research')]
source=ROOT/'experiments/battle-training-continuation-20261020/restore_learner.py';s=importlib.util.spec_from_file_location('_approved_restore',source);restore=importlib.util.module_from_spec(s);s.loader.exec_module(restore)
def main():
    torch.set_num_threads(1);out=HERE/'cpu-01';out.mkdir(exist_ok=False)
    cp=ROOT/'experiments/battle-training-continuation-20261020/monitor-independent-01/user-pause-01/control-update-60.pt';expected='443863dd26ea0daaed17cd01ab3dd44a6a16544efac73c96a89839f5b72c0e20'
    model,opt,b,spec=restore.prepare(cp,expected);counter=restore.install_counter(opt);proof=restore.restore_CPU(b,spec,model,opt,counter);proof.pop('CUDA_rng_payload')
    assert (b['completed_updates'],b['environment_steps'],counter['steps'])==(60,30720,7680)
    assert [g['lr'] for g in opt.param_groups]==[1e-5,1e-6]
    assert restore.digest(model.state_dict())==restore.digest(restore.weight_state(b)) and restore.digest(opt.state_dict())==restore.digest(b['optimizer_state_dict'])
    tests=[]
    def empty(n):return dict(reward=np.zeros((n,WORKERS)),value=np.zeros((n,WORKERS)),next_value=np.zeros((n,WORKERS)),terminal=np.zeros((n,WORKERS),bool),truncated=np.zeros((n,WORKERS),bool))
    p=empty(PREFIX);q=empty(DRAIN);p['value'][:]=.2;p['next_value'][:]=.2;q['value'][:]=.2;q['next_value'][:]=.2
    # Both signs, first terminal masks post-reset rewards, cap, exact boundary.
    q['terminal'][1,0]=True;q['reward'][1,0]=1;q['reward'][2:,0]=999
    q['terminal'][2,1]=True;q['reward'][2,1]=-1
    p['terminal'][-1,2]=True;p['reward'][-1,2]=1;q['terminal'][0,2]=True;q['reward'][0,2]=-1
    q['truncated'][0,3]=True;q['terminal'][1,3]=True;q['reward'][1,3]=1
    r=target(p,q);assert list(r['eligible'][:5])==[True,True,False,False,False]
    assert r['candidate_advantage'][-1,0]>r['control_advantage'][-1,0] and r['candidate_advantage'][-1,1]<r['control_advantage'][-1,1]
    q2={k:v.copy() for k,v in q.items()};q2['reward'][2:,0]=-888;r2=target(p,q2);assert np.array_equal(r['candidate_advantage'][:,0],r2['candidate_advantage'][:,0])
    assert np.array_equal(r['candidate_advantage'][:,2:],r['control_advantage'][:,2:])
    tests.extend(['terminal_win_and_loss_both_propagate','post_terminal_reset_rewards_do_not_leak','prefix_terminal_unchanged','nonterminal_truncation_original_bootstrap','cap_original_bootstrap','exact_prefix512_suffix0_loss_rows'])
    assert r['prefix_loss_rows']==512 and r['suffix_loss_rows']==0
    # Prefix earlier terminal isolates earlier episode from suffix target.
    p2={k:v.copy() for k,v in p.items()};p2['terminal'][10,0]=True;z=target(p2,q);assert np.array_equal(z['candidate_advantage'][:11,0],z['control_advantage'][:11,0]);tests.append('earlier_prefix_episode_unchanged')
    # Control remains original32-step GAE, including actual next-value at last row.
    assert np.allclose(r['control_advantage'][-1],p['reward'][-1]+p['next_value'][-1]*(~p['terminal'][-1])-p['value'][-1]);tests.append('original_last_row_next_value_bootstrap')
    from masked_ppo import gae as original_gae
    private=np.random.default_rng(2026102364);fixture=empty(PREFIX)
    for name in ['reward','value','next_value']:fixture[name]=private.normal(0,.3,(PREFIX,WORKERS))
    fixture['terminal']=private.random((PREFIX,WORKERS))<.04
    actual,_=original_gae(*(fixture[k] for k in ['reward','value','next_value','terminal','truncated']),gamma=1.,lam=.95)
    reference,_=gae(*(fixture[k] for k in ['reward','value','next_value','terminal','truncated']));assert np.allclose(actual,reference,atol=1e-6,rtol=0);tests.append('control_reference_matches_original_float32_GAE')
    # Drain RNG is private; seeded consumption cannot advance learning RNG.
    before=torch.get_rng_state().clone();generator=torch.Generator().manual_seed(2026106980);torch.multinomial(torch.ones((16,7)),1,generator=generator);assert torch.equal(before,torch.get_rng_state());tests.append('drain_private_generator_preserves_learning_RNG')
    ledgers=[]
    for arm in ['control','candidate']:
        ledger=Budget()
        for phase in range(4):ledger.phase(phase,[(phase*4+i//4,['BattleAI','MMAI_MODEL'][(i//2)%2],['attacker','defender'][i%2]) for i in range(16)])
        summary=ledger.summary();assert summary['admitted']==summary['suffix_observed']==4096 and summary['native']==8192 and summary['planned_Adam_calls']==1024 and summary['global_updates']==list(range(61,69));ledgers.append(summary)
    assert ledgers[0]==ledgers[1];tests.append('equal64_per_case_role_opponent_admission_equal64_suffix_budget')
    assert counter['steps']==7680 and restore.digest(opt.state_dict())==restore.digest(b['optimizer_state_dict'])
    assert torch.equal(torch.get_rng_state(),b['torch_rng_state']) and random.getstate()==b['python_rng_state'] and restore.numpy_state_payload()==b['numpy_rng_state']
    report=dict(passed=True,actual_CPU_parent_restore=True,parent_checkpoint_sha256=expected,parent_update=60,parent_environment_steps=30720,parent_Adam_steps=7680,LR_heads_body=[1e-5,1e-6],CUDA_RNG_payload_validated_only=True,CUDA_restore_executed=False,tests=tests,budget_per_arm=ledgers[0],synthetic_arrays_are_not_native_qualification=True,new_native_games=0,GPU_operations=0,optimizer_steps=0,resource_locks_taken=False,source_sha256={str(x):restore.sha(x) for x in [Path(__file__),HERE/'credit_extension.py',source]})
    (out/'AUDIT.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
