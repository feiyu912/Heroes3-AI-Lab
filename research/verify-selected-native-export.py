"""Export a frozen recovered candidate and check it in actual native battles.

Uses training scenarios only. Run via run-lab.sh with the GPU Python environment;
all inference here is deliberately on CPU, so no second CUDA trainer is started.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import time

import numpy as np
import torch
from lab_io import atomic_json
from observation_digest import update as update_digest
from vector_env import VectorEnv


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--checkpoint', required=True)
    parser.add_argument('--output-dir', required=True)
    args = parser.parse_args()
    research = Path(__file__).resolve().parent
    destination = Path(args.output_dir)
    checkpoint = Path(args.checkpoint)
    checksum = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
    before = checksum(checkpoint)

    def load(name, filename):
        spec = importlib.util.spec_from_file_location(name, research / filename)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    torch.set_num_threads(1)
    graph = load('export_graph', 'recovered-graph.py')
    upstream = load('export_upstream', 'upstream-policy.py')
    exporter = load('export_onnx', 'export-recovered-onnx.py')
    manifest = exporter.export(checkpoint, destination)
    pair = graph.RecoveredPair(str(checkpoint)).eval()
    policies = {role: upstream.UpstreamPolicy(destination / (role + '.onnx'))
                for role in ['attacker', 'defender']}
    native_directory = Path('/root/heroes3-ai-lab/data/vcmi/Data/MMAI/models')
    assert (native_directory / 'lab-upstream-attacker.onnx').is_file()
    prefix = 'lab-export-' + before[:16] + '-'
    for role in policies:
        target = native_directory / (prefix + role + '.onnx')
        shutil.copyfile(destination / (role + '.onnx'), target)
        assert checksum(target) == checksum(destination / (role + '.onnx'))
    cases = json.loads((research / 'scenarios-v2.json').read_text())
    records = []
    for role in policies:
        for scenario in [0, 7, 14]:
            other = 'defender' if role == 'attacker' else 'attacker'
            config = dict(map=cases[scenario]['map'], role=role,
                          seed=2026102500 + scenario,
                          feature_version='upstream-graph-v15', opponent='MMAI_MODEL',
                          opponent_model='DATA/MMAI/models/' + prefix + other + '.onnx',
                          worker_root='/root/heroes3-ai-lab/workers/export-' + str(time.time_ns()))
            vector = None
            maximum = 0.0
            digest = hashlib.sha256()
            try:
                vector = VectorEnv([config], '/root/heroes3-ai-lab/venv/bin/python')
                for step in range(1200):
                    obs = vector.states[0]['features']
                    update_digest(digest, obs)
                    action, probabilities, value = policies[role].predict(obs)
                    with torch.inference_mode():
                        logits, expected_value = pair.models[role](obs)
                    expected = logits.softmax(-1).numpy()
                    np.testing.assert_allclose(probabilities, expected, atol=4e-5, rtol=3e-4)
                    np.testing.assert_allclose(value, float(expected_value), atol=5e-4, rtol=3e-4)
                    assert action == int(obs['active_action_ids'][int(logits.argmax())]), 'Greedy export mismatch'
                    maximum = max(maximum, float(np.max(np.abs(expected - probabilities))))
                    transition = vector.step([action])[0]
                    if transition['terminated'] or transition['truncated']:
                        assert transition['terminated'] and not transition['truncated']
                        assert transition['outcome']['result_type'] == 0, 'Non-normal native battle ending'
                        break
                else:
                    raise AssertionError('Export verification did not end normally')
                vector.close()
                vector = None
            finally:
                if vector:
                    vector.abort()
            records.append(dict(role=role, training_scenario=scenario, steps=step + 1,
                                maximum_probability_error=maximum, outcome=transition['outcome'],
                                full_observation_sha256=digest.hexdigest(), observation_hash_version=2))
            print(records[-1], flush=True)
    assert checksum(checkpoint) == before, 'Checkpoint changed during verification'
    manifest.update(needs_numeric_and_live_validation=False, validation=dict(
        passed=True, records=records, all_workers_exit_zero=True,
        scope='Six training-scenario native battles with the exported opposing role; every controlled decision compares Torch and ONNX probabilities, values and greedy action. Deployment compatibility only, not strength evaluation.'))
    atomic_json(destination / 'manifest.json', manifest)
    print('Selected native export verified', before, flush=True)


if __name__ == '__main__':
    main()
