"""Actual native observations, migration equivalence and CPU checkpoint negatives."""
import argparse,copy,hashlib,importlib.util,json,random
from pathlib import Path
import torch
import encoder,model_io
from broker import Broker,validate_response
from qualification import require_qualification,qualified_catalog
HERE=Path(__file__).resolve().parent
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    torch.set_num_threads(1);b=require_qualification();catalog=qualified_catalog()
    init=HERE/'initialization-02/recruitment-initialization.pt'
    new,bundle,digest=model_io.load_model(init)
    spec=importlib.util.spec_from_file_location('_actual_cpu_oldcodec',HERE.parent/'strategic-learned-free-transfer-policy-v1/model_io.py')
    oldio=importlib.util.module_from_spec(spec);spec.loader.exec_module(oldio)
    old,_,_=oldio.load_model(HERE.parent/'strategic-learned-free-transfer-policy-v1/initialization-01/free-transfer-initialization.pt')
    raw=Path(json.loads(Path(b['mechanism_report']).read_text())['raw']);broker=Broker('new-policy',init)
    checked=0;actual_offers=[];bad_response=[]
    for number,path in enumerate(sorted((raw/'agent').glob('request-*.json')),1):
        original=path.read_bytes();q=json.loads(original);encoder.validate(q,catalog=catalog)
        proposal=broker.propose(original,number)
        actual_offers.extend(c['creature_id'] for c in q['candidates'] if c['op']=='recruit')
        reduced=copy.deepcopy(q);reduced['candidates']=[c for c in q['candidates'] if c['op']!='recruit']
        with torch.no_grad():x,v=old(**encoder.old.collate([encoder.project(reduced)]));y,w=new(**encoder.collate([reduced],catalog=catalog))
        assert torch.equal(x,y) and torch.equal(v,w) and torch.equal(x.softmax(-1),y.softmax(-1))
        response=proposal['response'];wrong=copy.deepcopy(response);wrong['request_sha256']='f'*64
        try:validate_response(wrong,q,original)
        except ValueError:bad_response.append(number)
        else:raise AssertionError('Wrong byte binding accepted')
        checked+=1
    coverage=encoder.require_training_catalog(catalog,b,actual_offers)
    torch.manual_seed(2026103900);random.seed(2026103900)
    opt=torch.optim.Adam(new.parameters(),lr=3e-4);assert not opt.state
    protocol=dict(initial_manual_recruit_bias=0.,schema='strategic-learned-recruitment-prior-zero-training-v1',catalog_sha256=catalog['sha256'],architecture_version=model_io.architecture.ARCHITECTURE_VERSION,
        action_schema=encoder.SCHEMA,economy_epoch=encoder.EPOCH,contract_sha256=model_io.CONTRACT_SHA256,threat_replan='off',
        native_flow_epoch=encoder.EPOCH,flow_contract_sha256=model_io.FLOW_CONTRACT_SHA256)
    rng=torch.get_rng_state().clone()
    checkpoint=model_io.make_bundle(new,opt,training_updates=0,complete=True,protocol=protocol,parent_sha=digest,lineage=dict(cpu_codec_test=True),
        collection_states={},purpose='cpu_codec_test',progress={})
    assert torch.equal(torch.get_rng_state(),rng)
    target=a.out/'CPU_CODEC_TEST_NOT_TRAINING.pt';model_io.atomic_save(checkpoint,target,allow_test=True)
    loaded,readback,_=model_io.load_model(target,allow_test=True)
    assert torch.equal(torch.get_rng_state(),rng) and model_io.tensor_sha(loaded.state_dict())==model_io.tensor_sha(new.state_dict())
    restored=torch.optim.Adam(loaded.parameters(),lr=3e-4)
    model_io.restore_training(readback,loaded,restored,protocol_sha=model_io.digest_json(protocol),allow_test=True)
    assert not restored.state and torch.equal(torch.get_rng_state(),rng)
    negatives=[]
    mutations=dict(wrong_catalog=lambda x:x.update(catalog_sha256='f'*64),partial_boundary=lambda x:x.update(complete_update_boundary=False),
        wrong_dim=lambda x:x.update(candidate_dim=43),duplicate_Adam_ID=lambda x:x['optimizer']['param_groups'][0]['params'].__setitem__(1,x['optimizer']['param_groups'][0]['params'][0]),wrong_adam_count=lambda x:x.update(optimizer_steps_total=1),
        wrong_protocol=lambda x:x['protocol'].update(economy_epoch='old'),wrong_tensor_sha=lambda x:x.update(policy_tensor_sha256='f'*64),
        malformed_CPU_RNG=lambda x:x['rng'].update(torch=torch.zeros(2,dtype=torch.uint8)),malformed_Python_RNG=lambda x:x['rng'].update(python=(0,)))
    for name,mutate in mutations.items():
        changed=copy.deepcopy(checkpoint);mutate(changed)
        try:model_io.validate(changed,resume=True,allow_test=True)
        except ValueError:negatives.append(name)
        else:raise AssertionError('Accepted '+name)
    for name,fn in [('CPU_test_as_training',lambda:model_io.read(target)),('CPU_as_CUDA_resume',lambda:model_io.restore_training(checkpoint,loaded,restored,protocol_sha=model_io.digest_json(protocol),device='cuda',allow_test=True)),
                    ('resume_protocol_change',lambda:model_io.restore_training(checkpoint,loaded,restored,protocol_sha='f'*64,allow_test=True))]:
        try:fn()
        except ValueError:negatives.append(name)
        else:raise AssertionError('Accepted '+name)
    with torch.no_grad():loaded.actor.stop_bias.add_(.125)
    live_before=model_io.tensor_sha(loaded.state_dict());live_rng=torch.get_rng_state().clone()
    broken=copy.deepcopy(checkpoint);broken['rng']['python']=(0,)
    try:model_io.restore_training(broken,loaded,restored,protocol_sha=model_io.digest_json(protocol),allow_test=True)
    except ValueError:pass
    else:raise AssertionError('Bad restore unexpectedly accepted')
    assert model_io.tensor_sha(loaded.state_dict())==live_before and torch.equal(torch.get_rng_state(),live_rng) and not restored.state
    report=dict(passed=True,CPU_only=True,actual_native_requests_checked=checked,actual_catalog_sha256=catalog['sha256'],coverage=coverage,
        actual_no_recruit_projection_logits_critic_softmax_bitwise_equal=True,model_sha256=digest,byte_binding_negatives=len(bad_response),
        codec_roundtrip_exact=True,new_Adam_state_empty=True,RNG_unchanged_by_save_load=True,bad_restore_leaves_live_model_Adam_RNG_unchanged=True,rejected_cases=negatives,
        optimizer_steps=0,GPU_steps=0,native_runs=0,codec_checkpoint_is_training=False)
    (a.out/'AUDIT.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
