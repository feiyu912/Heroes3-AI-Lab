"""CPU integration preflight. No actual CUDA/native/optimizer execution."""
import argparse,ast,copy,hashlib,json,random,sys,tempfile
from pathlib import Path
import numpy as np
import torch
HERE=Path(__file__).resolve().parent;R=HERE.parent.parent/'research';sys.path[:0]=[str(HERE),str(R)]
import curriculum,run,restore_learner as restore,support
from step_evidence import Journal
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);torch.set_num_threads(1)
    for f in HERE.glob('*.py'):ast.parse(f.read_text())
    model,opt,b,spec=restore.prepare();counter=restore.install_counter(opt);restore.restore_CPU(b,spec,model,opt,counter)
    assert (b['completed_updates'],b['environment_steps'],counter['steps'])==(30,15360,3840)
    before=restore.clone(opt.state_dict());arms={}
    for arm,lr in [('control',1e-6),('candidate',3e-6)]:
        opt.load_state_dict(restore.clone(before));opt.param_groups[1]['lr']=lr;arms[arm]=restore.clone(opt.state_dict())
    normalized=restore.clone(arms['candidate']);normalized['param_groups'][1]['lr']=1e-6;assert support.equal(normalized,arms['control'])
    args=argparse.Namespace(checkpoint=str(restore.DEFAULT_CHECKPOINT),resume=True,workers=16,updates=30,rollout=32,mode='last',opponents=['BattleAI','MMAI_MODEL'],native_opponent_device='cpu',head_learning_rate=1e-5,epochs=2,gamma=1,gae_lambda=.95,step_cost=0,shaping=.5,entropy_coef=.005,seed=2026102016,rotate_every=2,first_battle=True,no_auto_microbatch=True,microbatch=8)
    for arm,lr in [('control',1e-6),('candidate',3e-6)]:args.arm=arm;args.learning_rate=lr;support.validate_args(args)
    args.learning_rate=1e-6
    try:support.validate_args(args)
    except AssertionError:pass
    else:raise AssertionError('Wrong candidate LR accepted')
    registered=curriculum.registered(run.SCENARIOS);old=json.loads((HERE.parent/'battle-diverse-curriculum-20261020/cpu-plan-final-01/PLAN.json').read_text())['registered_curriculum']
    assert [[(r['scenario_index'],r['family'],r['role'],r['opponent']) for r in phase] for phase in registered['phases']]==[[(r['scenario_index'],r['family'],r['role'],r['opponent']) for r in phase] for phase in old['phases']]
    configs=[curriculum.configs(run.SCENARIOS,curriculum.SEED,phase,'CPU-FAKE-NOT-NATIVE') for phase in range(15)]
    assert len({(r['TRAIN_scenario_index'],r['role'],r['opponent']) for phase in configs for r in phase})==240
    assert all(r['seed']==2026103800+phase*1000+slot for phase,rows in enumerate(configs) for slot,r in enumerate(rows))
    assert [i//2 for i in range(30)]==[p for p in range(15) for _ in range(2)]
    assert [30+i+1 for i in range(30)]==list(range(31,61))
    with tempfile.TemporaryDirectory() as tmp:
        journal=Journal(Path(tmp)/'fake',dict(test_fixture=True,native_certification=False));obs=dict(active_action_ids=np.array([2,5]),nodes={'mock':np.array([1,2])})
        journal.decision(obs,torch.tensor([0.,1.]),torch.tensor(.5),5);journal.transition(obs,0,False,False,{})
        assert journal.manifest(True)['native_step_returns']==1
        journal.decision(obs,torch.tensor([0.,1.]),torch.tensor(.5),5)
        assert journal.manifest(False)['unreturned_decision']==1
        try:journal.manifest(True)
        except AssertionError:pass
        else:raise AssertionError('Unreturned native step certified')
        try:journal.decision(obs,torch.tensor([0.,1.]),torch.tensor(.5),5)
        except AssertionError:pass
        else:raise AssertionError('Concurrent pending decision accepted')
    frozen=run.inputs();assert all(restore.sha(p)==h for p,h in frozen.items())
    report=dict(passed=True,source_sha256={str(p):restore.sha(p) for p in HERE.glob('*.py')},input_count=len(frozen),parent_sha256=restore.DEFAULT_SHA,
        restored_CPU_model_Adam_counter=True,parent_updates=30,parent_environment_steps=15360,parent_actual_Adam_counter=3840,only_arm_difference_body_lr=True,
        original60_case_selection_preserved=True,new_native_seed_base=2026103800,new_schedule_epoch=curriculum.SCHEDULE_EPOCH,slots=240,global_updates=list(range(31,61)),
        fake_step_journal_checks=4,fake_fixtures_not_native=True,new_native_games=0,GPU_operations=0,optimizer_steps_performed=0,CUDA_restore_executed=False,
        limitation='CPU/source preflight only. Root must first execute actual CUDA restoration qualification, then actual two-arm training/native DEV.')
    (a.out/'CPU_PREFLIGHT.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
