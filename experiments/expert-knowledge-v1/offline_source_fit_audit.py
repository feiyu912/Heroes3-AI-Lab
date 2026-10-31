"""CPU-only fit audit of four TRAIN labels; never opens held-out states/results."""
import os
os.environ['CUDA_VISIBLE_DEVICES']=''
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG',':4096:8')
import hashlib
import importlib.util
import json
from pathlib import Path
import numpy as np
import torch

HERE=Path(__file__).resolve().parent
VARIANT=HERE/'wait-variant-v2'
LAB=HERE.parents[1]
READ=[]


def sha(path):
    path=Path(path)
    assert 'model-evaluation' not in str(path) and 'heldout' not in path.name.lower(), 'Refuse held-out data'
    READ.append(str(path))
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result


def main():
    torch.set_num_threads(2)
    torch.use_deterministic_algorithms(True)
    report_path=VARIANT/'source-bc-training.json'
    training=json.loads(report_path.read_text());READ.append(str(report_path))
    paths=dict(initial=Path(training['initial']),after=Path(training['checkpoint']),dataset=Path(training['dataset']))
    assert sha(paths['initial'])==training['initial_sha256']
    assert sha(paths['after'])==training['sha256']
    assert sha(paths['dataset'])==training['dataset_sha256']
    codepaths=[HERE/'graph_observation_codec.py',LAB/'research/recovered-graph.py']
    for path in codepaths:
        assert sha(path)==training['input_provenance']['input_hashes'][str(path)]
    graph=module('source_train_fit_graph',codepaths[1])
    codec=module('source_train_fit_codec',codepaths[0])
    records=[json.loads(line) for line in paths['dataset'].read_text().splitlines() if line]
    assert len(records)==training['samples']==4 and all(row['split']=='train' for row in records)
    assert {row['actor_side'] for row in records}=={0,1}
    observations=[];labels=[]
    for row in records:
        assert row['action_type']==0 and row['paired_result']['benefit_verified']
        assert row['action'] in row['observation']['active_action_ids']
        obs=codec.unpack(row['observation'],row['actor_side'])
        for array in obs['nodes'].values():assert array.ndim==2 and np.isfinite(array).all()
        for edge in obs['edges'].values():
            assert edge['index'].ndim==edge['attrs'].ndim==2 and edge['index'].shape[0]==2
            assert edge['index'].shape[1]==edge['attrs'].shape[0] and np.isfinite(edge['attrs']).all()
        observations.append(obs)
        labels.append(row['observation']['active_action_ids'].index(row['action']))
    models={name:graph.RecoveredPair(str(path)).cpu().eval() for name,path in [('before',paths['initial']),('after',paths['after'])]}
    for name,parameter in models['before'].named_parameters():
        if 'policy_head__' not in name:
            assert torch.equal(parameter,dict(models['after'].named_parameters())[name])
    results={};nlls={}
    with torch.inference_mode():
        for label,model in models.items():
            cache=model.encode_features(observations)
            batch=graph.head_collate(cache,'cpu');mask=batch[-1]
            logits,values=model(*batch)
            assert torch.isfinite(logits[mask]).all() and torch.isfinite(values).all()
            assert torch.isneginf(logits[~mask]).all()
            assert all(np.isfinite(sample[0]).all() and np.isfinite(sample[1]).all() for sample in cache)
            probabilities=logits.softmax(-1)
            nlls[label]=float(torch.nn.functional.cross_entropy(logits,torch.tensor(labels)))
            rows=[]
            for i,(record,target) in enumerate(zip(records,labels)):
                length=len(record['observation']['active_action_ids'])
                scores=logits[i,:length];target_logit=scores[target]
                chosen=int(scores.argmax())
                rows.append(dict(case=record['paired_result']['case'],actor_side=record['actor_side'],split='train',
                    legal_actions=length,wait_action_id=record['action'],wait_probability=float(probabilities[i,target]),
                    wait_rank=1+int((scores>target_logit).sum()),tied_logit_count=int((scores==target_logit).sum()),
                    argmax_action_id=record['observation']['active_action_ids'][chosen],argmax_matches_wait=chosen==target,
                    wait_negative_log_probability=float(-scores.log_softmax(-1)[target])))
            results[label]=dict(argmax_correct=sum(row['argmax_matches_wait'] for row in rows),samples=4,records=rows)
    atol=2e-4
    assert abs(nlls['before']-training['initial_training_nll'])<=atol
    assert abs(nlls['after']-training['final_training_nll'])<=atol
    assert sha(paths['initial'])==training['initial_sha256'] and sha(paths['after'])==training['sha256']
    result=dict(status='passed',device='CPU only; no backward, optimizer, CUDA or game execution',
        training_report_sha256=sha(report_path),initial_sha256=training['initial_sha256'],model_sha256=training['sha256'],
        dataset_sha256=training['dataset_sha256'],auditor_sha256=sha(__file__),
        samples=4,split='train',heldout_states_or_results_read=False,
        source_codec_unchanged=True,graph_and_value_tensors_unchanged=True,shape_and_finite_checks_passed=True,
        batch_structure='Same four records as CUDA BC; role-specific graph batches and head_collate on CPU',
        nll_cpu=nlls,nll_cuda_recorded=dict(before=training['initial_training_nll'],after=training['final_training_nll']),
        nll_absolute_tolerance=atol,nll_absolute_difference={key:abs(value-training['initial_training_nll' if key=='before' else 'final_training_nll']) for key,value in nlls.items()},
        fit=results,files_read_or_hashed=sorted(set(READ)),
        limitations='Training-label fit only. Four initial WAIT labels do not establish held-out improvement, selective timing, counter-tactics or ordinary-battle retention.')
    (VARIANT/'source-training-fit-audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({key:result[key] for key in ['status','samples','model_sha256','nll_cpu','nll_absolute_difference']}))
    print(json.dumps({'argmax_correct':{key:value['argmax_correct'] for key,value in results.items()},'records':results}))


if __name__=='__main__':main()
