"""Measure CUDA graph (not merely cached head) recomputation before recovery."""
import argparse
import os
import json
from pathlib import Path
import numpy as np
import torch
import full_graph_policy as graph
from lab_io import atomic_json


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--checkpoint',required=True)
    args=parser.parse_args();torch.set_num_threads(2)
    os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG',':4096:8')
    model=graph.FullGraphPair(args.checkpoint,'all').cuda().eval()
    versions=[p._version for p in model.parameters()]
    folder=Path('/root/heroes3-ai-lab/datasets/teacher-balanced-v1/train')
    observations=[]
    for path in sorted(folder.glob('*.json'))[:8]:
        metadata=json.loads(path.read_text())
        with np.load(path.with_suffix('.npz'),allow_pickle=False) as archive:
            for t in range(min(8,len(metadata['decisions']))):
                nodes={};edges={}
                for key in archive.files:
                    if not key.startswith(f'{t}/'):continue
                    parts=key.split('/')
                    if parts[1]=='nodes':nodes[parts[2]]=archive[key]
                    elif parts[1]=='edges':edges.setdefault(tuple(parts[2].split('|')),{})[parts[3]]=archive[key]
                for side in [0,1]:
                    observations.append(dict(nodes=nodes,edges=edges,active_action_ids=archive[f'{t}/legal_ids'],lab_side=side))
    trials=[]
    for deterministic in [False,True]:
        torch.use_deterministic_algorithms(deterministic)
        reference=[]
        with torch.inference_mode():
            for start in range(0,len(observations),24):
                subset=observations[start:start+24];logits,_=model(*graph.collate(subset,'cuda'))
                reference.extend([row[:len(obs['active_action_ids'])].log_softmax(-1) for row,obs in zip(logits,subset)])
            for size in [24,32,8,64]:
                maximum=0.;weighted_maximum=0.;greedy_differences=0
                for repeat in range(3):
                    for start in range(0,len(observations),size):
                        subset=observations[start:start+size];logits,_=model(*graph.collate(subset,'cuda'))
                        for i,obs in enumerate(subset):
                            actual=logits[i,:len(obs['active_action_ids'])].log_softmax(-1)
                            expected=reference[start+i];difference=(actual-expected).abs()
                            maximum=max(maximum,float(difference.max()))
                            likely=expected>-12.
                            if likely.any():weighted_maximum=max(weighted_maximum,float(difference[likely].max()))
                            greedy_differences+=int(actual.argmax()!=expected.argmax())
                trial=dict(deterministic=deterministic,batch_size=size,repeats=3,
                    maximum_all_legal_log_probability_error=maximum,
                    maximum_log_probability_error_for_p_above_exp_minus12=weighted_maximum,
                    greedy_differences=greedy_differences)
                trials.append(trial);print(trial,flush=True)
        # Check the deterministic setting also supports the actual gradient path.
        logits,values=model(*graph.collate(observations[:24],'cuda'))
        loss=-logits.log_softmax(-1)[:,0].mean()+values.square().mean();loss.backward()
        assert all(p.grad is None or torch.isfinite(p.grad).all() for p in model.parameters())
        model.zero_grad(set_to_none=True)
    assert versions==[p._version for p in model.parameters()]
    assert next(t for t in trials if t['deterministic'] and t['batch_size']==24)['maximum_all_legal_log_probability_error']==0.
    atomic_json(Path(__file__).with_name('full-graph-cuda-recompute-contract.json'),dict(
        checkpoint=args.checkpoint,distinct_training_observations=len(observations)//2,role_observation_combinations=len(observations),trials=trials,
        no_optimizer_updates=True,weights_unchanged=True,gradient_paths_passed=True,
        matmul_allow_tf32=torch.backends.cuda.matmul.allow_tf32,
        cublas_workspace=os.environ.get('CUBLAS_WORKSPACE_CONFIG'),deterministic_rollout_batch_exact=True,
        explanation='All legal-action log probabilities are checked, including extremely unlikely actions; raw full graph repeats and different batch partitions, unlike cached-head-only test.'))


if __name__=='__main__':main()
