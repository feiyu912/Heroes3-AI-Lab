"""Decode all original pilot records and CPU-encode eligible expert winners."""
import gzip
import importlib.util
import json
from pathlib import Path
import time
import torch
from lab_io import atomic_json
from recovery_utils import HERE,V1,RESEARCH,KNOWLEDGE,read,digest,training_rows,eligible_sources,unpack,frozen_recovery

INITIAL = '/root/heroes3-ai-lab/models/graph-finetune/1792068859379237126/update-64.pt'


def main():
    torch.set_num_threads(1)
    started = time.monotonic()
    original = [V1/name for name in ['run_pilot.py','train_bc.py','run_episode.py','experts.py',
        'generate_scenarios.py','test_experts.py','pilot-control.json','bc-training.log',
        'pilot-training-battles.json','scenarios.json']]
    for name,archive in [('pilot-control.json','original-pilot-control.failed.json'),
                         ('bc-training.log','original-bc-training.failed.log')]:
        destination = HERE/archive
        if destination.exists():
            assert destination.read_bytes()==(V1/name).read_bytes(), 'Preserve earlier failure archive'
        else:
            with destination.open('xb') as stream:
                stream.write((V1/name).read_bytes())
    rows = training_rows(INITIAL)
    decisions = empty_edges = 0
    for row in rows:
        original.extend([V1/'runs'/(row['battle_id']+'.json'),Path(row['demonstrations'])])
        with gzip.open(row['demonstrations'],'rt') as stream:
            data = json.load(stream)
        for record in data['decisions']:
            observation = unpack(record['observation'],record['actor_side'])
            for edge in observation['edges'].values():
                assert edge['index'].ndim==2 and edge['index'].shape[0]==2
                assert edge['attrs'].ndim==2 and edge['attrs'].shape[0]==edge['index'].shape[1]
                empty_edges += edge['index'].shape[1]==0
            assert all(array.ndim==2 for array in observation['nodes'].values())
            decisions += 1
    observations,labels,sources = eligible_sources(INITIAL)
    spec = importlib.util.spec_from_file_location('recovery_cpu_graph',RESEARCH/'recovered-graph.py')
    graph = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(graph)
    pair = graph.RecoveredPair(INITIAL).cpu().eval()
    cached = []
    with torch.inference_mode():
        for start in range(0,len(observations),8):
            features = pair.encode_features(observations[start:start+8])
            for observation,feature in zip(observations[start:start+8],features):
                assert feature[0].shape==(len(observation['active_action_ids']),64)
                assert feature[1].shape==(64,)
                assert torch.isfinite(torch.as_tensor(feature[0])).all()
            cached.extend(features)
        for start in range(0,len(cached),16):
            batch = graph.head_collate(cached[start:start+16],'cpu')
            logits,values = pair(*batch)
            assert torch.isfinite(logits[batch[-1]]).all() and torch.isfinite(values).all()
            target = torch.tensor(labels[start:start+16])
            assert batch[-1].gather(1,target[:,None]).all()
            assert torch.isfinite(torch.nn.functional.cross_entropy(logits,target))
    result = dict(passed=True,device='cpu',original_episodes=len(rows),decoded_decisions=decisions,
        restored_empty_edge_relations=empty_edges,eligible_normal_win_expert_episodes=len(sources),
        eligible_samples=len(cached),roles=sorted({observation['lab_side'] for observation in observations}),
        source_episodes=sources,codec_sha256=digest(KNOWLEDGE/'graph_observation_codec.py'),
        simulator_started=False,GPU_started=False,wall_seconds=time.monotonic()-started,
        quality='Q2 exploratory candidates, not validated tactic or human demonstrations')
    atomic_json(HERE/'cpu-preflight.json',result)
    manifest = dict(recovery_version='human-tactics-recovery-v2',cpu_preflight_passed=True,
        cpu_preflight_sha256=digest(HERE/'cpu-preflight.json'),original_artifacts={str(path):digest(path) for path in original},
        recovery_artifacts=frozen_recovery(),
        fix='Restore native-schema empty graph dimensions, retain all original data and original frozen run_episode.py',
        source_data= str(V1), future_BC_report=str(V1/'bc-training.json'),
        original_failed_control_preserved=True,original_failed_log_preserved=True)
    atomic_json(HERE/'recovery-manifest.json',manifest)
    print(json.dumps(result),flush=True)


if __name__ == '__main__':
    main()
