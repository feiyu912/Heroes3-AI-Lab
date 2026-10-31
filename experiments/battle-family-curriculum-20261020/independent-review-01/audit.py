"""Brief actual family-course/checkpoint/closure/paired-result audit; CPU only."""
import collections,hashlib,json,re,statistics,sys,time
from pathlib import Path
import numpy as np
import torch
OUT=Path(__file__).resolve().parent;HERE=OUT.parent;R=HERE.parent.parent/'research';LAB=Path('/root/heroes3-ai-lab');B=LAB/'evaluations/battle-family-curriculum-native-01'
sys.path[:0]=[str(HERE),str(R),str(LAB/'src/gym')]
import curriculum
import full_graph_policy as graph
from masked_ppo import gae
from support import equal
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def main():
    torch.set_num_threads(1);started=time.monotonic();t=read(B/'training.json');result=read(B/'RESULT.json');freeze=read(B/'FREEZE.json');plan=read(B/'PLAN.json');folder=Path(result['checkpoint']).parent
    assert result['passed'] and t['completed'] and t['all_workers_exit_zero'] and t['config']['workers']==12
    assert all(sha(p)==h for p,h in freeze['input_sha256'].items()) and t['config']['rotate_every']==2
    registration=curriculum.registered(t['config']['scenario_file']);assert registration==plan['registered_curriculum']
    b64=LAB/'models/graph-finetune/1792068859379237126/update-64.pt';base=graph.FullGraphPair(str(b64),'last').cpu().eval();initial={n:p.detach().clone() for n,p in base.named_parameters()}
    terminal=collections.Counter();cells=[];boundaries=[];checkpoints=[];raws=[];paths=[Path(__file__),B/'RESULT.json',B/'training.json',B/'PLAN.json',B/'FREEZE.json',B/'training.log',b64]
    for i in range(1,5):
        p=folder/f'update-{i}.pt';s=torch.load(p,map_location='cpu',weights_only=True);m=graph.FullGraphPair(str(p),'last').cpu().eval();record=t['records'][i-1]
        assert sha(p)==record['checkpoint_sha256'] and s['frozen_inputs']==freeze and s['actual_Adam_steps']==96*i and s['complete_update_boundary'] and not s['native_environment_restorable']
        heads=[];body=[];delta=collections.Counter();frozen_count=0
        for n,param in m.named_parameters():
            change=not torch.equal(param,initial[n]);role='attacker' if 'attacker' in n else 'defender';kind='last_graph' if 'gnn__' in n else 'policy' if 'policy_head__' in n else 'value'
            if not param.requires_grad:assert not change;frozen_count+=1
            elif change:delta[role+'/'+kind]+=1
            if param.requires_grad:(heads if 'policy_head__' in n or 'value_head__' in n else body).append(param)
        assert delta['attacker/last_graph'] and delta['defender/last_graph']
        opt=torch.optim.Adam([dict(params=heads,lr=1e-5),dict(params=body,lr=1e-6)]);opt.load_state_dict(s['optimizer_state_dict']);assert equal(opt.state_dict(),s['optimizer_state_dict'])
        steps=[int(v['step']) for v in opt.state.values()];assert 0<min(steps)<=max(steps)<=96*i
        assert len(s['phase_close_events'])==(0 if i<=2 else 1)
        checkpoints.append(dict(update=i,sha256=sha(p),actual_Adam_steps=96,actual_total_steps=96*i,CPU_Adam_restore_exact=True,parameter_step_range=[min(steps),max(steps)],changed_tensors_from_B64=dict(delta),unchanged_frozen_tensors=frozen_count))
        rp=folder/f'rollout-{i}.pt';raw=torch.load(rp,map_location='cpu',weights_only=False);assert len(raw['samples'])==384 and np.asarray(raw['rewards']).shape==(32,12);raws.append(raw);phase=(i-1)//2
        expected=curriculum.configs(t['config']['scenario_file'],2026102012,phase,folder.name);assert raw['configs']==expected
        if i in (1,3):cells +=[(c['family'],c['role'],c['opponent']) for c in expected]
        advantage,returns=gae(raw['rewards'],raw['values'],raw['next_values'],raw['terminated'],raw['truncated'],gamma=1.,lam=.95)
        assert np.isfinite(advantage).all() and np.isfinite(returns).all()
        final_delta=np.asarray(raw['rewards'][-1])+np.asarray(raw['next_values'][-1])*(~np.asarray(raw['terminated'][-1],bool))-np.asarray(raw['values'][-1])
        assert np.allclose(advantage[-1],final_delta,atol=1e-6,rtol=0)
        boundaries.append(dict(update=i,at_phase_end=i%2==0,last_GAE_delta_bootstrap_exact=True,nonterminal_last_rows=int((~np.asarray(raw['terminated'][-1],bool)).sum())))
        assert not np.asarray(raw['truncated']).any()
        for row in range(32):
            for slot in range(12):
                q=raw['samples'][row*12+slot];assert 0<=raw['actions'][row*12+slot]<len(q['active_action_ids'])
                if raw['terminated'][row][slot]:
                    r=float(raw['rewards'][row][slot])+.5*graph.potential(q);assert min(abs(r-1),abs(r+1))<1e-5
                    cfg=expected[slot];terminal[(cfg['family'],cfg['opponent'],cfg['role'],'win' if r>0 else 'loss')]+=1
        paths +=[p,rp]
    assert len(set(cells))==len(cells)==24 and sum(terminal.values())==60 and sum(v for k,v in terminal.items() if k[-1]=='win')==46
    actual_close=[]
    for phase in range(2):
        live=[0]*12
        for raw in raws[phase*2:phase*2+2]:
            for row in range(32):
                for slot in range(12):
                    live[slot]+=1
                    if raw['terminated'][row][slot] or raw['truncated'][row][slot]:live[slot]=0
        event=curriculum.close_evidence(phase,live,raw['configs'],'phase_switch' if phase==0 else 'final_budget_stop');assert event==t['phase_close_events'][phase];actual_close.append(event)
    log=(B/'training.log').read_text();boots=re.findall(r'Worker data: (/root/heroes3-ai-lab/workers/family-[^/]+/(\d+)-(\d+))/data/vcmi',log)
    worker_evidence=[]
    for raw in (raws[0],raws[2]):
        for cfg in raw['configs']:
            root=Path(cfg['worker_root']);data=root/'data/vcmi';settings=data/'config/settings.json';assert settings.is_file()
            assert all((data/name).resolve()==(LAB/'data/vcmi'/name).resolve() for name in ('Data','Maps','Mods'))
            worker_evidence.append(dict(path=str(root),settings_sha256=sha(settings)));paths.append(settings)
    assert len({e['path'] for e in worker_evidence})==24
    summaries={};pairs={};raw_files=0
    for name in ('B64','update4'):
        for opponent in ('BattleAI','MMAI_MODEL'):
            p=B/(name+'-'+opponent+'-DEV.json');d=read(p);assert d['artifacts_checked_before_and_after'] and all(sha(k)==v for k,v in d['frozen_artifacts'].items());root=LAB/'evaluations'/str(d['run_id']);wins=0;lost=[]
            for g in d['battles']:
                sid=int(g['scenario'].split('-')[-1]);f=root/f'{sid}-{g["role"]}-{g["seed"]}-recovered.json';l=f.with_suffix('.log');assert read(f)==g and 'VCMI shutdown complete.' in l.read_text()
                assert g['seed']==2026102600+sid*100 and g['terminated'] and not g['truncated'] and g['invalid_actions']==0 and g['terminal_outcome']['result_type']==0
                side=int(g['role']=='defender');assert g['success']==(g['terminal_outcome']['winner']==side)
                loss=sum(g['terminal_outcome']['casualties'][str(side)].values());wins+=g['success'];lost.append(loss);pairs.setdefault((opponent,sid,g['role']),{})[name]=dict(win=g['success'],lost=loss,steps=g['steps'],trajectory_sha256=g['trajectory_sha256']);raw_files+=1;paths +=[f,l]
            assert wins==d['summary'][0]['wins'] and statistics.mean(lost)==d['summary'][0]['mean_permanent_units_lost'];summaries[name+'/'+opponent]=dict(wins=wins,games=16,mean_units_lost=statistics.mean(lost));paths.append(p)
    paired=[dict(opponent=k[0],scenario=k[1],role=k[2],arms=v,win_delta=int(v['update4']['win'])-int(v['B64']['win']),loss_delta=v['update4']['lost']-v['B64']['lost'],trajectory_digest_same=v['update4']['trajectory_sha256']==v['B64']['trajectory_sha256']) for k,v in pairs.items()]
    out=dict(passed=True,new_native_games=0,GPU_operations=0,optimizer_steps_performed=0,checkpoint_CPU_reads_and_Adam_restores=checkpoints,actual_transitions=1536,normal_TRAIN_terminals=60,TRAIN_wins=46,TRAIN_truncations=0,registered_unique_cells=24,actual_cells=cells,
        unique_worker_directories_verified=24,worker_directory_evidence=worker_evidence,worker_startup_paths_present_in_log=len(boots),concurrency_evidence='12 configs/states per real rollout and 24 unique initialized worker data directories. Frozen VectorEnv starts/waits for all 12 before inference and sends all actions before receiving. Child bootstrap stdout is suppressed; no retrospective live PID measurement.',
        minimum_recorded_available_mib=min(r['free_mib'] for r in t['records']),maximum_recorded_GPU_peak_mib=max(r['gpu_peak_mib'] for r in t['records']),swap_guard='Frozen staged/update guards completed below 256MiB; no complete historical swap timeline',
        phase_close_events_independently_reconstructed=actual_close,GAE_last_step_bootstrap_checks=boundaries,TRAIN_terminal_strata={str(k):v for k,v in terminal.items()},DEV_raw_JSON_and_shutdown_verified=raw_files,DEV=summaries,pairs=paired,
        ability_improvement_claim=False,native_environment_restored=False,gradient_diagnostic_separate='GRADIENT_DIAGNOSTIC.json',input_sha256={str(p):sha(p) for p in paths},elapsed_seconds=time.monotonic()-started)
    (OUT/'AUDIT.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:out[k] for k in ['passed','actual_transitions','normal_TRAIN_terminals','TRAIN_wins','registered_unique_cells','minimum_recorded_available_mib','maximum_recorded_GPU_peak_mib','DEV','elapsed_seconds']},indent=2))
if __name__=='__main__':main()
