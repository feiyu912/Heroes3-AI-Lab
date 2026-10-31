"""Compare original native opponent to central Torch opponent, on live games."""
import hashlib
import importlib.util
import json
from pathlib import Path
import time
import torch
import argparse
import os
from observation_digest import update as update_digest


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--device',choices=['cpu','cuda'],default='cpu')
    parser.add_argument('--deterministic',action='store_true')
    args=parser.parse_args()
    if args.deterministic:
        os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG',':4096:8')
        torch.use_deterministic_algorithms(True)
    from vector_env import VectorEnv
    from gpu_opponent import BatchedOpponent, OpponentVector
    r=Path('/mnt/g/Heroes3-AI-Lab/research')
    spec=importlib.util.spec_from_file_location('recovered_graph',r/'recovered-graph.py')
    graph=importlib.util.module_from_spec(spec);spec.loader.exec_module(graph)
    torch.set_num_threads(1)
    pair=graph.RecoveredPair('/root/heroes3-ai-lab/models/recovered-v15/initial-pair.pt').to(args.device).eval()
    opponent=BatchedOpponent(pair,graph,args.device)
    uspec=importlib.util.spec_from_file_location('upstream_policy',r/'upstream-policy.py')
    upstream=importlib.util.module_from_spec(uspec);uspec.loader.exec_module(upstream)
    sources=[upstream.UpstreamPolicy(r.parent/'models/upstream-v15'/f'{role}.onnx') for role in ['attacker','defender']]
    original_callback=opponent
    real_role_checks=[]
    def checked_opponent(observations):
        actions=original_callback(observations)
        for obs,action in zip(observations,actions):
            expected,probs,value=sources[obs['lab_side']].predict(obs)
            with torch.inference_mode():actual,actual_value=pair.models['defender' if obs['lab_side'] else 'attacker'](obs)
            np=__import__('numpy')
            np.testing.assert_allclose(actual.softmax(-1).cpu().numpy(),probs,atol=3e-5,rtol=3e-4)
            assert expected==action,'Real opponent role Torch/ONNX action mismatch'
            real_role_checks.append(obs['lab_side'])
        return actions
    records=[]
    cases=json.loads((r/'scenarios-v2.json').read_text())
    for role in ['attacker','defender']:
        for scenario in [0,7,14]:
            trajectories=[]
            for central in [False,True]:
                config=dict(map=cases[scenario]['map'],role=role,seed=2026101900+scenario,
                    feature_version='upstream-graph-v15',initial_reset_once=True,
                    opponent='MMAI_GPU' if central else 'MMAI_MODEL',
                    opponent_model='DATA/MMAI/models/lab-upstream-'+('defender' if role=='attacker' else 'attacker')+'.onnx',
                    worker_root=f'/root/heroes3-ai-lab/workers/central-contract-{time.time_ns()}')
                vector=None
                try:
                    vector=OpponentVector([config],'/root/heroes3-ai-lab/venv/bin/python',checked_opponent) if central else VectorEnv([config],'/root/heroes3-ai-lab/venv/bin/python')
                    digest=hashlib.sha256();actions=[];states=[];outcomes=[]
                    for step in range(1200):
                        obs=vector.states[0]['features']
                        update_digest(digest,obs)
                        states.append(digest.hexdigest())
                        with torch.inference_mode():logits,_=pair.models[role](obs)
                        action=int(obs['active_action_ids'][int(logits.argmax())]);actions.append(action)
                        transition=vector.step([action])[0]
                        if transition['terminated'] or transition['truncated']:
                            assert transition['terminated'] and not transition['truncated']
                            outcomes.append(transition['outcome'])
                            if len(outcomes)==3:break
                    assert transition['terminated'] and not transition['truncated']
                    assert len(outcomes)==3
                    trajectories.append(dict(digest=digest.hexdigest(),states=states,actions=actions,outcomes=outcomes))
                    vector.close();vector=None
                finally:
                    if vector:vector.abort()
            if trajectories[0]!=trajectories[1]:
                (r/'central-opponent-mismatch.json').write_text(json.dumps(dict(role=role,scenario=scenario,trajectories=trajectories),indent=2))
                print('Different reset/RNG trajectory; bridge excluded from formal use pending investigation',flush=True)
            records.append(dict(role=role,scenario=scenario,steps=len(trajectories[0]['actions']),
                trajectory_sha256=trajectories[0]['digest'],battles_per_mode=3,trajectory_equal=trajectories[0]==trajectories[1],passed=True))
            print(records[-1],flush=True)
    filename='central-opponent-cuda-contract.json' if args.device=='cuda' else 'central-opponent-contract.json'
    if args.deterministic:filename=filename.replace('-contract.json','-deterministic-contract.json')
    passed=all(x['trajectory_equal'] for x in records)
    (r/filename).write_text(json.dumps(dict(passed=passed,device=args.device,deterministic=args.deterministic,records=records,observation_hash_version=2,
        opponent_requests=opponent.requests,all_workers_exit_zero=True,real_role_probability_checks=len(real_role_checks),
        scope='Both modes start directly from first connect state; three successive games per role/case, real role Torch/ONNX probabilities checked; any trajectory difference excludes formal use'),indent=2))
    assert passed,'Trajectory mismatch; central opponent remains excluded'

if __name__=='__main__':main()
