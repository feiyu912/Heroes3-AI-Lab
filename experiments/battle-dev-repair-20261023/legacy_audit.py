"""CPU final audit only after both update60 and all96DEV complete. Never runs games."""
import argparse,collections,hashlib,importlib.util,json,math,sys,time
from pathlib import Path
OUT=Path(__file__).resolve().parent;HERE=OUT.parent;R=HERE.parent.parent/'research';LAB=Path('/root/heroes3-ai-lab')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def gate(run):
    d=read(run/'RESULT.json')
    assert d.get('passed') and d.get('training_completed'),'Both completed arms required'
    assert set(d['arms'])=={'control','candidate'} and len(d.get('DEV',[]))==6,'All six final DEV reports required'
    expected={(m,o) for m in ('parent30','control','candidate') for o in ('BattleAI','MMAI_MODEL')}
    assert {(r['model'],r['opponent']) for r in d['DEV']}==expected
    for arm in d['arms']:
        t=read(run/arm/'training.json');assert t['completed'] and [r['update'] for r in t['records']]==list(range(31,61))
    assert all(Path(r['report']).is_file() for r in d['DEV']);return d
def review(run,result):
    import numpy as np
    import torch
    torch.set_num_threads(1);sys.path[:0]=[str(HERE),str(R),str(LAB/'src/gym')]
    import curriculum,restore_learner as restore,support
    import full_graph_policy as graph
    from masked_ppo import gae
    parent=restore.DEFAULT_CHECKPOINT;assert sha(parent)==restore.DEFAULT_SHA
    initial=torch.load(parent,map_location='cpu',weights_only=True)['models'];frozen=read(run/'FREEZE.json');assert len(frozen['input_sha256'])>=494
    assert all(sha(p)==h for p,h in frozen['input_sha256'].items())
    basepath=HERE.parent/'battle-diverse-curriculum-20261020/final-independent-01/audit_final.py'
    spec=importlib.util.spec_from_file_location('_old_delta_reader',basepath);old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
    paths=set(map(Path,frozen['input_sha256']))|{Path(__file__),basepath,parent,run/'RESULT.json',run/'FREEZE.json',run/'PLAN.json'}
    arms={};restorations={};normalized_configs={}
    for arm in ('control','candidate'):
        t=read(run/arm/'training.json');config=t['config'];paths|={run/arm/'training.json',run/arm/'training.log',run/arm/'training.restoration.json',run/arm/'FREEZE.json'}
        assert read(run/arm/'FREEZE.json')==frozen and t['all_workers_exit_zero']
        assert (config['workers'],config['updates'],config['rollout'],config['rotate_every'])==(16,30,32,2)
        assert config['learning_rate']=={'control':1e-6,'candidate':3e-6}[arm] and config['head_learning_rate']==1e-5 and config['resume'] and config['arm']==arm
        normalized_configs[arm]={k:v for k,v in config.items() if k not in ('arm','learning_rate','output','models_dir','freeze')}
        restored=t['restoration'];restorations[arm]=restored
        assert restored['parent_checkpoint_sha256']==restore.DEFAULT_SHA and restored['actual_Adam_counter_before_first_sampling']==3840 and restored['CUDA_restore_executed']
        assert all(restored['all_RNG_before_first_sampling'].values())
        assert restored==read(run/arm/'training.restoration.json')
        folder=Path(t['checkpoint']).parent;previous=initial;total=3840;term=collections.Counter();rows=collections.Counter();live=[0]*16;cuts=0;checks=[]
        for offset,record in enumerate(t['records']):
            u=31+offset;phase=offset//2;cp=folder/f'update-{u}.pt';s=torch.load(cp,map_location='cpu',weights_only=True);paths.add(cp)
            total+=record['actual_Adam_steps'];assert record['actual_Adam_steps']>0 and s['actual_Adam_steps']==record['actual_Adam_steps_total']==total and record['actual_Adam_steps_this_stage']==total-3840
            assert sha(cp)==record['checkpoint_sha256'] and s['completed_updates']==u and s['environment_steps']==15360+(offset+1)*512
            assert s['config']==config and s['complete_update_boundary'] and not s['native_environment_restorable'] and s['frozen_inputs']==frozen
            assert s['continuation_parent_sha256']==restore.DEFAULT_SHA and s['schedule_epoch']==record['schedule_epoch']==curriculum.SCHEDULE_EPOCH and s['continuation_restoration']==restored
            assert s['phase_close_events']==t['phase_close_events'][:phase] and s['phase_resource_events']==t['phase_resource_events'][:phase+1]
            delta=old.parameter_delta(s['models'],previous);old.compare_delta(delta,record['parameter_delta']);old.compare_delta(old.parameter_delta(s['models'],initial),record['delta_from_parent'])
            for v in s['optimizer_state_dict']['state'].values():
                assert 0<int(v['step'])<=total and torch.isfinite(v['exp_avg']).all() and torch.isfinite(v['exp_avg_sq']).all()
            assert s['torch_rng_state'].dtype==torch.uint8 and len(s['cuda_rng_states'])==1 and isinstance(s['python_rng_state'],tuple)
            restore.numpy_state_tuple(s['numpy_rng_state'])
            assert all(record['checkpoint_readback'][k] for k in ('model_exact','Adam_exact','global_RNG_payload_exact'))
            assert record['metrics']['maximum_recompute_logp_error']<=2e-4
            e=s['rollout_evidence'];assert e==record['rollout'];rp=Path(e['path']);paths.add(rp)
            assert sha(rp)==e['sha256'] and rp.stat().st_size==e['bytes'];raw=torch.load(rp,map_location='cpu',weights_only=False)
            assert len(raw['actions'])==len(raw['old_logp'])==512 and np.isfinite(raw['old_logp']).all() and np.isfinite(raw['values']).all() and np.isfinite(raw['next_values']).all()
            expected=curriculum.configs(config['scenario_file'],config['seed'],phase,folder.name);assert raw['configs']==expected and len(raw['samples'])==512
            if offset%2==0:live=[0]*16
            adv,ret=gae(raw['rewards'],raw['values'],raw['next_values'],raw['terminated'],raw['truncated'],gamma=1.,lam=.95)
            assert np.isfinite(adv).all() and np.isfinite(ret).all()
            last=np.asarray(raw['rewards'][-1])+np.asarray(raw['next_values'][-1])*(~np.asarray(raw['terminated'][-1],bool))-np.asarray(raw['values'][-1]);assert np.allclose(adv[-1],last,atol=1e-6,rtol=0)
            for tick in range(32):
                for slot,cfg in enumerate(expected):
                    i=tick*16+slot;obs=raw['samples'][i];action=raw['actions'][i];assert type(action) is int and 0<=action<len(obs['active_action_ids']) and obs['lab_side']==int(cfg['role']=='defender')
                    key=(cfg['TRAIN_scenario_index'],cfg['family'],cfg['role'],cfg['opponent']);rows[key]+=1;live[slot]+=1
                    if raw['terminated'][tick][slot]:
                        reward=float(raw['rewards'][tick][slot])+.5*graph.potential(obs);assert min(abs(reward-1),abs(reward+1))<1e-5;term[key+('win' if reward>0 else 'loss',)]+=1
                    cuts+=bool(raw['truncated'][tick][slot] and not raw['terminated'][tick][slot])
                    if raw['terminated'][tick][slot] or raw['truncated'][tick][slot]:live[slot]=0
            if offset%2==1:assert curriculum.close_evidence(phase,live,expected,'final_budget_stop' if phase==14 else 'phase_switch')==t['phase_close_events'][phase]
            checks.append(dict(global_update=u,new_Adam=record['actual_Adam_steps'],cumulative_Adam=total,checkpoint_sha256=sha(cp),rollout_sha256=e['sha256'],parameter_delta=delta));previous=s['models']
        assert len(rows)==240 and set(rows.values())=={64} and len({k[0] for k in rows})==60 and sum(rows.values())==15360
        terminals=sum(term.values());wins=sum(n for k,n in term.items() if k[-1]=='win');assert (terminals,wins,cuts)==(t['records'][-1]['episodes'],t['records'][-1]['wins'],t['records'][-1]['truncations'])
        assert total-3840==t['stage_actual_Adam_steps']==result['arms'][arm]['actual_Adam_steps_this_stage'] and total==result['arms'][arm]['actual_Adam_steps_total']
        assert Path(result['arms'][arm]['checkpoint'])==folder/'update-60.pt' and sha(folder/'update-60.pt')==result['arms'][arm]['checkpoint_sha256']
        model=graph.FullGraphPair(str(folder/'update-60.pt'),'last').cpu().eval();opt=restore.optimizer_for(model,s);opt.load_state_dict(s['optimizer_state_dict']);assert support.equal(opt.state_dict(),s['optimizer_state_dict'])
        arms[arm]=dict(new_Adam_steps=total-3840,cumulative_Adam_steps=total,new_samples=15360,terminals=terminals,wins=wins,cuts=cuts,checkpoint_reviews=checks,final_delta_from_parent=old.parameter_delta(s['models'],initial),terminals_by_cell=[dict(scenario=k[0],family=k[1],role=k[2],opponent=k[3],outcome=k[4],count=n) for k,n in sorted(term.items())],phase_close_events=t['phase_close_events'])
        print(json.dumps(dict(arm_checked=arm,cumulative_Adam=total,new_Adam=total-3840)),flush=True)
    assert normalized_configs['control']==normalized_configs['candidate']
    assert all(restorations['control'][k]==restorations['candidate'][k] for k in ('model_digest','Adam_digest_before_lr_override','all_RNG_before_first_sampling','parent_checkpoint_sha256'))
    dev=review_dev(run,result,paths)
    return dict(passed=True,scope='Completed engineering/learning evidence, not automatic ability promotion',arms=arms,DEV=dev,all_sources_current=True,source_count=len(frozen['input_sha256']),both_full_model_Adam_CPU_restored=True,
        independent_CUDA_restore=False,independent_full_probability_replay=False,new_native_games=0,GPU_operations=0,optimizer_steps_performed=0,native_state_restored=False,
        artifact_index=[dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size) for p in sorted(paths)])
def review_dev(run,result,paths):
    import numpy as np
    import torch
    from observation_digest import update
    from vcmi_gym.envs.v15.vcmi_env import Action
    def graphhash(obs):h=hashlib.sha256();update(h,obs);return h.hexdigest()
    games={};summaries={};total_games=0
    for report in result['DEV']:
        rp=Path(report['report']);assert sha(rp)==report['sha256'];paths.add(rp);d=read(rp);name=report['model'];opponent=report['opponent']
        cp=Path(read(run/'PLAN.json')['parent_checkpoint']) if name=='parent30' else Path(result['arms'][name]['checkpoint'])
        assert Path(d['checkpoint'])==cp and d['artifacts_checked_before_and_after'] and all(sha(p)==h for p,h in d['frozen_artifacts'].items())
        folder=LAB/'evaluations'/d['run_id'];wins=0;losses=[]
        for g in d['battles']:
            idx=int(g['scenario'].split('-')[-1]);side=int(g['role']=='defender');assert 192<=idx<200 and g['split']=='development' and g['seed']==2026103600+idx*100
            assert g['terminated'] and not g['truncated'] and g['invalid_actions']==0 and g['terminal_outcome']['result_type']==0 and g['success']==(g['terminal_outcome']['winner']==side)
            assert g['opponent']==opponent and Path(g['checkpoint'])==cp
            if opponent=='MMAI_MODEL':assert g['opponent_model']=='DATA/MMAI/models/lab-upstream-'+('attacker' if side else 'defender')+'.onnx' and g['opponent_temperature']==0
            raw=folder/f'{idx}-{g["role"]}-{g["seed"]}-recovered.json';log=raw.with_suffix('.log');assert read(raw)==g;paths|={raw,log}
            text=log.read_text();assert 'VCMI shutdown complete.' in text and 'Traceback' not in text
            mirrors=[json.loads(line) for line in text.splitlines() if line.startswith('{"scenario":')];assert mirrors==[g]
            e=g['step_evidence'];assert e['complete'] and e['unreturned_decision']==0 and e['decisions']==e['native_step_returns']==g['steps'] and len(e['files'])==2*g['steps']
            sequence=[];all_digest=hashlib.sha256();prior_next=None;types=collections.Counter()
            for tick in range(g['steps']):
                pair=e['files'][2*tick:2*tick+2];payload=[]
                for item in pair:
                    p=Path(item['path']);assert sha(p)==item['sha256'] and p.stat().st_size==item['bytes'];paths.add(p);payload.append(torch.load(p,map_location='cpu',weights_only=False))
                decision,returned=payload;obs=decision['obs'];identity=decision['identity'];assert identity==returned['identity']==e['identity'] and identity['checkpoint_sha256']==sha(cp) and identity['seed']==g['seed'] and identity['role']==g['role']
                assert decision['step']==returned['step']==tick+1 and decision['schema']=='battle-policy-decision-v1' and returned['schema']=='battle-native-step-return-v1'
                ids=np.asarray(obs['active_action_ids']);scores=decision['logits'];assert torch.isfinite(scores).all() and torch.isfinite(decision['value']).all() and scores.numel()==len(ids)
                assert np.array_equal(ids,decision['active_action_ids']) and decision['action']==int(ids[int(scores.argmax())]) and torch.equal(torch.softmax(scores,-1),decision['probabilities'])
                gh=graphhash(obs);update(all_digest,obs)
                if prior_next is not None:assert gh==prior_next
                prior_next=graphhash(returned['next_obs']);sequence.append(dict(step=tick+1,public_graph_sha256=gh,action=decision['action']))
                types[str(int(Action.decode_one(obs['nodes']['Action'][decision['action']]).ACTION_TYPE))]+=1
                if tick<g['steps']-1:assert not returned['terminated'] and not returned['truncated']
            assert returned['terminated'] and not returned['truncated'] and json.loads(json.dumps(returned['next_obs']['terminal_outcome']))==g['terminal_outcome'] and dict(types)==g['action_types']
            assert all_digest.hexdigest()==g['trajectory_sha256']
            lost=sum(g['terminal_outcome']['casualties'][str(side)].values());losses.append(lost);wins+=g['success'];total_games+=1
            games[(opponent,idx,g['role'],g['seed'],name)]=dict(win=g['success'],lost=lost,steps=g['steps'],sequence=sequence)
        assert len(d['battles'])==16 and wins==d['summary'][0]['wins'] and sum(losses)/16==d['summary'][0]['mean_permanent_units_lost'];summaries[name+'/'+opponent]=dict(games=16,wins=wins,mean_units_lost=sum(losses)/16)
    assert total_games==96 and len(games)==96
    comparisons=[]
    for opponent,idx,role,seed,name in sorted(games):
        if name!='parent30':continue
        for candidate in ('control','candidate'):
            a=games[(opponent,idx,role,seed,'parent30')];b=games[(opponent,idx,role,seed,candidate)];diff=None
            for i in range(max(len(a['sequence']),len(b['sequence']))):
                left=a['sequence'][i] if i<len(a['sequence']) else None;right=b['sequence'][i] if i<len(b['sequence']) else None
                if left!=right:diff=dict(step=i+1,parent=left,candidate=right);break
            comparisons.append(dict(arm=candidate,opponent=opponent,scenario=idx,role=role,seed=seed,parent_win=a['win'],candidate_win=b['win'],win_delta=int(b['win'])-int(a['win']),units_lost_delta=b['lost']-a['lost'],parent_steps=a['steps'],candidate_steps=b['steps'],first_public_graph_or_action_difference=diff,full_policy_sequence_equal=diff is None))
    direct=[]
    for opponent,idx,role,seed,name in sorted(games):
        if name!='control':continue
        a=games[(opponent,idx,role,seed,'control')];b=games[(opponent,idx,role,seed,'candidate')];diff=None
        for i in range(max(len(a['sequence']),len(b['sequence']))):
            left=a['sequence'][i] if i<len(a['sequence']) else None;right=b['sequence'][i] if i<len(b['sequence']) else None
            if left!=right:diff=dict(step=i+1,control=left,candidate=right);break
        direct.append(dict(opponent=opponent,scenario=idx,role=role,seed=seed,control_win=a['win'],candidate_win=b['win'],win_delta=int(b['win'])-int(a['win']),units_lost_delta=b['lost']-a['lost'],control_steps=a['steps'],candidate_steps=b['steps'],first_public_graph_or_action_difference=diff,full_policy_sequence_equal=diff is None))
    return dict(unique_games=96,shared_parent_baseline_games=32,paired_comparisons=64,control_vs_candidate_comparisons=32,summaries=summaries,pairs=comparisons,control_vs_candidate_pairs=direct,
        causal_limit='First public observation/action differences are reconstructable; this does not certify complete world or NPC-event-prefix equality, or cause of win/loss.')
def main():
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,default=LAB/'evaluations/battle-continuation-lr-paired-01');p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    try:result=gate(a.run)
    except (AssertionError,FileNotFoundError,KeyError) as error:print('INCOMPLETE/INVALID:',str(error));return 2
    a.out.mkdir(parents=True,exist_ok=False);start=time.monotonic()
    try:report=review(a.run,result);report['elapsed_seconds']=time.monotonic()-start
    except BaseException as error:
        (a.out/'AUDIT.json').write_text(json.dumps(dict(passed=False,error=repr(error),new_native_games=0,GPU_operations=0,optimizer_steps_performed=0),indent=2)+'\n');raise
    (a.out/'AUDIT.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(passed=True,arms={k:{f:v for f,v in r.items() if f in ('new_Adam_steps','cumulative_Adam_steps','new_samples','terminals','wins','cuts')} for k,r in report['arms'].items()},DEV_summaries=report['DEV']['summaries']),indent=2));return 0
if __name__=='__main__':raise SystemExit(main())
