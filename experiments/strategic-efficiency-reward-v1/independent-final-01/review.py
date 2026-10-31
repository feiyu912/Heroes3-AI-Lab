"""Independent CPU-only target/source/checkpoint/DEV evidence audit."""
import collections,copy,hashlib,importlib.util,inspect,json,re,statistics,subprocess,sys,tempfile,time
from pathlib import Path
import torch
OUT=Path(__file__).resolve().parent;HERE=OUT.parent;E=HERE.parent;LAB=Path('/root/heroes3-ai-lab');B=LAB/'evaluations/strategic-efficiency-paired-dev-01'
sys.path[:0]=[str(HERE),str(E/'strategic-typed-training-v1'),str(E/'strategic-threat-replan-v2')]
import targets
import efficiency_ppo
from model_io import load_model,tensor_sha
from load_admitted import load
from episode_balanced_ppo import collate
from causal_stability_audit_v2 import policy_action,first_difference,parse_log,movement_comparison
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def rows(p):return [json.loads(s) for s in Path(p).read_text().splitlines()]
def equal(a,b):
    if isinstance(a,torch.Tensor):return isinstance(b,torch.Tensor) and torch.equal(a.cpu(),b.cpu())
    if isinstance(a,dict):return a.keys()==b.keys() and all(equal(a[k],b[k]) for k in a)
    if isinstance(a,(list,tuple)):return len(a)==len(b) and all(equal(x,y) for x,y in zip(a,b))
    return a==b
def short_difference(a,b):
    d=first_difference(a,b)
    return None if d is None else {k:d[k] for k in ('index','off_eof','once_eof')}
def main():
    torch.set_num_threads(1);started=time.monotonic();tp=LAB/'evaluations/strategic-efficiency-targets-01'
    assert sha(tp/'TARGETS.json')=='b5fc0fba63fafc6c62513777b10ce92a5eefd4fe8b9a05b9da826746af123ce9'
    print('Starting actual CPU verify_targets over all 8 real admissions',flush=True)
    manifest=targets.verify_targets(tp);print('verify_targets passed after %.2fs'%(time.monotonic()-started),flush=True)
    cpu=read(HERE/'CPU_REPORT.json');assert cpu['passed'] and cpu['samples']==2111 and cpu['episodes']==8 and cpu['gradient_tensors']==13
    assert cpu['source_sha256']==manifest['sources'] and cpu['targets_sha256']==sha(tp/'TARGETS.json') and all(cpu['negative_cases'].values()) and len(cpu['negative_cases'])==15
    assert all(cpu[k] for k in ['control_prepare_tensors_bit_exact','control_all_minibatch_objective_exact','control_full_batch_accumulated_gradients_bit_exact'])
    spec=importlib.util.spec_from_file_location('_original_independent_efficiency',E/'strategic-typed-training-v1/episode_balanced_ppo.py');old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
    assert inspect.getsource(old.objective_terms)==inspect.getsource(efficiency_ppo.objective_terms) and inspect.getsource(old.ppo_update)==inspect.getsource(efficiency_ppo.ppo_update)
    code=(HERE/'train_efficiency.py').read_text();assert 'a.admission=[Path(p) for p in expected]' in code
    # Three independent early-gate mutations; never alter the real TARGETS.
    rejected=[]
    with tempfile.TemporaryDirectory(prefix='efficiency-independent-') as t:
        for case in ('missing_source','wrong_parent','wrong_arms'):
            m=copy.deepcopy(manifest)
            if case=='missing_source':m['sources'].pop(next(iter(m['sources'])))
            if case=='wrong_parent':m['parent_sha256']='0'*64
            if case=='wrong_arms':m['arms']={}
            Path(t,'TARGETS.json').write_text(json.dumps(m))
            try:targets.verify_targets(Path(t))
            except (ValueError,AssertionError):rejected.append(case)
            else:raise AssertionError(case+' accepted')
    paths=[Path(__file__),tp/'TARGETS.json',HERE/'CPU_REPORT.json',HERE/'matched-audit-01/AUDIT.json',HERE/'matched-audit-01/POLICY_DIFFERENCES.json'];episode_targets=[];training=[]
    for item in manifest['episodes']:
        day=item['day_evidence'];T=day['terminal_native_day']-day['first_request_day'];reward=item['native_reward'];expected=1-.05*T/(T+75) if reward==1 else -1
        assert item['targets']==dict(control=reward,treatment=expected)
        r,_,_=load(item['admission_directory']);training+=r
        episode_targets.append(dict(episode_id=item['episode_id'],native_reward=reward,first_day=day['first_request_day'],terminal_day=day['terminal_native_day'],elapsed=T,treatment=expected))
    assert len(training)==2111
    models={};bundles={};checkpoint_reports={}
    for arm in ('control','treatment'):
        root=LAB/('evaluations/strategic-efficiency-'+arm+'-update-01');model,bundle,digest=load_model(root/'update-1.pt','cpu');report=read(root/'RESULT.json');gpu_path=HERE/(arm+'-checkpoint-cuda-audit-01/AUDIT.json');gpu=read(gpu_path)
        assert report['completed_update'] and report['cuda_optimizer_steps']==132 and bundle['snapshot_device']=='cuda' and bundle['complete_update_boundary'] and bundle['optimizer_steps_total']==132
        assert bundle['parent_checkpoint_sha256']==targets.INITIAL_SHA and tensor_sha(model.state_dict())==bundle['policy_tensor_sha256'] and bundle['protocol']['derived_reward']['arm']==arm
        assert bundle['protocol']['derived_reward']['targets_sha256']==sha(tp/'TARGETS.json') and all(sha(p)==h for p,h in bundle['protocol']['sources'].items())
        assert gpu['passed_exact'] and gpu['checkpoint_sha256']==digest and gpu['optimizer_steps_restored']==132 and len(gpu['negative_cases'])==5 and gpu['audit_optimizer_steps']==0
        assert gpu['auditor_sha256']==sha(E/'strategic-typed-training-v1/audit_checkpoint_cuda.py')
        models[arm]=model;bundles[arm]=bundle;checkpoint_reports[arm]=dict(sha256=digest,optimizer_steps=132,GPU_recovery_certificate_verified=True,GPU_recovery_independently_rerun=False)
        paths += [root/'update-1.pt',root/'PLAN.json',root/'RESULT.json',gpu_path]
    ca=copy.deepcopy(bundles['control']['protocol']);cb=copy.deepcopy(bundles['treatment']['protocol']);ca['derived_reward'].pop('arm');cb['derived_reward'].pop('arm');assert ca==cb
    assert equal(bundles['control']['rng'],bundles['treatment']['rng']) and equal(bundles['control']['collection_states'],bundles['treatment']['collection_states'])
    K=[];diff=0
    with torch.no_grad():
        for row in training:
            x,_=models['control'](**collate([row['request']],'cpu'));y,_=models['treatment'](**collate([row['request']],'cpu'));x=x[0].double();y=y[0].double();diff+=int(x.argmax())!=int(y.argmax());K.append(float((x.softmax(0)*(x.log_softmax(0)-y.log_softmax(0))).sum()))
    assert diff==0
    plan=read(B/'PLAN.json');result=read(B/'RESULT.json');assert result['passed'] and len(result['pairs'])==8 and all(sha(p)==h for p,h in plan['input_sha256'].items())
    assert [j['seed'] for j in plan['jobs']]==list(range(2026102400,2026102408))
    pairs=[];proposal_replays=0;stop=0
    for i,pair in enumerate(result['pairs']):
        data={};summaries={}
        for arm,name in [('a','control'),('b','treatment')]:
            root=B/f'pair-{i:02d}'/arm;native=root/'native';out=OUT/f'pair-{i:02d}'/arm;out.mkdir(parents=True,exist_ok=False)
            subprocess.run([sys.executable,str(E/'strategic-director-terminal-drain-v4/audit_game_v6.py'),str(native),str(out/'raw-audit')],check=True,capture_output=True,text=True)
            proof=read(out/'raw-audit/AUDIT.json');assert proof==read(root/'raw-audit/AUDIT.json') and sha(root/'raw-audit/AUDIT.json')==pair['arms'][arm]['audit_sha256']
            proposals=rows(native/'agent/typed-broker.jsonl');typed=rows(native/'typed.jsonl');trace=rows(native/'strategy-trace.jsonl');np=read(native/'PLAN.json')
            assert np['decision_policy']=='model' and np['threat_replan']=='off' and sha(np['checkpoint'])==checkpoint_reports[name]['sha256']
            for p in proposals:
                with torch.no_grad():l,_=models[name](**collate([p['request']],'cpu'))
                assert int(l[0].argmax())==p['response']['selected_index'] and p['response']['classification']=='new_policy'
                proposal_replays+=1;stop+=p['response']['op']=='end_turn'
            terminal=[t for t in trace if t['event'] in ('victory','defeat')];assert len(terminal)==1
            summaries[arm]=dict(win=terminal[0]['event']=='victory',trace_terminal_day=terminal[0]['day'],policy_decisions=len(proposals),counts=proof['counts'])
            data[arm]=dict(requests=[p['request'] for p in proposals],actions=[policy_action(p) for p in proposals],steps=[dict(hero=p['request']['hero'],own_turn=p['request']['own_turn'],op=p['response']['op'],origin=p['request']['from'],next=p['request']['candidates'][p['response']['selected_index']].get('next')) for p in proposals],movements=parse_log((native/'client.log').read_text())['movements'])
            paths += [native/'PLAN.json',native/'EXECUTION.json',native/'client.log',native/'typed.jsonl',native/'strategy-trace.jsonl',native/'agent/typed-broker.jsonl',out/'raw-audit/AUDIT.json']
        a,b=data['a'],data['b'];reqdiff=short_difference(a['requests'],b['requests']);actdiff=short_difference(a['actions'],b['actions']);stepdiff=short_difference(a['steps'],b['steps'])
        assert summaries['a']['win']==summaries['b']['win'] and summaries['a']['counts']==summaries['b']['counts']
        pairs.append(dict(pair=i,job=pair['job'],arms=summaries,request_first_difference=reqdiff,semantic_action_first_difference=actdiff,step_first_difference=stepdiff,full_server_movement_projection=movement_comparison(a['movements'],b['movements'])))
        print('Independent DEV pair %d audited'%i,flush=True)
    assert stop==0
    paths += [B/'PLAN.json',B/'RESULT.json']
    out=dict(passed=True,new_native_games=0,GPU_operations=0,audit_optimizer_steps=0,target_verify_independently_rerun=True,source_closure_verified=True,three_independent_negative_cases=rejected,
        control_full_gradient_check_independently_rerun=False,control_CPU_gradient_certificate_verified=True,objective_and_PPO_loop_source_equality_independently_checked=True,
        checkpoints=checkpoint_reports,saved_RNG_and_sampling_states_equality_independently_checked_CPU=True,episode_targets=episode_targets,train_rows=len(training),train_argmax_differences=diff,train_forward_KL_mean=statistics.mean(K),
        raw_DEV_games_independently_reaudited=16,DEV_proposals_CPU_argmax_replayed=proposal_replays,DEV_argmax_end_turns=stop,baseline_wins=sum(p['arms']['a']['win'] for p in pairs),candidate_wins=sum(p['arms']['b']['win'] for p in pairs),pairs=pairs,
        ability_improvement_claim=False,input_sha256={str(p):sha(p) for p in paths},elapsed_seconds=time.monotonic()-started)
    (OUT/'AUDIT.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k not in ('input_sha256','pairs','episode_targets')},indent=2))
if __name__=='__main__':main()
