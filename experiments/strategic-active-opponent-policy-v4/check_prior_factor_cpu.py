"""Exact one-tensor initialization comparison; actual requests, zero optimizer steps."""
import argparse,hashlib,io,json
from pathlib import Path
import torch
import encoder,model_io
from qualification import require_qualification
HERE=Path(__file__).resolve().parent;EXP=HERE.parent
OLD=EXP/'strategic-learned-recruitment-policy-v2/initialization-01/recruitment-initialization.pt'
OLD_SHA='b9ede0d158d113eff42d58cb8a844277b42e8a0820122d985299dfcf9cdb7b79'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    torch.set_num_threads(1)
    protected=json.loads((EXP/'strategic-learned-recruitment-run-v1/SOURCE_FREEZE.json').read_text())['files']
    assert all(sha(EXP/relative.replace('\\','/'))==h for relative,h in protected.items())
    assert sha(OLD)==OLD_SHA
    oldbundle=torch.load(io.BytesIO(OLD.read_bytes()),map_location='cpu',weights_only=True)
    new,newbundle,newsha=model_io.load_model(HERE/'initialization-02/recruitment-initialization.pt','cpu')
    assert set(oldbundle['state_dict'])==set(newbundle['state_dict'])
    changed=[name for name in oldbundle['state_dict'] if not torch.equal(oldbundle['state_dict'][name],newbundle['state_dict'][name])]
    assert changed==['actor.recruit_bias']
    assert float(oldbundle['state_dict']['actor.recruit_bias'])==-4. and float(newbundle['state_dict']['actor.recruit_bias'])==0.
    assert oldbundle['lineage']['parent_checkpoint_sha256']==newbundle['lineage']['parent_checkpoint_sha256']
    assert oldbundle['lineage']['migration_seed']==newbundle['lineage']['migration_seed']==2026103900
    assert oldbundle['catalog_sha256']==newbundle['catalog_sha256']
    assert oldbundle['architecture_version']==newbundle['architecture_version'] and oldbundle['encoder_version']==newbundle['encoder_version']
    old=model_io.architecture.PriorCandidateActorCritic(oldbundle['hidden'],**oldbundle['prior_config']);old.load_state_dict(oldbundle['state_dict'],strict=True);old.eval()
    binding=require_qualification();raw=Path(json.loads(Path(binding['mechanism_report']).read_text())['raw'])
    cases=[];max_error=0.
    for path in sorted((raw/'agent').glob('request-*.json')):
        request=json.loads(path.read_text());batch=encoder.collate([request])
        with torch.no_grad():oz,ov=old(**batch);nz,nv=new(**batch)
        assert torch.equal(ov,nv)
        recruit=[i for i,c in enumerate(request['candidates']) if c['op']=='recruit'];other=[i for i,c in enumerate(request['candidates']) if c['op']!='recruit']
        assert torch.equal(oz[:,other],nz[:,other])
        if recruit:
            error=float(((nz[:,recruit]-oz[:,recruit])-4.).abs().max());max_error=max(max_error,error);assert error<=1e-6
        cases.append(dict(decision_id=request['request_id'],old_argmax_op=request['candidates'][int(oz.argmax(-1)[0])]['op'],new_argmax_op=request['candidates'][int(nz.argmax(-1)[0])]['op'],
            old_recruit_probability=sum(float(oz.softmax(-1)[0,i]) for i in recruit),new_recruit_probability=sum(float(nz.softmax(-1)[0,i]) for i in recruit)))
    rejected=[]
    import importlib.util
    spec=importlib.util.spec_from_file_location('_frozen_minus_four_codec_rejection',EXP/'strategic-learned-recruitment-policy-v2/model_io.py')
    oldio=importlib.util.module_from_spec(spec);spec.loader.exec_module(oldio)
    for name,fn in [('old_prior_initialization_wrong_epoch',lambda:model_io.initialization_model(oldbundle)),
                    ('zero_prior_initialization_in_old_codec',lambda:oldio.initialization_model(newbundle)),
                    ('false_zero_prior_metadata',lambda:model_io.initialization_model(dict(newbundle,prior_config=dict(newbundle['prior_config'],recruit_bias=-4.))))]:
        try:fn()
        except ValueError:rejected.append(name)
        else:raise AssertionError('Accepted '+name)
    optimizer=torch.optim.Adam(new.parameters(),lr=3e-4);assert not optimizer.state
    from episode_balanced_ppo import PROTOCOL
    spec=importlib.util.spec_from_file_location('_same_prior_parent_ppo',EXP/'strategic-learned-recruitment-policy-v2/episode_balanced_ppo.py')
    parent=importlib.util.module_from_spec(spec);spec.loader.exec_module(parent);assert PROTOCOL==parent.PROTOCOL
    assert all(sha(EXP/relative.replace('\\','/'))==h for relative,h in protected.items()) and sha(OLD)==OLD_SHA
    report=dict(passed=True,CPU_only=True,changed_initial_tensors=changed,old_initial_sha256=OLD_SHA,new_initial_sha256=newsha,
        old_manual_recruit_bias=-4.,new_manual_recruit_bias=0.,manual_prior_is_learning=False,same_833_parent=True,same_catalog_architecture_encoder=True,
        PPO_protocol_exactly_unchanged=True,new_Adam_empty=True,same_reset_initial_RNG_seed=2026103900,actual_requests_checked=len(cases),nonrecruit_logits_and_critic_exact=True,
        recruit_logit_delta_expected=4.,recruit_logit_delta_max_error=max_error,actual_request_probability_changes=cases,rejected_cases=rejected,
        old_source_freeze_all_files_unchanged=True,optimizer_steps=0,GPU_steps=0,native_runs=0,locks_acquired=False,DEV_read=False)
    (a.out/'AUDIT.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='actual_request_probability_changes'},indent=2))
if __name__=='__main__':main()
