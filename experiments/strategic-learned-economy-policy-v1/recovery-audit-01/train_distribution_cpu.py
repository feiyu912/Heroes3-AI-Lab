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
    initial=POLICY/'cpu-01/build-initialization.pt';trained=a.training/'update-01/update-1.pt'
    before,_,isha=load_model(initial,'cpu');after,bundle,tsha=load_model(trained,'cpu')
    assert tsha=='34a6a86ea74d727338388db74e0ab3b9e16ec85e45ef46313757b1ac814538bc'
    updates=json.loads((a.training/'update-01/RESULT.json').read_text());assert updates['completed_update']
    rows=[];changes=[];builds=[];windows=[];episodes=[];inputs={str(initial):sha(initial),str(trained):sha(trained),str(a.training/'RESULT.json'):sha(a.training/'RESULT.json')}
    with torch.no_grad():
        for cell in sorted(a.training.glob('cell-*')):
            samples,manifest,admission=load(cell/'admitted');episodes.extend(manifest)
            inputs[str(cell/'admitted/AUDIT.json')]=sha(cell/'admitted/AUDIT.json')
            for sample in samples:
                request=sample['request'];batch=collate([request]);l0,v0=before(**batch);l1,v1=after(**batch)
                l0=l0[0];l1=l1[0];p0=l0.softmax(-1);p1=l1.softmax(-1);idx0=int(l0.argmax());idx1=int(l1.argmax());action=sample['action']
                buildidx=[i for i,c in enumerate(request['candidates']) if c['op']=='build']
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
    assert len(rows)==3000 and len(builds)==19
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
        argmax_op_transitions=dict(collections.Counter(r['initial_argmax_op']+'->'+r['trained_argmax_op'] for r in changes)),
        mean_total_variation=mean([r['total_variation'] for r in rows]),mean_forward_kl=mean([r['forward_kl'] for r in rows]),
        max_abs_value_delta=max(abs(r['value_delta']) for r in rows),
        actual_build_candidate_states=len(windows),initial_mean_build_mass_on_available_states=mean([r['initial_build_probability'] for r in windows]),
        trained_mean_build_mass_on_available_states=mean([r['trained_build_probability'] for r in windows]),
        actual_19builds_mean_probability_before=mean([b['initial_CPU_probability'] for b in builds]),
        actual_19builds_mean_probability_after=mean([b['trained_CPU_probability'] for b in builds]),
        weights=weights,input_sha256=inputs,auditor_sha256=sha(Path(__file__)),
        limitation='Same collected TRAIN states, not counterfactual trajectories or DEV. Shared actor changes movement and building probabilities together; no isolated economic benefit or general strength claim.')
    for name,data in [('ARGMAX_CHANGES.json',changes),('ACTUAL_BUILD_SAMPLES.json',builds),('AUDIT.json',report)]:
        (a.out/name).write_text(json.dumps(data,indent=2)+'\n')
    (a.out/'STATE_METRICS.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    print(json.dumps({k:v for k,v in report.items() if k not in ('weights','input_sha256')},indent=2))
if __name__=='__main__':main()
