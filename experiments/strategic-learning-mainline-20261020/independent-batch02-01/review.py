"""CPU-only independent TRAIN/checkpoint provenance and behavior review."""
import collections,hashlib,json,math,statistics,subprocess,sys
from pathlib import Path
import torch
OUT=Path(__file__).resolve().parent;HERE=OUT.parent;TRAIN=HERE.parent/'strategic-typed-training-v1';PIPE=HERE/'native-pipeline'
sys.path.insert(0,str(TRAIN));sys.path.insert(0,str(PIPE))
from load_admitted import load
from model_io import load_model,tensor_sha,digest_json
from episode_balanced_ppo import collate
from pipeline_common import validate_cells,validate_native_epoch,EPOCH,INITIAL_SHA
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
B=Path('/root/heroes3-ai-lab/evaluations/strategic-mainline-temperature2-train-02')
def main():
    torch.set_num_threads(1);result=json.loads((B/'RESULT.json').read_text());plan=json.loads((B/'PLAN.json').read_text())
    assert result['passed'] and not result['ability_improvement_claim'] and len(result['episodes'])==8
    assert plan['epoch']==EPOCH and plan['checkpoint_sha256']==INITIAL_SHA
    assert [j['job']['seed'] for j in plan['jobs']]==list(range(2026102200,2026102208))
    assert all(sha(p)==h for p,h in plan['input_sha256'].items())
    checkpoint=B/'update-01/update-1.pt';trained,bundle,digest=load_model(checkpoint,'cpu');initial,_,initial_sha=load_model(plan['checkpoint'],'cpu')
    assert digest=='bb3417624bdb25023e1dbbb2e8eb49de140f2a4264c9de0444659f2b953803cc' and initial_sha==INITIAL_SHA
    assert sha(HERE/'trained-cuda-01/update-1.pt')==digest
    update=json.loads((B/'update-01/RESULT.json').read_text());protocol=bundle['protocol']
    assert update['completed_update'] and update['cuda_optimizer_steps']==172 and update['checkpoint_sha256']==digest
    assert bundle['complete_update_boundary'] and bundle['snapshot_device']=='cuda' and bundle['optimizer_steps_total']==172 and bundle['training_updates']==1
    assert bundle['parent_checkpoint_sha256']==INITIAL_SHA and tensor_sha(trained.state_dict())==bundle['policy_tensor_sha256']
    assert digest_json(protocol)==bundle['protocol_sha256'] and protocol['schema']==EPOCH
    assert all(sha(p)==h for p,h in protocol['sources'].items())
    # Inspect actual saved optimizer tensors, without creating a CUDA device or stepping it.
    optimizer=bundle['optimizer'];names=bundle['parameter_groups'];state_steps=[];stop_moment=None
    for group,n in zip(optimizer['param_groups'],names):
        assert len(group['params'])==len(n)
        for identity,name in zip(group['params'],n):
            state=optimizer['state'][identity];state_steps.append(int(state['step']))
            assert int(state['step'])==172 and torch.isfinite(state['exp_avg']).all() and torch.isfinite(state['exp_avg_sq']).all()
            if name=='actor.stop_bias':stop_moment=float(state['exp_avg']);assert stop_moment!=0
    assert len(bundle['rng']['cuda'])>=1 and len(bundle['collection_states'])==8
    delta={}
    for prefix in ('actor.','critic.'):
        pairs=[(n,p,initial.state_dict()[n]) for n,p in trained.state_dict().items() if n.startswith(prefix)]
        delta[prefix]=dict(changed_tensors=sum(not torch.equal(p,q) for _,p,q in pairs),l2=math.sqrt(sum(float(((p.double()-q.double())**2).sum()) for _,p,q in pairs)))
        assert delta[prefix]['changed_tensors']>0
    counts=collections.Counter();groups={};episode_reports=[];episodes=[];KL=[];logp_errors=[];changed=[];input_paths=[Path(__file__),B/'RESULT.json',B/'PLAN.json',B/'update-01/RESULT.json',checkpoint,HERE/'checkpoint-cuda-audit-01/AUDIT.json',HERE/'learned-policy-comparison-01/AUDIT.json']
    for i in range(8):
        cell=B/f'cell-{i:02d}';native=cell/'native';audit_dir=OUT/f'cell-{i:02d}-raw-audit'
        subprocess.run([sys.executable,str(HERE.parent/'strategic-director-terminal-drain-v4/audit_game_v6.py'),str(native),str(audit_dir)],check=True,capture_output=True,text=True)
        proof=json.loads((audit_dir/'AUDIT.json').read_text());original=json.loads((cell/'raw-audit/AUDIT.json').read_text());assert proof==original
        np=json.loads((native/'PLAN.json').read_text());ne=json.loads((native/'EXECUTION.json').read_text());validate_native_epoch(proof,np,ne)
        assert np['pipeline_epoch']==ne['pipeline_epoch']==EPOCH
        rows,manifest,admission=load(cell/'admitted');assert len(manifest)==1;ep=manifest[0];episodes+=manifest
        assert ep==result['episodes'][i] and ep['job']['seed']==2026102200+i and ep['checkpoint_sha256']==INITIAL_SHA
        assert ep['job']['opponent']==plan['jobs'][i]['job']['opponent']
        ec=collections.Counter()
        for row in rows:
            q=row['request'];moves=[k for k,c in enumerate(q['candidates']) if c['op']=='move'];stops=[k for k,c in enumerate(q['candidates']) if c['op']=='end_turn'];assert len(stops)==1
            assert len(moves)>=1
            group='one_move' if len(moves)==1 else 'multiple_moves';gc=groups.setdefault(group,collections.Counter());counts['rows']+=1;gc['rows']+=1
            with torch.no_grad():x,_=initial(**collate([q],'cpu'));y,_=trained(**collate([q],'cpu'))
            x=x[0].double();y=y[0].double();lx=x.log_softmax(0);ly=y.log_softmax(0);px=lx.exp();action=row['action'];stop=action==stops[0];diff=int(x.argmax())!=int(y.argmax())
            logp_errors.append(abs(float(lx[action])-row['old_logprob']));KL.append(float((px*(lx-ly)).sum()))
            for c in (counts,gc,ec):
                c['stops']+=stop;c['moves']+=not stop;c['non_argmax']+=action!=int(x.argmax());c['learned_argmax_changes']+=diff
            counts['initial_argmax_stop']+=int(x.argmax())==stops[0];counts['trained_argmax_stop']+=int(y.argmax())==stops[0]
            if stop:assert q['movement']>0
            if diff:changed.append(dict(episode_id=row['episode_id'],decision_id=row['decision_id'],group=group))
        trace=[json.loads(s) for s in (native/'strategy-trace.jsonl').read_text().splitlines()];terminal=[t for t in trace if t['event'] in ('victory','defeat')];assert len(terminal)==1
        assert ep['reward']==(1 if terminal[0]['event']=='victory' else -1)
        episode_reports.append(dict(cell=i,seed=ep['job']['seed'],opponent=ep['job']['opponent'],player=ep['job']['owned_player'],reward=ep['reward'],decisions=len(rows),day=terminal[0]['day'],counts=dict(ec),whole_game_valid=proof['whole_game_valid'],owned_request_count=proof['director_registry_proof']['registered_count']))
        input_paths += [cell/'admitted/AUDIT.json',cell/'raw-audit/AUDIT.json',native/'PLAN.json',native/'EXECUTION.json',audit_dir/'AUDIT.json']
    validate_cells(episodes);assert counts['rows']==2742 and counts['stops']==173 and len(changed)==13 and max(logp_errors)<1e-4
    assert groups['one_move']['rows']==2123 and groups['multiple_moves']['rows']==619 and groups['one_move']['learned_argmax_changes']==0
    assert all((e['reward']==1)==(e['opponent']=='EmptyAI') for e in episode_reports)
    gpu=json.loads((HERE/'checkpoint-cuda-audit-01/AUDIT.json').read_text());assert gpu['checkpoint_sha256']==digest and gpu['passed_exact'] and gpu['audit_optimizer_steps']==0
    assert gpu['auditor_sha256']==sha(TRAIN/'audit_checkpoint_cuda.py') and len(gpu['negative_cases'])==5
    comparison=json.loads((HERE/'learned-policy-comparison-01/AUDIT.json').read_text());assert comparison['trained_sha256']==digest and abs(statistics.mean(KL)-comparison['exact_full_distribution_forward_KL_mean'])<1e-10
    out=dict(passed=True,scope='Independent CPU read-only TRAIN/source/raw/serialized-state review; no new CUDA/native run',new_native_games=0,GPU_operations=0,audit_optimizer_steps=0,
        checkpoint_sha256=digest,optimizer_steps_in_saved_checkpoint=172,saved_Adam_step_range=[min(state_steps),max(state_steps)],saved_stop_exp_avg=stop_moment,parameter_deltas=delta,
        exact_CUDA_recovery_report_verified=True,exact_CUDA_recovery_independently_rerun=False,raw_audits_independently_rerun=8,counts=dict(counts),groups={k:dict(v) for k,v in groups.items()},
        CPU_archived_logprob_max_error=max(logp_errors),full_distribution_KL_mean=statistics.mean(KL),learned_changes=changed,episodes=episode_reports,
        ability_improvement_claim=False,invalid_previous_batch_preserved=True,input_sha256={str(p):sha(p) for p in input_paths})
    (OUT/'AUDIT.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:out[k] for k in ['passed','checkpoint_sha256','counts','groups','full_distribution_KL_mean']}))
if __name__=='__main__':main()
