"""Explicit weights-only exploration intervention, never a gradient update/resume."""
import hashlib,json,sys
from pathlib import Path
import torch
HERE=Path(__file__).resolve().parent;TRAIN=HERE.parent/'strategic-typed-training-v1'
sys.path.insert(0,str(TRAIN))
from model_io import load_model,architecture,tensor_sha
from load_admitted import load
from episode_balanced_ppo import collate
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    torch.set_num_threads(1)
    decision=json.loads((HERE/'train-exploration-audit-01/AUDIT.json').read_text())
    assert decision['passed'] and decision['chosen_temperature']==2
    assert all(sha(p)==h for p,h in decision['input_sha256'].items())
    parent=TRAIN/'cuda-curriculum-ack-01/update-1.pt';model,bundle,digest=load_model(parent,'cpu')
    before={k:v.detach().clone() for k,v in model.state_dict().items()}
    with torch.no_grad():
        model.actor[-1].weight.div_(2);model.actor[-1].bias.div_(2)
        model.actor.stop_bias.div_(2);model.prior_scale.div_(2)
    changed={k for k,v in model.state_dict().items() if not torch.equal(v,before[k])}
    assert changed=={'prior_scale','actor.4.weight','actor.4.bias','actor.stop_bias'}
    assert all(torch.equal(v,before[k]) for k,v in model.state_dict().items() if k.startswith('critic.'))
    lineage={'reset_optimizer':True,'reset_rng':True,'discard_rollout':True,'weights_only':True,
        'parent_checkpoint_sha256':digest,'parent_training_updates':bundle['training_updates'],
        'parent_optimizer_steps_total':bundle['optimizer_steps_total'],'initialization_intervention':'all actor logits divided by2; critic unchanged',
        'temperature':2,'new_gradient_steps':0,'ability_improvement_claim':False,'audit_sha256':sha(HERE/'train-exploration-audit-01/AUDIT.json')}
    out=HERE/'temperature-initialization-01';out.mkdir(exist_ok=False)
    checkpoint=out/'temperature-2-initialization.pt'
    architecture.atomic_torch_save(architecture.weights_bundle(model,lineage),checkpoint)
    loaded,_,newsha=load_model(checkpoint,'cpu');original,_,_=load_model(parent,'cpu')
    assert tensor_sha(loaded.state_dict())==tensor_sha(model.state_dict())
    max_error=0.;rows_checked=0;value_max_error=0.
    sealed=json.loads((TRAIN/'balanced-ack-certified-01/RESULT.json').read_text())
    with torch.no_grad():
        for entry in sealed['episodes']:
            rows,_,_=load(entry['admission'])
            for s in rows:
                batch=collate([s['request']],'cpu');a,v=original(**batch);b,w=loaded(**batch)
                assert a.argmax(-1).item()==b.argmax(-1).item()
                max_error=max(max_error,float((a/2-b).abs().max()))
                value_max_error=max(value_max_error,float((v-w).abs().max()));rows_checked+=1
    assert max_error<1e-5 and value_max_error==0 and rows_checked==2588
    report={'passed':True,'checkpoint':str(checkpoint),'checkpoint_sha256':newsha,'parent_sha256':digest,
        'rows_checked':rows_checked,'max_logit_temperature_error':max_error,'critic_value_max_error':value_max_error,
        'argmax_unchanged_on_all_train_states':True,'changed_state_keys':sorted(changed),'new_gradient_steps':0,
        'explicit_optimizer_rng_reset_required':True,'ability_improvement_claim':False,'lineage':lineage,
        'input_sha256':{str(p):sha(p) for p in (Path(__file__),HERE/'PLAN.md',HERE/'train-exploration-audit-01/AUDIT.json',parent)}}
    (out/'AUDIT.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if __name__=='__main__':main()
