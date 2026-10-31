"""Read-only comparison on actual admitted TRAIN observations; not an evaluation."""
import argparse,collections,hashlib,json,math,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;POLICY=HERE.parent
sys.path.insert(0,str(POLICY))
import torch
from encoder import collate
from model_io import load_model,tensor_sha
from load_admitted import load
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--training',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=False);torch.set_num_threads(1)
    initial=POLICY.parent/'strategic-learned-build-exploration-v1/calibration-01/build-offset-initialization.pt';trained=a.training/'update-01/update-1.pt'
    before,_,isha=load_model(initial,'cpu');after,bundle,tsha=load_model(trained,'cpu')
    assert isha=='40eccc511fbc61b84b86e75b5aec102781835f2574db809f9a698f9a81db6d97'
    assert tsha=='d27d282bbcdaf1f1bf47f13b4b44c40ee1cd82639bedd47db90da5fd6c0da1d2'
    updates=json.loads((a.training/'update-01/RESULT.json').read_text());assert updates['completed_update']
    rows=[];changes=[];builds=[];windows=[];episodes=[];income=[];candidate_counts=collections.Counter();frozen={}
    inputs={str(initial):sha(initial),str(trained):sha(trained),str(a.training/'RESULT.json'):sha(a.training/'RESULT.json')}
    for f,h in bundle['protocol']['sources'].items():assert sha(f)==h;frozen[f]=h
    with torch.no_grad():
        for cell in sorted(a.training.glob('cell-*')):
            samples,manifest,admission=load(cell/'admitted');episodes.extend(manifest)
            plan=json.loads((cell/'native/PLAN.json').read_text());raw_audit=json.loads((cell/'raw-audit/AUDIT.json').read_text())
            for name,h in raw_audit['raw_sha256'].items():
                path=str(cell/'native'/name);assert sha(path)==h;frozen[path]=h
            for name,h in plan['hashes'].items():
                if name not in frozen:assert sha(name)==h
                else:assert frozen[name]==h
                frozen[name]=h
            inputs[str(cell/'admitted/AUDIT.json')]=sha(cell/'admitted/AUDIT.json')
            for sample in samples:
                request=sample['request'];batch=collate([request]);l0,v0=before(**batch);l1,v1=after(**batch)
                l0=l0[0];l1=l1[0];p0=l0.softmax(-1);p1=l1.softmax(-1);idx0=int(l0.argmax());idx1=int(l1.argmax());action=sample['action']
                buildidx=[i for i,c in enumerate(request['candidates']) if c['op']=='build']
                incomeidx=[i for i in buildidx if request['candidates'][i]['category']=='income']
                candidate_counts.update(request['candidates'][i]['category'] for i in buildidx)
                if incomeidx:
                    income.append(dict(cell=cell.name,decision_id=sample['decision_id'],
                        candidates=[request['candidates'][i] for i in incomeidx],
                        initial_income_mass=float(p0[incomeidx].sum()),trained_income_mass=float(p1[incomeidx].sum())))
                row=dict(cell=cell.name,decision_id=sample['decision_id'],day=request['day'],own_turn=request['own_turn'],
                    candidate_count=len(request['candidates']),build_candidates=len(buildidx),economy_window_open=request['economy_window_open'],
                    initial_argmax=idx0,trained_argmax=idx1,initial_argmax_op=request['candidates'][idx0]['op'],trained_argmax_op=request['candidates'][idx1]['op'],
                    actual_sampled_op=sample['action_type'],initial_build_probability=float(p0[buildidx].sum()) if buildidx else 0.,
                    trained_build_probability=float(p1[buildidx].sum()) if buildidx else 0.,
                    total_variation=float((p0-p1).abs().sum()/2),forward_kl=float((p0*(l0.log_softmax(-1)-l1.log_softmax(-1))).sum()),
                    value_delta=float(v1[0]-v0[0]))
                rows.append(row)
                if idx0!=idx1:changes.append(row)
                if buildidx:windows.append(row)
                if sample['action_type']=='build':
                    c=request['candidates'][action]
                    builds.append(dict(cell=cell.name,decision_id=sample['decision_id'],native_request_id=sample['native_request_id'],
                        day=request['day'],own_turn=request['own_turn'],town_id=c['town_id'],building_id=c['building_id'],category=c['category'],cost=c['cost'],
                        sampled_action_index=action,sampling_GPU_probability=math.exp(sample['old_logprob']),
                        initial_CPU_probability=float(p0[action]),trained_CPU_probability=float(p1[action]),
                        initial_build_mass=row['initial_build_probability'],trained_build_mass=row['trained_build_probability'],
                        initial_argmax_build=idx0==action,trained_argmax_build=idx1==action,native_certified=True,terminal_training_return=sample['return']))
    assert len(rows)==1891 and len(builds)==28
    weights=[]
    for name,x in before.state_dict().items():
        y=after.state_dict()[name];delta=y.double()-x.double();weights.append(dict(name=name,l2=float(delta.square().sum().sqrt()),max_abs=float(delta.abs().max()),changed=bool(delta.ne(0).any())))
    mean=lambda values:sum(values)/len(values) if values else None
    report=dict(passed=True,CPU_read_only=True,optimizer_steps_in_audit=0,new_native_games=0,
        training_only_not_independent_evaluation=True,ability_improvement_claim=False,
        initial_checkpoint_sha256=isha,trained_checkpoint_sha256=tsha,episodes=len(episodes),states=len(rows),actual_policy_builds=len(builds),
        training_wins=sum(e['reward']==1 for e in episodes),training_losses=sum(e['reward']==-1 for e in episodes),
        actual_build_categories=dict(collections.Counter(b['category'] for b in builds)),
        actual_builds_by_cell=dict(collections.Counter(b['cell'] for b in builds)),
        argmax_changes=len(changes),argmax_changes_with_build_candidates=sum(r['build_candidates']>0 for r in changes),
        initial_argmax_ops=dict(collections.Counter(r['initial_argmax_op'] for r in rows)),
        trained_argmax_ops=dict(collections.Counter(r['trained_argmax_op'] for r in rows)),
        income_candidate_states=len(income),income_candidate_occurrences=sum(len(i['candidates']) for i in income),
        actual_build_candidate_categories=dict(candidate_counts),
        argmax_op_transitions=dict(collections.Counter(r['initial_argmax_op']+'->'+r['trained_argmax_op'] for r in changes)),
        mean_total_variation=mean([r['total_variation'] for r in rows]),mean_forward_kl=mean([r['forward_kl'] for r in rows]),
        max_abs_value_delta=max(abs(r['value_delta']) for r in rows),
        actual_build_candidate_states=len(windows),initial_mean_build_mass_on_available_states=mean([r['initial_build_probability'] for r in windows]),
        trained_mean_build_mass_on_available_states=mean([r['trained_build_probability'] for r in windows]),
        actual_28builds_mean_probability_before=mean([b['initial_CPU_probability'] for b in builds]),
        actual_28builds_mean_probability_after=mean([b['trained_CPU_probability'] for b in builds]),
        weights=weights,input_sha256=inputs,auditor_sha256=sha(Path(__file__)),
        raw_and_source_freeze_count=len(frozen),all_original_raw_source_runtime_inputs_rehashed=True,
        fresh_epoch_optimizer_steps=bundle['optimizer_steps_total'],ancestor_optimizer_steps_not_continuous=188,
        optimizer_reset_at_calibrated_initialization=True,build_bias_before=float(before.actor.build_bias.detach()),
        build_bias_after=float(after.actor.build_bias.detach()),
        limitation='Same collected TRAIN states, not counterfactual trajectories or DEV. Shared actor changes movement and building probabilities together; no isolated economic benefit or general strength claim.')
    assert bundle['optimizer_steps_total']==120 and bundle['training_updates']==1
    assert all(sha(p)==h for p,h in frozen.items())
    for name,data in [('ARGMAX_CHANGES.json',changes),('ACTUAL_BUILD_SAMPLES.json',builds),('AUDIT.json',report),('INCOME_CANDIDATES.json',income),('FROZEN_INPUT_RECHECK.json',frozen)]:
        (a.out/name).write_text(json.dumps(data,indent=2)+'\n')
    (a.out/'STATE_METRICS.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    print(json.dumps({k:v for k,v in report.items() if k not in ('weights','input_sha256')},indent=2))
if __name__=='__main__':main()

