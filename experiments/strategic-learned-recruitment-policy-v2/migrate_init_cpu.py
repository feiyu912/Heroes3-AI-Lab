"""833 weights-only migration with actual qualified vocabulary; fresh Adam/RNG."""
import argparse,copy,hashlib,importlib.util,json,random
from pathlib import Path
import torch
import model_io
from qualification import qualified_catalog,require_qualification
HERE=Path(__file__).resolve().parent
PARENT=HERE.parent/'strategic-learned-free-transfer-policy-v1/initialization-01/free-transfer-initialization.pt'
EXPECTED='83319be8bde5d94eea839b1a889821449a7c1492c65da7ca6cde2deb63aab25a'
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--seed',type=int,default=2026103900);a=p.parse_args()
    b=require_qualification();catalog=qualified_catalog();torch.set_num_threads(1)
    spec=importlib.util.spec_from_file_location('_recruit_parent_codec',PARENT.parent.parent/'model_io.py')
    oldio=importlib.util.module_from_spec(spec);spec.loader.exec_module(oldio)
    old,bundle,digest=oldio.load_model(PARENT,'cpu');assert digest==EXPECTED
    torch.manual_seed(a.seed);random.seed(a.seed)
    new=model_io.architecture.migrate_weights_only(old,catalog_size=len(catalog['ids']))
    optimizer=torch.optim.Adam(new.parameters(),lr=3e-4)
    assert not optimizer.state and model_io.steps(optimizer.state_dict())==0
    prior=copy.deepcopy(bundle['prior_config']);prior.update(recruit_bias=-4.,catalog_size=len(catalog['ids']))
    initial=dict(format=model_io.INITIAL_FORMAT,schema=model_io.architecture.encoder.SCHEMA,encoder_version=model_io.architecture.ENCODER_VERSION,
        architecture_version=model_io.architecture.ARCHITECTURE_VERSION,state_dim=35,candidate_dim=new.candidate_dim,catalog_sha256=catalog['sha256'],
        hidden=old.hidden,prior_config=prior,state_dict=model_io.cpu_tree(new.state_dict()),policy_tensor_sha256=model_io.tensor_sha(new.state_dict()),
        lineage=dict(reset_optimizer=True,reset_rng=True,discard_rollout=True,weights_only=True,new_gradient_steps=0,
            parent_checkpoint_sha256=digest,new_epoch='strategic-learned-recruitment-training-v1',threat_replan='off',
            manual_recruit_prior=-4.,manual_prior_is_learning=False,migration_seed=a.seed,qualification_report_sha256=b['mechanism_report_sha256']))
    a.out.mkdir(parents=True,exist_ok=False);target=a.out/'recruitment-initialization.pt'
    output_sha=model_io.save_initialization(initial,target);loaded,_,loaded_sha=model_io.load_model(target)
    assert loaded_sha==output_sha and model_io.tensor_sha(loaded.state_dict())==model_io.tensor_sha(new.state_dict())
    report=dict(passed=True,CPU_only=True,parent_sha256=digest,initialization_sha256=output_sha,catalog_sha256=catalog['sha256'],
        registered_species=len(catalog['ids']),new_Adam_state_empty=True,reset_RNG=True,discard_rollout=True,optimizer_steps=0,
        native_runs=0,GPU_steps=0,manual_prior_is_learning=False,readback_exact=True)
    (a.out/'AUDIT.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
