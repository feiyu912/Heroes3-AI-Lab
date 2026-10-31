"""Read-only proof that changing runtime/source protocol cannot reuse old resume acceptance."""
import argparse,copy,hashlib,importlib.util,json,random
from pathlib import Path
import torch
HERE=Path(__file__).resolve().parent
PARENT=Path('/root/heroes3-ai-lab/evaluations/strategic-build-exploration-continuation-01/round-04/update/update-4.pt')
EXPECTED='24b8c3f3d5ddacd61e48bd87a526c1fd59b2a83eafbdacfe44bd5ddcfb5d3e6d'
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    source=HERE.parent/'strategic-learned-build-exploration-policy-v1/model_io.py'
    spec=importlib.util.spec_from_file_location('_free_transfer_draft_old_codec',source)
    codec=importlib.util.module_from_spec(spec);spec.loader.exec_module(codec)
    torch.set_num_threads(1);model,bundle,digest=codec.load_model(PARENT,'cpu')
    assert digest==EXPECTED and bundle['optimizer_steps_total']==504
    optimizer=torch.optim.Adam(model.parameters(),lr=3e-4)
    before=codec.tensor_sha(model.state_dict());rng=torch.get_rng_state().clone();python=random.getstate()
    proposed=copy.deepcopy(bundle['protocol']);proposed['schema']='strategic-learned-free-transfer-training-v1'
    # This is only a changed-protocol rejection test, not a fabricated v2 capsule SHA.
    proposed_sha=codec.digest_json(proposed);assert proposed_sha!=bundle['protocol_sha256']
    try:codec.restore_training(bundle,model,optimizer,protocol_sha=proposed_sha,device='cpu')
    except ValueError as error:reason=str(error)
    else:raise AssertionError('Old protocol resume wrongly accepted a changed epoch')
    assert before==codec.tensor_sha(model.state_dict()) and not optimizer.state
    assert torch.equal(rng,torch.get_rng_state()) and python==random.getstate()
    report=dict(passed=True,CPU_only=True,native_games=0,GPU_steps=0,optimizer_steps=0,status='draft_only_not_frozen',
        parent_sha256=digest,parent_saved_Adam_steps=504,old_protocol_sha256=bundle['protocol_sha256'],
        changed_schema_test_protocol_sha256=proposed_sha,old_resume_rejected=True,rejection_reason=reason,
        model_optimizer_CPU_Python_RNG_unchanged=True,chosen_transition='same-architecture exact weights-only migration; reset Adam/RNG/rollout; new source/runtime epoch',
        native_v2_capsule_pins_pending=True,new_initialization_not_generated=True,
        inspected_codec_sha256=hashlib.sha256(source.read_bytes()).hexdigest())
    (a.out/'AUDIT.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
