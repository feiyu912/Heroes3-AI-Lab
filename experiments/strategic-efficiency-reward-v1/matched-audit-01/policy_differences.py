"""Full-distribution and goal-choice comparison on the shared TRAIN observations."""
import hashlib,json,sys,statistics
from pathlib import Path
import torch
HERE=Path(__file__).resolve().parent;BASE=HERE.parent.parent/'strategic-typed-training-v1';sys.path.insert(0,str(BASE))
from model_io import load_model
from load_admitted import load
from episode_balanced_ppo import collate
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    torch.set_num_threads(1);root=Path('/root/heroes3-ai-lab/evaluations')
    models=[load_model(root/f'strategic-efficiency-{arm}-update-01/update-1.pt')[0] for arm in ('control','treatment')]
    changes=[];kls=[];stop_deltas=[];n=0;stops=[0,0];inputs={str(Path(__file__)):sha(__file__)}
    with torch.no_grad():
        for cell in range(8):
            admission=root/f'strategic-efficiency-shared-train-01/cell-{cell:02d}/admitted';rows,_,_=load(admission);inputs[str(admission/'AUDIT.json')]=sha(admission/'AUDIT.json')
            for sample in rows:
                request=sample['request'];batch=collate([request]);logits=[m(**batch)[0][0].double() for m in models]
                choices=[int(x.argmax()) for x in logits];stop=next(i for i,c in enumerate(request['candidates']) if c['op']=='end_turn')
                ps=[torch.softmax(x,0) for x in logits];logs=[torch.log_softmax(x,0) for x in logits]
                kls.append(float((ps[0]*(logs[0]-logs[1])).sum()));stop_deltas.append(float(ps[1][stop]-ps[0][stop]));n+=1
                for arm in range(2):stops[arm]+=choices[arm]==stop
                if choices[0]!=choices[1]:changes.append({'cell':cell,'decision_id':sample['decision_id'],'day':request['day'],'choices':choices,'candidates':[request['candidates'][c] for c in choices]})
    assert n==2111
    report={'passed':True,'TRAIN_rows':n,'different_argmax':len(changes),'argmax_stop_control_treatment':stops,
        'full_distribution_KL_control_to_treatment_mean':statistics.mean(kls),'full_distribution_KL_max':max(kls),'stop_probability_delta_mean':statistics.mean(stop_deltas),
        'changes':changes,'input_sha256':inputs,'new_games':0,'optimizer_steps':0,'ability_improvement_claim':False,
        'scope':'CPU singleton inference on shared TRAIN states only. Tensor changes do not guarantee strategic choice changes or independent improvement.'}
    out=HERE/'POLICY_DIFFERENCES.json';assert not out.exists();out.write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k not in ('changes','input_sha256')},indent=2))
if __name__=='__main__':main()
