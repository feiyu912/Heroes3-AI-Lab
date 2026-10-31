"""Final CPU audit. Refuses to start until all 30 updates and all four DEV reports finish."""
import argparse,collections,hashlib,json,math,sys,time
from pathlib import Path
OUT=Path(__file__).resolve().parent;HERE=OUT.parent;R=HERE.parent.parent/'research';LAB=Path('/root/heroes3-ai-lab')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def gate(run):
    if not (run/'RESULT.json').is_file():raise ValueError('INCOMPLETE: final RESULT absent; no final audit or certification')
    result=read(run/'RESULT.json');training=read(run/'training.json')
    if not result.get('passed') or not result.get('training_completed') or not training.get('completed') or len(training.get('records',[]))!=30:raise ValueError('INCOMPLETE/FAILED: final 30-update execution required')
    expected={str(run/(name+'-'+opp+'-DEV.json')) for name in ('B64','update30') for opp in ('BattleAI','MMAI_MODEL')}
    if len(result.get('DEV',[]))!=4 or {d['report'] for d in result['DEV']}!=expected or not all(Path(p).is_file() for p in expected):raise ValueError('INCOMPLETE: all four complete DEV reports required')
    return result,training
def main():
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,default=LAB/'evaluations/battle-diverse60-native-02');p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    try:result,training=gate(a.run)
    except (ValueError,FileNotFoundError) as error:print(str(error));return 2
    a.out.mkdir(parents=True,exist_ok=False)
    try:
        report=review(a.run,a.out,result,training);report['passed']=True
    except BaseException as error:
        report=dict(passed=False,error=repr(error),final_experiment_certified=False,new_native_games=0,GPU_operations=0,optimizer_steps_performed=0)
        (a.out/'AUDIT.json').write_text(json.dumps(report,indent=2)+'\n');raise
    (a.out/'AUDIT.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k in ('passed','actual_Adam_steps','TRAIN_summary','DEV_summary','paired_flips','elapsed_seconds')},indent=2));return 0
def review(run,out,result,training):
    import numpy as np
    import torch
    sys.path[:0]=[str(HERE),str(R),str(LAB/'src/gym')]
    import curriculum
    import full_graph_policy as graph
    from masked_ppo import gae
    from support import equal
    torch.set_num_threads(1);started=time.monotonic();freeze=read(run/'FREEZE.json');plan=read(run/'PLAN.json');config=training['config']
    assert all(sha(p)==h for p,h in freeze['input_sha256'].items()) and freeze['schema']=='battle-diverse-60case-last-v1'
    assert (config['workers'],config['updates'],config['rollout'],config['rotate_every'],config['mode'])==(16,30,32,2,'last')
    assert config['opponents']==['BattleAI','MMAI_MODEL'] and config['native_opponent_device']=='cpu' and not config['resume']
    assert config['learning_rate']==1e-6 and config['head_learning_rate']==1e-5 and config['gamma']==1 and config['shaping']==.5 and config['step_cost']==0
    assert training['all_workers_exit_zero'] and result['ability_improvement_claim'] is False
    registration=curriculum.registered(config['scenario_file']);assert registration==plan['registered_curriculum'] and registration['selected_cases']==60
    b64=LAB/'models/graph-finetune/1792068859379237126/update-64.pt';assert sha(b64)=='1e022707186a3c0dad7c671233b100930e870fff6c79cc703fb5b89dfb192936'
    initial=torch.load(b64,map_location='cpu',weights_only=True)['models'];previous=initial;folder=Path(result['checkpoint']).parent
    paths=[Path(__file__),run/'RESULT.json',run/'training.json',run/'PLAN.json',run/'FREEZE.json',run/'training.log',b64,HERE/'curriculum.py',HERE/'support.py',R/'masked_ppo.py',R/'full_graph_policy.py',R/'recovered-graph.py']
    # Include every original frozen dependency in the reproducible archive index.
    paths +=[Path(p) for p in freeze['input_sha256']]
    term=collections.Counter();rows_per_cell=collections.Counter();configured_slots=[];live=[0]*16;closures=[];checkpoint_reviews=[];bootstrap=[];global_steps=0;forced=0;sampled_non_argmax_unknown=True
    for i in range(1,31):
        record=training['records'][i-1];phase=(i-1)//2;assert record['update']==i and record['phase']==phase and record['samples']==512
        assert record['actual_Adam_steps']>0;global_steps+=record['actual_Adam_steps'];assert record['actual_Adam_steps_total']==global_steps
        assert record['metrics']['maximum_recompute_logp_error']<=2e-4 and record['metrics']['recompute_batch_size']==16
        cp=folder/f'update-{i}.pt';state=torch.load(cp,map_location='cpu',weights_only=True)
        assert sha(cp)==record['checkpoint_sha256'] and state['completed_updates']==i and state['actual_Adam_steps']==global_steps and state['complete_update_boundary'] is True
        assert state['frozen_inputs']==freeze and state['native_environment_restorable'] is False and state['config']==config
        assert state['phase_close_events']==training['phase_close_events'][:phase] and state['phase_resource_events']==training['phase_resource_events'][:phase+1]
        per_step=parameter_delta(state['models'],previous);from_b64=parameter_delta(state['models'],initial)
        compare_delta(per_step,record['parameter_delta']);compare_delta(from_b64,record['delta_from_B64'])
        assert all(state['models'][role]['metadata']==initial[role]['metadata'] for role in ('attacker','defender'))
        adam_steps=[]
        for identity,s in state['optimizer_state_dict']['state'].items():
            step=int(s['step']);assert 0<step<=global_steps and s['exp_avg'].shape==s['exp_avg_sq'].shape
            assert torch.isfinite(s['exp_avg']).all() and torch.isfinite(s['exp_avg_sq']).all();adam_steps.append(step)
        assert adam_steps and state['torch_rng_state'].dtype==torch.uint8 and len(state['cuda_rng_states'])==1 and state['cuda_rng_states'][0].dtype==torch.uint8
        assert isinstance(state['python_rng_state'],tuple) and isinstance(state['numpy_rng_state']['keys'],list)
        assert record['checkpoint_readback']['model_exact'] and record['checkpoint_readback']['Adam_exact'] and record['checkpoint_readback']['global_RNG_payload_exact']
        evidence=state['rollout_evidence'];assert evidence==record['rollout'];rp=Path(evidence['path']);assert rp==folder/f'rollout-{i}.pt' and sha(rp)==evidence['sha256'] and rp.stat().st_size==evidence['bytes']
        raw=torch.load(rp,map_location='cpu',weights_only=False);assert len(raw['samples'])==len(raw['actions'])==len(raw['old_logp'])==512
        expected=curriculum.configs(config['scenario_file'],config['seed'],phase,folder.name);assert raw['configs']==expected
        if i%2==1:
            live=[0]*16;configured_slots +=[(c['TRAIN_scenario_index'],c['family'],c['role'],c['opponent']) for c in expected]
        for field in ('rewards','values','next_values','terminated','truncated'):assert np.asarray(raw[field]).shape==(32,16)
        assert np.isfinite(raw['old_logp']).all() and np.isfinite(raw['values']).all() and np.isfinite(raw['next_values']).all() and max(raw['old_logp'])<=1e-5
        advantages,returns=gae(raw['rewards'],raw['values'],raw['next_values'],raw['terminated'],raw['truncated'],gamma=1.,lam=.95)
        assert np.isfinite(advantages).all() and np.isfinite(returns).all()
        expected_last=np.asarray(raw['rewards'][-1])+np.asarray(raw['next_values'][-1])*(~np.asarray(raw['terminated'][-1],bool))-np.asarray(raw['values'][-1])
        assert np.allclose(advantages[-1],expected_last,atol=1e-6,rtol=0)
        cuts=0
        for t in range(32):
            for slot,cfg in enumerate(expected):
                index=t*16+slot;q=raw['samples'][index];action=raw['actions'][index]
                assert type(action) is int and 0<=action<len(q['active_action_ids']) and q['lab_side']==int(cfg['role']=='defender')
                forced+=len(q['active_action_ids'])==1;key=(cfg['TRAIN_scenario_index'],cfg['family'],cfg['role'],cfg['opponent']);rows_per_cell[key]+=1;live[slot]+=1
                if raw['terminated'][t][slot]:
                    native=float(raw['rewards'][t][slot])+.5*graph.potential(q);assert min(abs(native-1),abs(native+1))<1e-5;term[key+('win' if native>0 else 'loss',)]+=1
                if raw['truncated'][t][slot] and not raw['terminated'][t][slot]:cuts+=1
                if raw['terminated'][t][slot] or raw['truncated'][t][slot]:live[slot]=0
        bootstrap.append(dict(update=i,last_step_bootstrap_checked=True,nonterminal_last_rows=int((~np.asarray(raw['terminated'][-1],bool)).sum()),cuts=cuts))
        if i%2==0:
            event=curriculum.close_evidence(phase,live,expected,'final_budget_stop' if phase==14 else 'phase_switch');assert event==training['phase_close_events'][phase];closures.append(event)
        checkpoint_reviews.append(dict(update=i,checkpoint_sha256=sha(cp),rollout_sha256=evidence['sha256'],actual_Adam_steps=record['actual_Adam_steps'],actual_total_steps=global_steps,Adam_parameter_step_range=[min(adam_steps),max(adam_steps)],changed_from_previous=per_step,changed_from_B64=from_b64))
        paths +=[cp,rp];previous=state['models']
        print(json.dumps(dict(completed_boundary_checked=i,of=30,actual_Adam_steps=global_steps)),flush=True)
    assert len(configured_slots)==len(set(configured_slots))==240 and len({c[0] for c in configured_slots})==60
    assert len(rows_per_cell)==240 and set(rows_per_cell.values())=={64} and sum(rows_per_cell.values())==15360
    assert len(closures)==15 and len(training['phase_resource_events'])==15
    normal=sum(term.values());wins=sum(n for k,n in term.items() if k[-1]=='win');cuts=sum(b['cuts'] for b in bootstrap)
    assert normal==training['records'][-1]['episodes'] and wins==training['records'][-1]['wins'] and cuts==training['records'][-1]['truncations']
    assert result['actual_Adam_steps']==global_steps and sha(result['checkpoint'])==result['checkpoint_sha256'] and Path(result['checkpoint'])==folder/'update-30.pt'
    # Actual CPU restore of final model and optimizer; no CUDA RNG restore or step.
    restored=graph.FullGraphPair(str(folder/'update-30.pt'),'last').cpu().eval();heads=[];body=[]
    for n,p in restored.named_parameters():
        if p.requires_grad:(heads if 'policy_head__' in n or 'value_head__' in n else body).append(p)
    opt=torch.optim.Adam([dict(params=heads,lr=1e-5),dict(params=body,lr=1e-6)]);opt.load_state_dict(state['optimizer_state_dict']);assert equal(opt.state_dict(),state['optimizer_state_dict'])
    dev,paired,raw_count=review_dev(run,result,paths)
    groups=collections.Counter()
    for k,n in term.items():groups[(k[1],k[2],k[3],k[4])]+=n
    artifact_index=[dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size) for p in sorted(set(paths))]
    return dict(final_experiment_certified=True,new_native_games=0,GPU_operations=0,optimizer_steps_performed=0,actual_Adam_steps=global_steps,
        checkpoints_and_rollouts_checked=30,all_saved_model_parameter_deltas_independently_recomputed=True,final_model_Adam_independently_restored_CPU=True,
        saved_RNG_payloads_inspected=True,CUDA_RNG_restore_independently_rerun=False,all_onpolicy_probability_replay_independently_rerun=False,
        TRAIN_summary=dict(unique_cases=60,unique_case_role_opponent_slots=240,owned_transitions=15360,rows_each_slot=64,normal_terminals=normal,wins=wins,cuts=cuts,forced_candidates=forced),
        TRAIN_terminal_strata=[dict(family=k[0],role=k[1],opponent=k[2],outcome=k[3],count=n) for k,n in sorted(groups.items())],
        TRAIN_per_case_terminals=[dict(scenario=k[0],family=k[1],role=k[2],opponent=k[3],outcome=k[4],count=n) for k,n in sorted(term.items())],
        checkpoint_reviews=checkpoint_reviews,bootstrap_checks=bootstrap,phase_close_events=closures,
        minimum_recorded_available_mib=min(r['free_mib'] for r in training['records']),maximum_recorded_model_GPU_peak_mib=max(r['gpu_peak_mib'] for r in training['records']),
        DEV_summary=dev,DEV_raw_files_verified=raw_count,pairs=paired,paired_flips=[p for p in paired if p['win_delta']],
        native_environment_restored=False,DEV_first_policy_divergence_reconstructable=False,ability_improvement_claim=False,
        limitation='Case/role/opponent transition exposure is balanced; actual terminal counts need not be. Saved graph-digest DEV reports do not recover per-step policy/world causality. Small known-map DEV is not hidden confirmation.',
        input_sha256={x['path']:x['sha256'] for x in artifact_index},artifact_index=artifact_index,elapsed_seconds=time.monotonic()-started)
def parameter_delta(current,before):
    import torch
    groups={k:dict(changed_tensors=0,squared_delta=0.) for g in ('actor_heads','critic_heads','last_graph') for k in (g,'attacker/'+g,'defender/'+g)};changed=[];total=0.;frozen=0
    for role in ('attacker','defender'):
        weights=current[role]['weights'];assert weights.keys()==before[role]['weights'].keys()
        for name,p in weights.items():
            prior=before[role]['weights'][name];released=name.startswith(('policy_head.','value_head.','gnn.convs.2.','gnn.norms.2.'));same=torch.equal(p,prior)
            if not released:assert same,'Frozen parameter changed '+role+'/'+name;frozen+=1
            if same:continue
            group='actor_heads' if name.startswith('policy_head.') else 'critic_heads' if name.startswith('value_head.') else 'last_graph'
            value=float((p.double()-prior.double()).square().sum());total+=value;changed.append('models.'+role+'.weights.'+name.replace('.','__'))
            for key in (group,role+'/'+group):groups[key]['changed_tensors']+=1;groups[key]['squared_delta']+=value
    for g in groups.values():g['l2']=g.pop('squared_delta')**.5
    return dict(changed_tensors=len(changed),l2=total**.5,unchanged_frozen_tensors=frozen,changed_parameter_names=changed,parameter_groups=groups)
def compare_delta(actual,recorded):
    assert actual['changed_tensors']==recorded['changed_tensors'] and actual['unchanged_frozen_tensors']==recorded['unchanged_frozen_tensors'] and sorted(actual['changed_parameter_names'])==sorted(recorded['changed_parameter_names'])
    assert math.isclose(actual['l2'],recorded['l2'],abs_tol=1e-10,rel_tol=1e-8)
    for key,g in actual['parameter_groups'].items():
        old=recorded['parameter_groups'][key];assert g['changed_tensors']==old['changed_tensors'] and math.isclose(g['l2'],old['l2'],abs_tol=1e-10,rel_tol=1e-8)
def review_dev(run,result,paths):
    summaries={};paired={};raw_count=0
    for original in result['DEV']:
        p=Path(original['report']);assert sha(p)==original['sha256'];d=read(p);assert d['artifacts_checked_before_and_after'] and all(sha(f)==h for f,h in d['frozen_artifacts'].items())
        name=original['model'];opponent=original['opponent'];assert name in ('B64','update30') and opponent in ('BattleAI','MMAI_MODEL') and len(d['battles'])==16
        expected_checkpoint=(LAB/'models/graph-finetune/1792068859379237126/update-64.pt') if name=='B64' else Path(result['checkpoint'])
        assert Path(d['checkpoint'])==expected_checkpoint and sha(d['checkpoint'])==sha(expected_checkpoint)
        root=LAB/'evaluations'/str(d['run_id']);wins=0;lost=[]
        for g in d['battles']:
            scenario=int(g['scenario'].split('-')[-1]);side=int(g['role']=='defender');assert 192<=scenario<200 and g['split']=='development' and g['seed']==2026103400+scenario*100
            assert g['terminated'] and not g['truncated'] and g['invalid_actions']==0 and g['terminal_outcome']['result_type']==0 and g['success']==(g['terminal_outcome']['winner']==side)
            assert g['policy']=='recovered' and g['opponent']==opponent and sha(g['checkpoint'])==sha(d['checkpoint'])
            if opponent=='MMAI_MODEL':assert g['opponent_model']=='DATA/MMAI/models/lab-upstream-'+('attacker' if side else 'defender')+'.onnx' and g['opponent_temperature']==0
            file=root/f'{scenario}-{g["role"]}-{g["seed"]}-recovered.json';log=file.with_suffix('.log');text=log.read_text();assert read(file)==g and 'VCMI shutdown complete.' in text and 'Traceback' not in text
            mirror=[s for s in text.splitlines() if s.startswith('{"scenario":')];assert len(mirror)==1 and json.loads(mirror[0])==g
            loss=sum(g['terminal_outcome']['casualties'][str(side)].values());wins+=g['success'];lost.append(loss)
            paired.setdefault((opponent,scenario,g['role'],g['seed']),{})[name]=dict(win=g['success'],steps=g['steps'],permanent_units_lost=loss,trajectory_sha256=g['trajectory_sha256'],action_types=g['action_types'])
            paths +=[file,log];raw_count+=1
        assert wins==d['summary'][0]['wins'] and sum(lost)/16==d['summary'][0]['mean_permanent_units_lost'];summaries[name+'/'+opponent]=dict(wins=wins,games=16,mean_permanent_units_lost=sum(lost)/16);paths.append(p)
    assert raw_count==64 and len(paired)==32 and all(set(v)=={'B64','update30'} for v in paired.values())
    pairs=[dict(opponent=k[0],scenario=k[1],role=k[2],seed=k[3],arms=v,win_delta=int(v['update30']['win'])-int(v['B64']['win']),unit_loss_delta=v['update30']['permanent_units_lost']-v['B64']['permanent_units_lost'],public_graph_trajectory_digest_same=v['update30']['trajectory_sha256']==v['B64']['trajectory_sha256']) for k,v in sorted(paired.items())]
    return summaries,pairs,raw_count
if __name__=='__main__':raise SystemExit(main())
