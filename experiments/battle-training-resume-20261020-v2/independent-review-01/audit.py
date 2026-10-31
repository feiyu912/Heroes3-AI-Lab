"""CPU-only independent checkpoint/rollout/native evaluation evidence review."""
import collections,hashlib,json,math,statistics,sys,time
from pathlib import Path
import numpy as np
import torch
OUT=Path(__file__).resolve().parent;HERE=OUT.parent;R=HERE.parent.parent/'research';LAB=Path('/root/heroes3-ai-lab');B=LAB/'evaluations/battle-lastgraph-resume-20261020-02'
sys.path[:0]=[str(R),str(HERE),str(LAB/'src/gym')]
import full_graph_policy as graph
from masked_ppo import distribution
from support import equal
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def state_delta(model,before):
    result={};frozen=0
    for name,p in model.named_parameters():
        d=p.detach().cpu().double()-before[name].double();changed=bool(d.ne(0).any())
        if not p.requires_grad:assert not changed,name;frozen+=1
        role='attacker' if 'attacker' in name else 'defender';group='graph_last' if 'gnn__' in name else 'policy_head' if 'policy_head__' in name else 'value_head'
        x=result.setdefault(role+'/'+group,dict(changed_tensors=0,l2_squared=0.));x['changed_tensors']+=changed;x['l2_squared']+=float(d.square().sum())
    for x in result.values():x['l2']=x.pop('l2_squared')**.5
    return dict(groups=result,unchanged_frozen_tensors=frozen)
def main():
    torch.set_num_threads(1);start=time.monotonic();top=read(B/'RESULT.json');report=read(B/'training.json');freeze=read(B/'FREEZE.json');assert top['passed'] and report['completed'] and report['all_workers_exit_zero']
    assert all(sha(p)==h for p,h in freeze['input_sha256'].items());B64=LAB/'models/graph-finetune/1792068859379237126/update-64.pt';base=graph.FullGraphPair(str(B64),'last').cpu().eval();base_state={n:p.detach().clone() for n,p in base.named_parameters()};folder=Path(top['checkpoint']).parent
    paths=[Path(__file__),B/'RESULT.json',B/'training.json',B/'FREEZE.json',B64];checks=[];rollouts=[];models=[base]
    for i in range(1,5):
        p=folder/f'update-{i}.pt';m=graph.FullGraphPair(str(p),'last').cpu().eval();state=torch.load(p,map_location='cpu',weights_only=True);record=report['records'][i-1]
        assert sha(p)==record['checkpoint_sha256'] and state['completed_updates']==i and state['actual_Adam_steps']==64*i and state['complete_update_boundary'] and not state['native_environment_restorable']
        assert state['frozen_inputs']==freeze and state['finetuning_mode']=='last' and state['config']['opponents']==['BattleAI','MMAI_MODEL']
        heads=[];body=[]
        for n,param in m.named_parameters():
            if param.requires_grad:(heads if 'policy_head__' in n or 'value_head__' in n else body).append(param)
        opt=torch.optim.Adam([dict(params=heads,lr=1e-5),dict(params=body,lr=1e-6)])
        opt.load_state_dict(state['optimizer_state_dict']);assert equal(opt.state_dict(),state['optimizer_state_dict'])
        steps=[int(s['step']) for s in opt.state.values()];assert 0<min(steps)<=max(steps)<=64*i
        assert state['torch_rng_state'].dtype==torch.uint8 and len(state['cuda_rng_states'])==1 and state['cuda_rng_states'][0].dtype==torch.uint8
        changes=state_delta(m,base_state);assert all(changes['groups'][role+'/graph_last']['changed_tensors']>0 and changes['groups'][role+'/policy_head']['changed_tensors']>0 for role in ('attacker','defender'))
        checks.append(dict(update=i,sha256=sha(p),actual_Adam_steps=64,actual_Adam_steps_total=64*i,saved_Adam_parameter_step_range=[min(steps),max(steps)],Adam_CPU_restore_exact=True,parameter_delta_from_B64=changes,GPU_recompute_error_from_original_record=record['metrics']['maximum_recompute_logp_error']))
        rp=folder/f'rollout-{i}.pt';raw=torch.load(rp,map_location='cpu',weights_only=False);assert len(raw['samples'])==len(raw['actions'])==len(raw['old_logp'])==256 and np.asarray(raw['rewards']).shape==(32,8)
        assert all(s['feature_version']=='upstream-graph-v15' and s['opponent'] in ('BattleAI','MMAI_MODEL') for s in raw['configs'])
        rollouts.append(raw);models.append(m);paths +=[p,rp]
    terminal_counts=collections.Counter();counts=collections.Counter();replay=[];decisions=[];all_cfg=rollouts[0]['configs'];assert all(r['configs']==all_cfg for r in rollouts)
    for iteration,raw in enumerate(rollouts):
        before=models[iteration];after=models[iteration+1];log_errors=[];value_errors=[];changed=[]
        for t in range(32):
            obs=raw['samples'][t*8:(t+1)*8]
            with torch.no_grad():x,v=before(*graph.collate(obs,'cpu'));y,_=after(*graph.collate(obs,'cpu'));z,_=models[-1](*graph.collate(obs,'cpu'));u,_=base(*graph.collate(obs,'cpu'))
            dist=distribution(x,graph.collate(obs,'cpu')[-1]);chosen=torch.tensor(raw['actions'][t*8:(t+1)*8]);lp=dist.log_prob(chosen)
            for worker,q in enumerate(obs):
                a=int(chosen[worker]);assert 0<=a<len(q['active_action_ids']);counts['transitions']+=1;counts['sampled_non_argmax']+=a!=int(x[worker].argmax());counts['B64_vs_update4_argmax_changes']+=int(z[worker].argmax())!=int(u[worker].argmax())
                log_errors.append(abs(float(lp[worker])-raw['old_logp'][t*8+worker]));value_errors.append(abs(float(v[worker])-float(raw['values'][t][worker])))
                if int(x[worker].argmax())!=int(y[worker].argmax()):changed.append(dict(t=t,worker=worker,before_action_id=int(q['active_action_ids'][int(x[worker].argmax())]),after_action_id=int(q['active_action_ids'][int(y[worker].argmax())])))
                if raw['terminated'][t][worker]:
                    # At real termination potential(next)=0, so recover original +/-1.
                    terminal_reward=float(raw['rewards'][t][worker])+.5*graph.potential(q)
                    assert min(abs(terminal_reward-1),abs(terminal_reward+1))<1e-5
                    cfg=all_cfg[worker];terminal_counts[(cfg['opponent'],cfg['role'],'win' if terminal_reward>0 else 'loss')]+=1
                assert not raw['truncated'][t][worker]
        assert max(log_errors)<2e-4 and max(value_errors)<2e-4
        replay.append(dict(update=iteration+1,CPU_archived_logprob_max_error=max(log_errors),CPU_archived_value_max_error=max(value_errors),before_after_argmax_changes=len(changed),first_changed_TRAIN_observations=changed[:8]))
        print('CPU checkpoint/rollout %d passed'%(iteration+1),flush=True)
    assert counts['transitions']==1024 and sum(terminal_counts.values())==40 and sum(v for k,v in terminal_counts.items() if k[-1]=='win')==33
    scenarios=read(R/'diverse-curriculum.json');map_to_index={s['map']:i for i,s in enumerate(scenarios)};schedule=[dict(map=c['map'],TRAIN_index=map_to_index[c['map']],family=map_to_index[c['map']]%6,opponent=c['opponent'],role=c['role']) for c in all_cfg];assert all(s['TRAIN_index']<192 for s in schedule)
    evaluations={};games=[];paired={}
    for name in ('B64','update4'):
        for opponent in ('BattleAI','MMAI_MODEL'):
            p=B/(name+'-'+opponent+'-DEV.json');d=read(p);assert d['artifacts_checked_before_and_after'] and len(d['battles'])==16 and all(sha(f)==h for f,h in d['frozen_artifacts'].items())
            runtime=LAB/'evaluations'/str(d['run_id']);wins=0;losses=[]
            for g in d['battles']:
                side=int(g['role']=='defender');o=g['terminal_outcome'];assert g['terminated'] and not g['truncated'] and g['invalid_actions']==0 and o['result_type']==0 and g['success']==(o['winner']==side)
                sid=int(g['scenario'].split('-')[-1]);assert g['split']=='development' and 192<=sid<200 and g['seed']==2026102500+100*sid
                file=runtime/f'{sid}-{g["role"]}-{g["seed"]}-recovered.json';log=file.with_suffix('.log');assert read(file)==g
                text=log.read_text();assert 'VCMI shutdown complete.' in text and 'Traceback' not in text
                json_line=[s for s in text.splitlines() if s.startswith('{"scenario":')];assert len(json_line)==1 and json.loads(json_line[0])==g
                assert sha(g['checkpoint'])==sha(B64 if name=='B64' else top['checkpoint'])
                if opponent=='MMAI_MODEL':assert g['opponent_model']=='DATA/MMAI/models/lab-upstream-'+('attacker' if side else 'defender')+'.onnx' and g['opponent_temperature']==0
                casualty=sum(o['casualties'][str(side)].values());wins+=g['success'];losses.append(casualty)
                row=dict(model=name,opponent=opponent,scenario=sid,role=g['role'],seed=g['seed'],win=g['success'],steps=g['steps'],permanent_units_lost=casualty,trajectory_sha256=g['trajectory_sha256'],action_types=g['action_types'])
                games.append(row);paired.setdefault((opponent,sid,g['role'],g['seed']),{})[name]=row;paths +=[file,log]
            assert wins==d['summary'][0]['wins'] and statistics.mean(losses)==d['summary'][0]['mean_permanent_units_lost']
            evaluations[name+'/'+opponent]=dict(wins=wins,games=16,mean_permanent_units_lost=statistics.mean(losses));paths.append(p)
    flips=[];pair_stats=[]
    for key,arms in paired.items():
        a,b=arms['B64'],arms['update4'];stat=dict(opponent=key[0],scenario=key[1],role=key[2],seed=key[3],win_delta=int(b['win'])-int(a['win']),units_lost_delta=b['permanent_units_lost']-a['permanent_units_lost'],observation_trajectory_digest_same=a['trajectory_sha256']==b['trajectory_sha256'],B64=a,update4=b)
        pair_stats.append(stat)
        if stat['win_delta']:flips.append(stat)
    out=dict(passed=True,new_native_games=0,GPU_operations=0,optimizer_steps_performed=0,checkpoints_CPU_read_and_Adam_restored=checks,original_GPU_recompute_certificate_only=True,
        rollout_CPU_policy_replays=replay,TRAIN_counts=dict(counts),TRAIN_terminal_counts={str(k):v for k,v in terminal_counts.items()},TRAIN_schedule=schedule,TRAIN_families=sorted({s['family'] for s in schedule}),
        evaluations=evaluations,raw_DEV_logs_and_JSON_verified=64,paired_flips=flips,pairs=pair_stats,
        DEV_first_policy_difference_recoverable=False,limitation='Frozen DEV runner stores whole-observation digest and action-type totals, not per-step obs/actions. First policy divergence cannot be reconstructed. No new native replay performed.',
        saved_global_RNG_payloads_inspected=True,GPU_RNG_restore_independently_rerun=False,native_environment_restored=False,ability_improvement_claim=False,input_sha256={str(p):sha(p) for p in paths},elapsed_seconds=time.monotonic()-start)
    (OUT/'AUDIT.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:out[k] for k in ['passed','TRAIN_counts','TRAIN_terminal_counts','TRAIN_families','evaluations','paired_flips','elapsed_seconds']},indent=2))
if __name__=='__main__':main()
