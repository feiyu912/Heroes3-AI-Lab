"""Same-architecture exact weights migration; no native qualification or optimizer update."""
import argparse,copy,hashlib,importlib.util,json,sys
from pathlib import Path
import torch
import model_io
HERE=Path(__file__).resolve().parent
PARENT=Path('/root/heroes3-ai-lab/evaluations/strategic-build-exploration-continuation-01/round-04/update/update-4.pt')
EXPECTED='24b8c3f3d5ddacd61e48bd87a526c1fd59b2a83eafbdacfe44bd5ddcfb5d3e6d'
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    torch.set_num_threads(1)
    oldio=module('_free_transfer_old_codec',HERE.parent/'strategic-learned-build-exploration-policy-v1/model_io.py')
    old,pb,digest=oldio.load_model(PARENT,'cpu');assert digest==EXPECTED and pb['optimizer_steps_total']==504
    initial=dict(format=model_io.INITIAL_FORMAT,schema=model_io.architecture.encoder.SCHEMA,
        encoder_version=model_io.architecture.ENCODER_VERSION,architecture_version=model_io.architecture.ARCHITECTURE_VERSION,
        state_dim=35,candidate_dim=43,hidden=old.hidden,prior_config=copy.deepcopy(pb['prior_config']),
        state_dict=model_io.cpu_tree(old.state_dict()),policy_tensor_sha256=model_io.tensor_sha(old.state_dict()),
        lineage=dict(reset_optimizer=True,reset_rng=True,discard_rollout=True,weights_only=True,new_gradient_steps=0,
            parent_checkpoint_sha256=digest,parent_optimizer_steps_not_continued=504,parent_training_updates=4,
            new_epoch='strategic-learned-free-transfer-training-v1',threat_replan='off',
            architecture_unchanged=True,native_qualification_pending=True))
    target=a.out/'free-transfer-initialization.pt';initial_sha=model_io.save_initialization(initial,target)
    new,_,loaded_sha=model_io.load_model(target,'cpu')
    assert loaded_sha==initial_sha and model_io.tensor_sha(new.state_dict())==model_io.tensor_sha(old.state_dict())
    loader=module('_free_transfer_historical_admission',HERE.parent/'strategic-learned-economy-policy-v1/load_admitted.py')
    source=Path('/root/heroes3-ai-lab/evaluations/strategic-learned-build-training-01');rows_checked=0;windows=0
    with torch.no_grad():
        for cell in sorted(source.glob('cell-*')):
            rows,_,_=loader.load(cell/'admitted')
            for row in rows:
                q=row['request'];batch=model_io.architecture.encoder.collate([q]);x,v=old(**batch);y,w=new(**batch)
                assert torch.equal(x,y) and torch.equal(v,w);rows_checked+=1
                windows+=any(c['op']=='build' for c in q['candidates'])
    assert rows_checked==3000 and windows==400
    optimizer=torch.optim.Adam(new.parameters(),lr=3e-4)
    assert not optimizer.state and model_io.steps(optimizer.state_dict())==0
    assert 'actor.build_bias' in model_io.groups(new,optimizer)[0]
    run=HERE.parent/'strategic-learned-free-transfer-run-v1';sys.path.append(str(run))
    import pipeline_common
    rejected=[]
    for name,fn in [('source_closure',pipeline_common.source_inputs),('capsule',lambda:pipeline_common.validate_capsule(Path('/unqualified/no-native-run'))),('qualification',pipeline_common.require_qualification)]:
        try:fn()
        except ValueError:rejected.append(name)
        else:raise AssertionError('Draft native execution gate accepted '+name)
    report=dict(passed=True,CPU_only=True,native_games=0,GPU_steps=0,optimizer_steps=0,
        status='reviewable source draft; native-v2 exact qualification pins and flow auditor pending; not frozen',
        parent_sha256=digest,parent_optimizer_steps_not_continued=504,initialization_sha256=initial_sha,
        same_architecture_exact_weights=True,logits_and_critic_bitwise_exact_rows=rows_checked,included_historical_build_windows=windows,
        new_Adam_state_empty=True,new_Adam_step=0,new_Adam_binding_includes_build_bias=True,
        unqualified_native_gates_rejected=rejected,
        source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in HERE.glob('*.py')})
    (a.out/'AUDIT.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
