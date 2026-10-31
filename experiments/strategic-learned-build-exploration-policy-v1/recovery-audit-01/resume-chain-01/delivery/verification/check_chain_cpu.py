"""One bounded read-only inspection of fully published continuation updates. No polling."""
import argparse,collections,hashlib,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;POLICY=HERE.parent.parent
RUN=POLICY.parent/'strategic-learned-build-exploration-run-v1'
sys.path.insert(0,str(RUN));sys.path.insert(0,str(POLICY))
import torch
from model_io import read,load_model,tensor_sha
from load_admitted import load
from pipeline_common import validate_cells
BASE=Path('/root/heroes3-ai-lab/evaluations/strategic-learned-build-exploration-train-01/update-01/update-1.pt')
BASE_SHA='d27d282bbcdaf1f1bf47f13b4b44c40ee1cd82639bedd47db90da5fd6c0da1d2'
ROOT=Path('/root/heroes3-ai-lab/evaluations/strategic-build-exploration-continuation-01')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def parameter_steps(bundle):
    steps={};moments={}
    for names,group in zip(bundle['parameter_groups'],bundle['optimizer']['param_groups']):
        for name,identity in zip(names,group['params']):
            entry=bundle['optimizer']['state'].get(identity)
            steps[name]=int(entry['step']) if entry else 0
            if entry:
                moments[name]=dict(step=steps[name],exp_avg_l2=float(entry['exp_avg'].double().square().sum().sqrt()),
                    exp_avg_sq_l2=float(entry['exp_avg_sq'].double().square().sum().sqrt()))
    return steps,moments

def published_result(path):
    if not path.is_file():return None
    first=path.read_bytes()
    try:value=json.loads(first)
    except json.JSONDecodeError:return None
    if first!=path.read_bytes():return None
    return value

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=ROOT);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=False);torch.set_num_threads(1)
    parent,psha=read(BASE);assert psha==BASE_SHA and parent['optimizer_steps_total']==120 and parent['training_updates']==1
    protocol_sha=parent['protocol_sha256'];reports=[];not_complete=[];rehashed={}
    plan=published_result(a.root/'PLAN.json');assert plan and plan['parent_sha256']==BASE_SHA and plan['optimizer_reset'] is False
    for f,h in plan['input_sha256'].items():assert sha(f)==h;rehashed[f]=h
    for update in (2,3,4):
        root=a.root/f'round-{update:02d}';result=published_result(root/'update/RESULT.json')
        if result is None:
            not_complete.append(dict(target_update=update,state='No stable complete update RESULT published at inspection; no process status inferred'))
            break
        assert result.get('completed_update') is True,'A published failed/partial training result cannot be audited as complete'
        path=Path(result['checkpoint']);current,digest=read(path)
        assert digest==result['checkpoint_sha256'] and current['parent_checkpoint_sha256']==psha
        assert current['protocol_sha256']==protocol_sha and current['protocol']==parent['protocol']
        assert current['lineage']['explicit_optimizer_reset'] is False and current['complete_update_boundary'] is True
        assert current['training_updates']==update and result['training_updates']==update
        delta=current['optimizer_steps_total']-parent['optimizer_steps_total']
        assert delta==result['cuda_optimizer_steps'] and delta>0
        assert current['optimizer_steps_total']==result['optimizer_steps_total']
        oldsteps,_=parameter_steps(parent);steps,moments=parameter_steps(current)
        assert steps.keys()==oldsteps.keys() and current['parameter_groups']==parent['parameter_groups']
        assert all(steps[n]>=oldsteps[n] for n in steps)
        assert steps['actor.build_bias']>oldsteps['actor.build_bias'] and steps['actor.stop_bias']>oldsteps['actor.stop_bias']
        assert max(steps.values())==current['optimizer_steps_total']
        samples=[];episodes=[];builds=[];candidate_categories=collections.Counter();build_categories=collections.Counter();cells=[]
        for index in range(8):
            cell=root/f'cell-{index:02d}';rows,manifest,admission=load(cell/'admitted')
            assert len(manifest)==1;episode=manifest[0];episodes.append(episode);samples.extend(rows)
            assert episode['checkpoint_sha256']==psha and episode['job']['logical_update']==update-1
            assert episode['job']['seed']==2026103000+(update-2)*100+index
            assert all(s['policy_sha256']==psha for s in rows)
            raw=json.loads((cell/'raw-audit/AUDIT.json').read_text());collection=json.loads((cell/'native/PLAN.json').read_text())
            for name,h in raw['raw_sha256'].items():
                f=str(cell/'native'/name);assert sha(f)==h;rehashed[f]=h
            for f,h in collection['hashes'].items():
                if f not in rehashed:assert sha(f)==h
                else:assert rehashed[f]==h
                rehashed[f]=h
            selected=collections.Counter()
            for row in rows:
                q=row['request']
                candidate_categories.update(c['category'] for c in q['candidates'] if c['op']=='build')
                if row['action_type']=='build':
                    c=q['candidates'][row['action']];build_categories[c['category']]+=1;selected[c['category']]+=1
                    builds.append(dict(cell=cell.name,decision_id=row['decision_id'],native_request_id=row['native_request_id'],day=q['day'],
                        town_id=c['town_id'],building_id=c['building_id'],category=c['category'],cost=c['cost']))
            cells.append(dict(cell=index,rows=len(rows),builds=dict(selected),reward=episode['reward'],job=episode['job']))
        validate_cells(episodes)
        assert len(samples)==result['samples'] and len(builds)==result['policy_builds']
        cpu_model,loaded,loaded_sha=load_model(path,'cpu')
        assert loaded_sha==digest and tensor_sha(cpu_model.state_dict())==current['policy_tensor_sha256']
        assert all(v.device.type=='cpu' for v in cpu_model.state_dict().values())
        assert float(cpu_model.actor.build_bias.detach())==current['prior_config']['build_bias']
        report=dict(update=update,parent_sha256=psha,checkpoint_sha256=digest,protocol_sha256=protocol_sha,
            explicit_optimizer_reset=False,new_CUDA_optimizer_steps=delta,cumulative_same_optimizer_steps=current['optimizer_steps_total'],
            parameter_step_increments={n:steps[n]-oldsteps[n] for n in steps},parameter_moments=moments,
            samples=len(samples),policy_builds=len(builds),actual_build_categories=dict(build_categories),candidate_categories=dict(candidate_categories),
            training_wins=sum(e['reward']==1 for e in episodes),training_losses=sum(e['reward']==-1 for e in episodes),
            build_bias=float(cpu_model.actor.build_bias.detach()),CPU_model_load_exact=True,cells=cells,builds=builds)
        reports.append(report);parent=current;psha=digest
    assert all(sha(f)==h for f,h in rehashed.items())
    final=dict(passed_completed_prefix=True,CPU_read_only=True,no_polling=True,audit_optimizer_steps=0,new_native_games=0,
        inspected_complete_updates=reports,not_yet_complete=not_complete,all3_updates_completed_and_verified=len(reports)==3,
        fixed_parent_sha256=BASE_SHA,protocol_sha256=protocol_sha,raw_source_runtime_hashes_rechecked=len(rehashed),
        cumulative_steps_last_verified=parent['optimizer_steps_total'],ancestor188_not_in_this_optimizer_epoch=True,
        controller_explicitly_external_to_original_checkpoint_protocol=True,ability_improvement_claim=False,
        auditor_sha256=sha(Path(__file__)),limitation='CPU saved-state/parent/source/native-admission audit only. No new CUDA restoration or continuous-vs-split equivalence claim; independent DEV remains separate.')
    (a.out/'AUDIT.json').write_text(json.dumps(final,indent=2)+'\n')
    (a.out/'INPUT_RECHECK.json').write_text(json.dumps(rehashed,indent=2)+'\n')
    print(json.dumps({k:v for k,v in final.items() if k!='inspected_complete_updates'},indent=2))
    for report in reports:print(json.dumps({k:v for k,v in report.items() if k not in ('parameter_step_increments','parameter_moments','cells','builds')},indent=2))
if __name__=='__main__':main()
