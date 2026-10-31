"""Train only paired-benefit WAIT labels, then freeze before independent tests."""
import fcntl
import argparse
import gzip
import importlib.util
import json
import os
from pathlib import Path
import shutil
import time
import numpy as np
import torch
from lab_io import atomic_json
from evaluation_provenance import digest
from graph_observation_codec import unpack

HERE=Path(__file__).resolve().parent
LAB=HERE.parents[1]
VARIANT=HERE/'wait-variant-v2'
INITIAL='/root/heroes3-ai-lab/models/graph-finetune/1792068859379237126/update-64.pt'


def verify_inputs(provenance):
    for path,expected in provenance['input_hashes'].items():
        assert digest(path)==expected, 'Frozen input changed: '+path
    for path,expected in provenance.get('snapshot_hashes',{}).items():
        assert digest(path)==expected, 'Source snapshot changed: '+path


def capture_inputs():
    """Capture executable inputs before waiting for the CUDA/resource lock."""
    files={Path(__file__),HERE/'graph_observation_codec.py',HERE/'reconstruct_wait.py',
        HERE/'source_wait_case.json',VARIANT/'source_wait_case.json',
        LAB/'research/recovered-graph.py',LAB/'research/gpu_opponent.py',
        LAB/'research/lab_io.py',LAB/'research/evaluation_provenance.py',
        LAB/'research/battle_outcome_audit.py',Path(INITIAL)}
    for name in ['candidate-bc-train.jsonl','wait-train-comparison.json','dataset-audit.json',
                 'heldout-scenarios.json','source-wait-scenarios.json']:
        files.add(VARIANT/name)
    for name in ['heldout-scenarios.json','source-wait-scenarios.json']:
        for case in json.loads((VARIANT/name).read_text()):
            path=Path('/root/heroes3-ai-lab/data/vcmi/Maps')/case['map']
            assert digest(path)==case['sha256'], 'Scenario differs from declared fixture: '+case['id']
            files.add(path)
    for row in json.loads((VARIANT/'wait-train-comparison.json').read_text())['results']:
        if not row['benefit_verified']:continue
        for kind in ['wait-expert','no-wait-control']:
            path=VARIANT/'wait-runs'/f'{row["case"]}-{kind}.json'
            files.add(path)
            raw=json.loads(path.read_text())
            for source,expected in raw['source_hashes'].items():
                assert digest(source)==expected, 'Demonstration source changed: '+source
                files.add(Path(source))
    snapshot=VARIANT/'run-snapshots'/str(time.time_ns())
    snapshot.mkdir(parents=True)
    provenance=dict(input_hashes={str(path):digest(path) for path in sorted(files)},
        snapshot_hashes={},captured_unix=time.time(),captured_before_resource_lock=True)
    for index,path in enumerate(sorted(files)):
        if path.suffix=='.py':
            destination=snapshot/f'{index:02d}-{path.name}'
            shutil.copy2(path,destination)
            assert digest(destination)==provenance['input_hashes'][str(path)]
            provenance['snapshot_hashes'][str(destination)]=digest(destination)
    verify_inputs(provenance)
    atomic_json(snapshot/'inputs.json',provenance)
    provenance['manifest']=str(snapshot/'inputs.json')
    return provenance


def validate_records(records):
    audit=json.loads((VARIANT/'dataset-audit.json').read_text())
    assert audit['status']=='passed' and audit['dataset_sha256']==digest(VARIANT/'candidate-bc-train.jsonl')
    assert audit['comparison_sha256']==digest(VARIANT/'wait-train-comparison.json')
    cases={case['id']:case for case in json.loads((VARIANT/'source-wait-scenarios.json').read_text())}
    comparisons={row['case']:row for row in json.loads((VARIANT/'wait-train-comparison.json').read_text())['results']}
    assert len({row['battle_id'] for row in records})==len(records)
    for row in records:
        case_id=row['paired_result']['case']
        assert row['split']=='train' and cases[case_id]['split']=='train'
        assert row['paired_result']==comparisons[case_id]
        assert row['paired_result']['normal_pair'] and row['paired_result']['benefit_verified'] and row['paired_result']['window_verified']
        assert row['action_type']==0 and row['action'] in row['observation']['active_action_ids']
        pair=[json.loads((VARIANT/'wait-runs'/f'{case_id}-{kind}.json').read_text()) for kind in ['wait-expert','no-wait-control']]
        side=int(cases[case_id]['role']=='defender')
        assert row['actor_side']==side
        for raw in pair:
            assert raw['terminated'] and not raw['truncated'] and raw['terminal_outcome']['result_type']==0 and raw['invalid_actions']==0
        assert all(row[key]==value for key,value in pair[0]['decisions'][0].items())
        assert pair[0]['cross_round_window_verified'] and pair[0]['terminal_outcome']['winner']==side
        losses=[sum(raw['terminal_outcome']['casualties'][str(side)].values()) for raw in pair]
        assert pair[1]['terminal_outcome']['winner']!=side or losses[0]<losses[1]


def model_window(decisions):
    """Measure actual model decisions, irrespective of episode(wait=False)."""
    return bool(len(decisions)>=3 and decisions[0]['action_type']==0
        and decisions[1]['round']==decisions[0]['round']
        and decisions[2]['round']==decisions[1]['round']+1
        and decisions[1]['opposing_actions_before']==decisions[2]['opposing_actions_before']
        and decisions[1]['opposing_actions_before']>decisions[0]['opposing_actions_before'])


def verify_freeze(training):
    frozen=json.loads((VARIANT/'source-bc-freeze.json').read_text())
    assert frozen['sha256']==training['sha256']==digest(training['checkpoint'])
    assert frozen['initial_sha256']==training['initial_sha256']==digest(INITIAL)
    assert frozen['dataset_sha256']==training['dataset_sha256']==digest(VARIANT/'candidate-bc-train.jsonl')
    assert digest(VARIANT/'heldout-scenarios.json')==frozen['heldout_definition_sha256']
    verify_inputs(frozen['input_provenance'])
    for case in json.loads((VARIANT/'heldout-scenarios.json').read_text()):
        assert digest(Path('/root/heroes3-ai-lab/data/vcmi/Maps')/case['map'])==case['sha256']
    return frozen


def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def train(provenance):
    data_path=VARIANT/'candidate-bc-train.jsonl'
    assert data_path.exists(),'No paired-benefit source demonstrations yet; do not fabricate positives'
    records=[json.loads(line) for line in data_path.read_text().splitlines() if line.strip()]
    assert records and {row['actor_side'] for row in records}=={0,1},'Require both roles with independently verified training benefit'
    # The wrapper emits only the initial proven WAIT, not an entire greedy path.
    validate_records(records)
    with Path('/root/heroes3-ai-lab/evaluations/.pool-lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        verify_inputs(provenance)
        for entry in Path('/proc').iterdir():
            if not entry.name.isdigit():continue
            try:command=(entry/'cmdline').read_bytes().split(b'\0')
            except OSError:continue
            # Other BC jobs also acquire this same flock before CUDA work;
            # they may legitimately be alive while waiting for our lock.
            assert not (len(command)>1 and Path(os.fsdecode(command[1])).name in ['train-graph-finetune.py','train-recovered-heads.py','train_conservative_heads.py']), 'Another unmanaged learner is active'
        os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG',':4096:8')
        torch.set_num_threads(2);torch.manual_seed(2026103101)
        torch.use_deterministic_algorithms(True)
        graph=load_module('source_wait_graph',LAB/'research/recovered-graph.py')
        pair=graph.RecoveredPair(INITIAL).cuda().eval()
        observations=[unpack(row['observation'],row['actor_side']) for row in records]
        labels=torch.tensor([row['observation']['active_action_ids'].index(row['action']) for row in records],device='cuda')
        cache=pair.encode_features(observations)
        batch=graph.head_collate(cache,'cuda');mask=batch[-1]
        before={name:parameter.detach().cpu().clone() for name,parameter in pair.named_parameters()}
        for name,parameter in pair.named_parameters():parameter.requires_grad_('policy_head__' in name)
        with torch.inference_mode():
            original_logits,_=pair(*batch)
            reference_logp=original_logits.log_softmax(-1).masked_fill(~mask,0).detach().clone()
            reference_prob=original_logits.softmax(-1).detach().clone()
            initial_nll=float(torch.nn.functional.cross_entropy(original_logits,labels))
        optimizer=torch.optim.Adam([parameter for parameter in pair.parameters() if parameter.requires_grad],lr=1e-4)
        for _ in range(60):
            logits,_=pair(*batch)
            nll=torch.nn.functional.cross_entropy(logits,labels)
            logp=logits.log_softmax(-1).masked_fill(~mask,0)
            kl=(reference_prob*(reference_logp-logp)).sum(-1).mean()
            loss=nll+0.1*kl
            assert torch.isfinite(loss)
            optimizer.zero_grad(set_to_none=True);loss.backward()
            assert torch.isfinite(torch.nn.utils.clip_grad_norm_(pair.parameters(),0.5))
            optimizer.step()
        with torch.inference_mode():
            logits,_=pair(*batch)
            final_nll=float(torch.nn.functional.cross_entropy(logits,labels))
        assert final_nll<initial_nll
        verify_inputs(provenance)
        for name,parameter in pair.named_parameters():
            if 'policy_head__' not in name:assert torch.equal(before[name],parameter.detach().cpu())
        target=VARIANT/'models/source-wait-bc.pt';target.parent.mkdir(parents=True,exist_ok=True)
        assert not target.exists(),'Preserve frozen source-pilot weights'
        bundle=dict(models={role:dict(weights={key.replace('__','.'):value.detach().cpu() for key,value in model.weights.items()},metadata=model.metadata) for role,model in pair.models.items()},
            source='Hallas WAIT principle reconstructed and paired-benefit filtered; lab demonstrations, not human replay',
            algorithm='BC',finetuning_mode='heads',completed_updates=0,environment_steps=0,bc_steps=60,
            optimizer_state_dict=optimizer.state_dict(),torch_rng_state=torch.get_rng_state(),cuda_rng_states=torch.cuda.get_rng_state_all(),
            config=dict(initial=INITIAL,seed=2026103101,lr=1e-4,reference_kl_coefficient=0.1,dataset_sha256=digest(data_path)),
            resume_note='BC optimizer; start PPO with fresh optimizer instead of --resume')
        temporary=target.with_name(target.name+'.tmp');torch.save(bundle,temporary)
        with temporary.open('rb') as stream:os.fsync(stream.fileno())
        os.replace(temporary,target)
        report=dict(completed=True,CUDA_training=True,checkpoint=str(target),sha256=digest(target),initial=INITIAL,
            initial_sha256=digest(INITIAL),dataset=str(data_path),dataset_sha256=digest(data_path),samples=len(records),
            initial_training_nll=initial_nll,final_training_nll=final_nll,steps=60,
            policy_heads_only=True,graph_and_value_unchanged=True,source='hallas-2001-wait-cross-round-action-window',
            test_read=False,trained_on_human_replay=False,script_sha256=provenance['input_hashes'][str(Path(__file__))],
            input_provenance=provenance)
        atomic_json(VARIANT/'source-bc-training.json',report)
        atomic_json(VARIANT/'source-bc-freeze.json',dict(**report,frozen_unix=time.time(),heldout_definition_sha256=digest(VARIANT/'heldout-scenarios.json')))
        return report


def evaluate(training):
    frozen=verify_freeze(training)
    reconstruction=load_module('source_wait_runtime',HERE/'reconstruct_wait.py')
    graph=load_module('source_wait_eval_graph',LAB/'research/recovered-graph.py')
    cases=json.loads((VARIANT/'heldout-scenarios.json').read_text())
    evaluation_root=VARIANT/'model-evaluation';evaluation_root.mkdir(exist_ok=True)
    source_copy=evaluation_root/'source_wait_case.json'
    if not source_copy.exists():source_copy.write_bytes((HERE/'source_wait_case.json').read_bytes())
    assert digest(source_copy)==digest(HERE/'source_wait_case.json')
    reconstruction.HERE=evaluation_root
    original_greedy=reconstruction.greedy
    results=[]
    for label,path in [('baseline',INITIAL),('source-bc',training['checkpoint'])]:
        verify_freeze(training)
        model=graph.RecoveredPair(path).cpu().eval()
        for case in cases:
            if case['split']!='test':continue
            verify_freeze(training)
            side=int(case['role']=='defender')
            def predict(obs):
                if obs['lab_side']!=side:return original_greedy(obs)
                with torch.inference_mode():logits,value=model.models[case['role']](obs)
                assert torch.isfinite(logits).all() and torch.isfinite(value).all()
                return int(obs['active_action_ids'][int(logits.argmax())])
            reconstruction.greedy=predict
            adjusted=dict(case,id=case['id']+'-'+label)
            output=evaluation_root/'wait-runs'/f'{adjusted["id"]}-no-wait-control.json'
            if output.exists():
                previous=json.loads(output.read_text())
                assert previous.get('model_sha256')==digest(path), 'Cached raw battle has no matching frozen model attribution'
                assert previous.get('model_evaluation_wrapper_sha256')==frozen['script_sha256'], 'Cached evaluation used another wrapper'
            try:result=reconstruction.episode(adjusted,False)
            finally:reconstruction.greedy=original_greedy
            verify_freeze(training)
            result['policy']=label;result['model_checkpoint']=str(path);result['model_sha256']=digest(path)
            result['model_evaluation_wrapper_sha256']=frozen['script_sha256']
            result['cross_round_window_verified']=model_window(result['decisions'])
            for decision in result['decisions']:decision['expert_version']='model-'+digest(path)
            atomic_json(output,result)
            results.append(dict(case=case['id'],role=case['role'],policy=label,success=result['success'],
                truncated=result['truncated'],loss=result['permanent_units_lost'],first_action=result['decisions'][0]['action_type'],
                window_verified=result['cross_round_window_verified'],report=str(output)))
            atomic_json(VARIANT/'source-bc-heldout.json',dict(results=results,complete=False))
    assert len(results)==2*sum(case['split']=='test' for case in cases)==8
    verify_freeze(training)
    atomic_json(VARIANT/'source-bc-heldout.json',dict(results=results,complete=True,
        limitations='Four held-out conditions, same creature pair and controlled opponent. No claim of broad transfer or ordinary BattleAI retention. Model was frozen before test; no selection from these outcomes.'))


def main():
    global VARIANT
    parser=argparse.ArgumentParser()
    parser.add_argument('--experiment',default=str(VARIANT))
    args=parser.parse_args()
    VARIANT=Path(args.experiment).resolve()
    assert VARIANT.is_relative_to(HERE), 'Keep source-pilot outputs isolated'
    report_path=VARIANT/'source-bc-training.json'
    if report_path.exists():
        report=json.loads(report_path.read_text());assert digest(report['checkpoint'])==report['sha256']
    else:report=train(capture_inputs())
    evaluate(report)


if __name__=='__main__':main()
