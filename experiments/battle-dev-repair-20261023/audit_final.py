"""CPU audit: real saved58..60 rollouts/checkpoints and raw96-game evidence.

Legacy57/control60 are immutable audited boundaries, not silently called newly
trained here. Reuse the prior independently authored full DEV raw checker.
"""
import argparse,collections,hashlib,importlib.util,json,sys,time
from pathlib import Path
import numpy as np
import torch
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'battle-resume-20261023'))
import curriculum,restore_learner as restore,support
REPAIR=Path(__file__).resolve().parent;HERE=REPAIR.parent/'battle-resume-20261023';ROOT=HERE.parent.parent
sys.path[:0]=[str(ROOT/'research'),'/root/heroes3-ai-lab/src/gym']
import full_graph_policy as graph
from masked_ppo import gae
sha=restore.sha
def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def read(path):return json.loads(path.read_text())
def main():
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--dev-run',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    result=read(a.dev_run/'RESULT.json');assert result['passed'] and not result['control_retrained'] and len(result['DEV'])==6
    assert {(x['model'],x['opponent']) for x in result['DEV']}=={(m,o) for m in ['parent30','control','candidate'] for o in ['BattleAI','MMAI_MODEL']}
    a.out.mkdir(parents=True,exist_ok=False);torch.set_num_threads(1)
    old=load_module('independent_original_final',REPAIR/'legacy_audit.py')
    delta=load_module('independent_delta',HERE.parent/'battle-diverse-curriculum-20261020/final-independent-01/audit_final.py')
    controller=load_module('resume_controller',HERE/'run.py')
    t=read(a.run/'candidate/training.json');assert t['completed'] and t['all_workers_exit_zero']
    assert [r['update'] for r in t['records']]==[58,59,60] and [r['phase'] for r in t['records']]==[13,14,14]
    frozen=read(a.run/'candidate/FREEZE.json');assert all(sha(p)==h for p,h in frozen['input_sha256'].items())
    restored=t['restoration'];assert restored['parent_checkpoint_sha256']==restore.DEFAULT_SHA and restored['actual_Adam_counter_before_first_sampling']==7296 and restored['CUDA_restore_executed'] and all(restored['all_RNG_before_first_sampling'].values())
    assert restored==read(a.run/'candidate/training.restoration.json')
    initial=torch.load(restore.DEFAULT_CHECKPOINT,map_location='cpu',weights_only=True)['models'];previous=initial;counter=7296;episodes=wins=cuts=0;paths=set(map(Path,frozen['input_sha256']));rows=collections.Counter();checks=[];live=[0]*16
    for offset,record in enumerate(t['records']):
        cp=Path(t['checkpoint']).parent/f'update-{58+offset}.pt';b=torch.load(cp,map_location='cpu',weights_only=True);paths.add(cp)
        assert sha(cp)==record['checkpoint_sha256'] and b['completed_updates']==58+offset and b['environment_steps']==29184+512*(offset+1)
        counter+=record['actual_Adam_steps'];assert record['actual_Adam_steps']>0 and counter==b['actual_Adam_steps']==record['actual_Adam_steps_total'] and record['actual_Adam_steps_this_stage']==counter-7296
        assert b['complete_update_boundary'] and not b['native_environment_restorable'] and b['frozen_inputs']==frozen and b['config']==t['config']
        assert b['continuation_parent_sha256']==restore.DEFAULT_SHA and b['continuation_restoration']==restored and b['schedule_epoch']==curriculum.SCHEDULE_EPOCH
        assert b['resume_boundary']['discarded_native_inflight'] and b['resume_boundary']['checkpoint_update']==57
        delta.compare_delta(delta.parameter_delta(b['models'],previous),record['parameter_delta']);delta.compare_delta(delta.parameter_delta(b['models'],initial),record['delta_from_parent'])
        model=graph.FullGraphPair(str(cp),'last').cpu().eval();opt=restore.optimizer_for(model,b);opt.load_state_dict(b['optimizer_state_dict']);assert support.equal(opt.state_dict(),b['optimizer_state_dict'])
        assert all(0<int(s['step'])<=counter and torch.isfinite(s['exp_avg']).all() and torch.isfinite(s['exp_avg_sq']).all() for s in opt.state.values())
        assert all(record['checkpoint_readback'][k] for k in ['model_exact','Adam_exact','global_RNG_payload_exact']) and record['metrics']['maximum_recompute_logp_error']<=2e-4
        restore.numpy_state_tuple(b['numpy_rng_state']);assert b['torch_rng_state'].dtype==torch.uint8 and len(b['cuda_rng_states'])==1
        e=b['rollout_evidence'];assert e==record['rollout'] and sha(e['path'])==e['sha256'];paths.add(Path(e['path']));raw=torch.load(e['path'],map_location='cpu',weights_only=False)
        phase=[13,14,14][offset];expected=curriculum.configs(t['config']['scenario_file'],2026102016,phase,cp.parent.name);assert raw['configs']==expected
        assert len(raw['actions'])==len(raw['samples'])==len(raw['old_logp'])==512
        adv,ret=gae(raw['rewards'],raw['values'],raw['next_values'],raw['terminated'],raw['truncated'],gamma=1.,lam=.95);assert np.isfinite(adv).all() and np.isfinite(ret).all()
        if offset<2:live=[0]*16
        for tick in range(32):
            for slot,cfg in enumerate(expected):
                i=tick*16+slot;obs=raw['samples'][i];action=raw['actions'][i];assert 0<=action<len(obs['active_action_ids']) and obs['lab_side']==int(cfg['role']=='defender')
                rows[(phase,cfg['TRAIN_scenario_index'],cfg['role'],cfg['opponent'])]+=1;live[slot]+=1
                if raw['terminated'][tick][slot]:
                    reward=float(raw['rewards'][tick][slot])+.5*graph.potential(obs);assert min(abs(reward-1),abs(reward+1))<1e-5;episodes+=1;wins+=reward>0
                cuts+=bool(raw['truncated'][tick][slot] and not raw['terminated'][tick][slot])
                if raw['terminated'][tick][slot] or raw['truncated'][tick][slot]:live[slot]=0
        if offset in (0,2):assert curriculum.close_evidence(phase,live,expected,'phase_switch' if offset==0 else 'final_budget_stop')==t['phase_close_events'][offset//2]
        checks.append(dict(update=58+offset,checkpoint_sha256=sha(cp),rollout_sha256=e['sha256'],cumulative_Adam_steps=counter));previous=b['models']
    assert counter==7680 and t['stage_actual_Adam_steps']==384 and sum(rows.values())==1536
    assert (episodes,wins,cuts)==(t['records'][-1]['episodes'],t['records'][-1]['wins'],t['records'][-1]['truncations'])
    assert sha(controller.CONTROL)==controller.CONTROL_SHA and sha(t['checkpoint'])==result['candidate']['sha256']
    adapted=dict(result,arms=dict(control=dict(checkpoint=str(controller.CONTROL)),candidate=dict(checkpoint=t['checkpoint'])))
    dev=old.review_dev(a.dev_run,adapted,paths)
    report=dict(passed=True,checkpoint_reviews=checks,new_Adam_steps=384,cumulative_Adam_steps=7680,new_samples=1536,training_terminals=episodes,training_wins=int(wins),training_truncations=cuts,
        DEV=dev,independent_raw96games_recomputed=True,recovered_old_games=result['recovered_games'],new_native_DEV_games=result['new_native_games'],independent_full_NN_probability_replay=False,new_native_games=0,GPU_operations=0,optimizer_steps_performed=0,
        native_restart_limitation=read(a.run/'PLAN.json')['limitation'],control_retrained=False,ability_promotion=False,
        artifact_index=[dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size) for p in sorted(paths)])
    (a.out/'AUDIT.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(passed=True,DEV=dev['summaries']),indent=2))
if __name__=='__main__':main()
