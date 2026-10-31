"""Precommitted TRAIN-only logit-offset calibration; no optimizer or new rollout."""
import argparse,collections,copy,hashlib,importlib.util,json,math,sys
from pathlib import Path
import torch
import model,model_io
HERE=Path(__file__).resolve().parent;POLICY=HERE.parent/'strategic-learned-economy-policy-v1'
PARENT=Path('/root/heroes3-ai-lab/evaluations/strategic-learned-build-training-01/update-01/update-1.pt')
PARENT_SHA='34a6a86ea74d727338388db74e0ab3b9e16ec85e45ef46313757b1ac814538bc'
TRAIN=PARENT.parent.parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def summary(values):
    v=torch.tensor(values,dtype=torch.float64)
    return dict(n=len(values),mean=float(v.mean()),minimum=float(v.min()),median=float(v.quantile(.5)),
        p90=float(v.quantile(.9)),p95=float(v.quantile(.95)),p99=float(v.quantile(.99)),maximum=float(v.max()),
        above_half=int((v>.5).sum()),above_nine_tenths=int((v>.9).sum()))

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    torch.set_num_threads(1);old,bundle,digest=model_io.parent_io.load_model(PARENT,'cpu');assert digest==PARENT_SHA
    assert all(sha(f)==h for f,h in bundle['protocol']['sources'].items())
    with torch.random.fork_rng(devices=[]):new=model.PriorCandidateActorCritic(old.hidden,**bundle['prior_config'],build_bias=0.)
    state=copy.deepcopy(old.state_dict());state['actor.build_bias']=torch.tensor(0.);new.load_state_dict(state,strict=True)
    sys.path.append(str(POLICY));spec=importlib.util.spec_from_file_location('_calibration_admitted',POLICY/'load_admitted.py')
    admission_io=importlib.util.module_from_spec(spec);spec.loader.exec_module(admission_io)
    dataset=[];sources={str(PARENT):digest,str(HERE/'PLAN.md'):sha(HERE/'PLAN.md')};selected_builds=[];candidate_types=collections.Counter();income_examples=[]
    exact_logits=True;exact_values=True
    with torch.no_grad():
        for cell in sorted(TRAIN.glob('cell-*')):
            samples,_,_=admission_io.load(cell/'admitted');sources[str(cell/'admitted/AUDIT.json')]=sha(cell/'admitted/AUDIT.json')
            for sample in samples:
                q=sample['request'];batch=model.encoder.collate([q]);before,bv=old(**batch);after,av=new(**batch)
                exact_logits &= torch.equal(before,after);exact_values &= torch.equal(bv,av)
                logits=before[0];bits=torch.tensor([c['op']=='build' for c in q['candidates']]);income=torch.tensor([c['op']=='build' and c['category']=='income' for c in q['candidates']])
                data=dict(cell=cell.name,decision=sample['decision_id'],request=q,logits=logits,build=bits,income=income,sample=sample)
                dataset.append(data)
                for c in q['candidates']:
                    if c['op']=='build':candidate_types[c['category']]+=1
                if sample['action_type']=='build':selected_builds.append(dict(cell=cell.name,decision=sample['decision_id'],category=q['candidates'][sample['action']]['category']))
                if bool(income.any()):
                    probs=logits.softmax(-1)
                    for i in income.nonzero().flatten().tolist():income_examples.append(dict(cell=cell.name,decision=sample['decision_id'],day=q['day'],candidate=q['candidates'][i],parent_probability=float(probs[i])))
    assert len(dataset)==3000 and exact_logits and exact_values
    eligible=[d for d in dataset if bool(d['build'].any())];assert len(eligible)==400
    results=[];details={}
    for bias in [0.,.5,1.,1.5,2.,3.,4.]:
        masses=[];incomemasses=[];kl=[];rkl=[];tv=[];argbuild=0;argincome=0;nb_error=0.;income_records=[]
        for d in eligible:
            logits=d['logits'];newlogits=logits+bias*d['build'].to(logits.dtype)
            p0=logits.softmax(-1);p1=newlogits.softmax(-1);nb=~d['build']
            nb_error=max(nb_error,float((logits[nb].softmax(-1)-newlogits[nb].softmax(-1)).abs().max()))
            masses.append(float(p1[d['build']].sum()));incomemasses.append(float(p1[d['income']].sum()))
            kl.append(float((p0*(logits.log_softmax(-1)-newlogits.log_softmax(-1))).sum()))
            rkl.append(float((p1*(newlogits.log_softmax(-1)-logits.log_softmax(-1))).sum()))
            tv.append(float((p1-p0).abs().sum()/2));arg=int(newlogits.argmax());argbuild+=bool(d['build'][arg]);argincome+=bool(d['income'][arg])
            if bool(d['income'].any()):income_records.append(dict(cell=d['cell'],decision=d['decision'],income_mass=float(p1[d['income']].sum())))
        results.append(dict(bias=bias,build_probability=summary(masses),income_mass_on_all_eligible_states=summary(incomemasses),
            forward_KL_eligible=summary(kl),reverse_KL_eligible=summary(rkl),total_variation_eligible=summary(tv),
            forward_KL_all3000_mean=sum(kl)/3000,conditional_nonbuild_distribution_max_error=nb_error,
            conditional_Move_EndTurn_odds_unchanged=nb_error==0.,argmax_build_on400=argbuild,argmax_income_on400=argincome))
        details[bias]=income_records
    first=next((r for r in results if r['bias']>0 and r['build_probability']['mean']>=.1),None)
    chosen=first['bias'] if first and first['build_probability']['mean']<=.2 else None
    # Only the independent scalar shifts build logits; no move/stop/value dependence.
    probe=next(d for d in eligible if any(c['op']=='move' for c in d['request']['candidates']))
    logits,value=new(**model.encoder.collate([probe['request']]))
    moveidx=next(i for i,c in enumerate(probe['request']['candidates']) if c['op']=='move');buildidx=next(i for i,c in enumerate(probe['request']['candidates']) if c['op']=='build')
    move_grad=torch.autograd.grad(logits[0,moveidx],new.actor.build_bias,retain_graph=True)[0]
    build_grad=torch.autograd.grad(logits[0,buildidx],new.actor.build_bias,retain_graph=True)[0]
    value_grad=torch.autograd.grad(value[0],new.actor.build_bias,allow_unused=True)[0]
    assert float(move_grad)==0. and float(build_grad)==1. and value_grad is None
    checkpoint_sha=None
    if chosen is not None:
        with torch.no_grad():new.actor.build_bias.fill_(chosen)
        lineage=dict(reset_optimizer=True,reset_rng=True,discard_rollout=True,weights_only=True,new_gradient_steps=0,
            parent_checkpoint_sha256=digest,parent_actual_optimizer_steps=bundle['optimizer_steps_total'],new_epoch=model.EPOCH,
            calibration_train_only=True,calibration_states=3000,calibration_eligible_states=400,calibration_plan_sha256=sha(HERE/'PLAN.md'),
            added_parameter='actor.build_bias',chosen_bias=chosen,not_an_ability_improvement=True)
        newbundle=dict(format=model_io.FORMAT,schema=model.encoder.SCHEMA,encoder_version=model.ENCODER_VERSION,architecture_version=model.ARCHITECTURE_VERSION,
            state_dim=35,candidate_dim=43,hidden=new.hidden,prior_config=dict(bundle['prior_config'],build_bias=chosen),
            state_dict=model_io.parent_io.cpu_tree(new.state_dict()),lineage=lineage,policy_tensor_sha256=model_io.tensor_sha(new.state_dict()))
        checkpoint=a.out/'build-offset-initialization.pt';checkpoint_sha=model_io.save_initialization(newbundle,checkpoint)
        loaded,_,loadedsha=model_io.load_model(checkpoint);assert loadedsha==checkpoint_sha and model_io.tensor_sha(loaded.state_dict())==model_io.tensor_sha(new.state_dict())
    report=dict(passed=True,CPU_only=True,native_games=0,optimizer_steps=0,gradient_updates=0,ability_improvement_claim=False,
        parent_sha256=digest,parent_actual_optimizer_steps=bundle['optimizer_steps_total'],zero_offset_logits_exact_all3000=exact_logits,
        zero_offset_critic_exact_all3000=exact_values,new_parameter_derivatives=dict(move=float(move_grad),build=float(build_grad),critic=None),
        actual_train_states=3000,actual_eligible_states=400,actual_build_candidates_by_category=dict(candidate_types),
        actual_sampled_build_categories=dict(collections.Counter(d['category'] for d in selected_builds)),
        income_legal_candidate_occurrences=len(income_examples),income_eligible_states=sum(bool(d['income'].any()) for d in eligible),
        candidate_results=results,chosen_bias=chosen,chosen_checkpoint_sha256=checkpoint_sha,
        new_epoch=model.EPOCH,source_sha256={p.name:sha(p) for p in HERE.glob('*.py')},input_sha256=sources,
        limitation='TRAIN-only deterministic logit calibration, not gradient learning or independent ability improvement. New on-policy sampling and source/epoch-qualified training are mandatory.')
    for name,data in [('AUDIT.json',report),('INCOME_CANDIDATES.json',income_examples),('CHOSEN_INCOME_MASS.json',details.get(chosen,[]))]:
        (a.out/name).write_text(json.dumps(data,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('candidate_results','input_sha256','source_sha256')},indent=2))
    print(json.dumps([dict(bias=r['bias'],meanP=r['build_probability']['mean'],argmax_build=r['argmax_build_on400'],argmax_income=r['argmax_income_on400'],KL=r['forward_KL_eligible']['mean']) for r in results],indent=2))
if __name__=='__main__':main()
