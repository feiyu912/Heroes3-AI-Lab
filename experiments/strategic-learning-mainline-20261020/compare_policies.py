"""Separate actual learned policy changes from the zero-step temperature intervention."""
import argparse,hashlib,json,sys,statistics
from pathlib import Path
import torch
HERE=Path(__file__).resolve().parent;TRAIN=HERE.parent/'strategic-typed-training-v1'
sys.path.insert(0,str(TRAIN))
from model_io import load_model
from load_admitted import load
from episode_balanced_ppo import collate
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--trained',type=Path,required=True);p.add_argument('--admission',type=Path,action='append',required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    torch.set_num_threads(1)
    initial=HERE/'temperature-initialization-01/temperature-2-initialization.pt';parent=TRAIN/'cuda-curriculum-ack-01/update-1.pt'
    warm,_,warmsha=load_model(initial);trained,bundle,trainedsha=load_model(a.trained);original,_,parentsha=load_model(parent)
    assert bundle['parent_checkpoint_sha256']==warmsha and bundle['complete_update_boundary'] and bundle['optimizer_steps_total']>0
    counts={'rows':0,'one_move_plus_stop':0,'multiple_moves_plus_stop':0,'sampled_end_turns':0,'learned_argmax_changes':0,'one_move_argmax_changes':0,'multiple_move_argmax_changes':0,'initial_argmax_stop':0,'trained_argmax_stop':0,'parent_temperature_argmax_changes':0}
    kls=[];stop_delta=[];details=[];proofs={str(p):sha(p) for p in (Path(__file__),a.trained,initial,parent)}
    episodes=[]
    with torch.no_grad():
        for admission in a.admission:
            rows,manifest,_=load(admission);episodes.extend(manifest);proofs[str(admission/'AUDIT.json')]=sha(admission/'AUDIT.json')
            for s in rows:
                assert s['policy_sha256']==warmsha
                q=s['request'];batch=collate([q]);x,_=warm(**batch);y,_=trained(**batch);z,_=original(**batch)
                x=x[0].double();y=y[0].double();z=z[0].double();i=int(x.argmax());j=int(y.argmax());k=int(z.argmax())
                stops=[n for n,c in enumerate(q['candidates']) if c['op']=='end_turn'];moves=[n for n,c in enumerate(q['candidates']) if c['op']=='move'];assert len(stops)==1
                one=len(moves)==1;counts['rows']+=1;counts['one_move_plus_stop' if one else 'multiple_moves_plus_stop']+=1
                counts['sampled_end_turns']+=s['action_type']=='end_turn';counts['learned_argmax_changes']+=i!=j
                counts['one_move_argmax_changes' if one else 'multiple_move_argmax_changes']+=i!=j
                counts['initial_argmax_stop']+=i==stops[0];counts['trained_argmax_stop']+=j==stops[0];counts['parent_temperature_argmax_changes']+=i!=k
                px=torch.softmax(x,0);py=torch.softmax(y,0)
                kls.append(float((px*(torch.log_softmax(x,0)-torch.log_softmax(y,0))).sum()));stop_delta.append(float(py[stops[0]]-px[stops[0]]))
                if i!=j:details.append(dict(episode_id=s['episode_id'],decision_id=s['decision_id'],day=q['day'],initial=i,trained=j,initial_op=q['candidates'][i]['op'],trained_op=q['candidates'][j]['op']))
    assert len(episodes)==8 and len({e['episode_id'] for e in episodes})==8 and counts['parent_temperature_argmax_changes']==0
    result=dict(passed=True,counts=counts,exact_full_distribution_forward_KL_mean=statistics.mean(kls),exact_full_distribution_forward_KL_max=max(kls),
        stop_probability_delta_mean=statistics.mean(stop_delta),learned_changes=details,optimizer_steps_in_saved_model=bundle['optimizer_steps_total'],
        trained_sha256=trainedsha,initial_sha256=warmsha,parent_sha256=parentsha,input_sha256=proofs,audit_optimizer_steps=0,
        ability_improvement_claim=False,scope='Actual fresh training states: learned changes and probability shifts only. Not independent ability evidence; paired DEV still required.')
    a.out.mkdir(parents=True,exist_ok=False);(a.out/'AUDIT.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k not in ('learned_changes','input_sha256')},indent=2))
if __name__=='__main__':main()
