"""Check actual source demonstrations round-trip without fabricating features."""
import json
from pathlib import Path
import importlib.util
import numpy as np
import torch
from graph_observation_codec import unpack
from lab_io import atomic_json
from evaluation_provenance import digest

here=Path(__file__).resolve().parent
path=here/'wait-variant-v2/candidate-bc-train.jsonl'
rows=[json.loads(line) for line in path.read_text().splitlines() if line.strip()]
assert len(rows)==4
observations=[]
empty=0
for row in rows:
    obs=unpack(row['observation'],row['actor_side'])
    for name,original in row['observation']['nodes'].items():
        assert obs['nodes'][name].tolist()==original
    for edge in row['observation']['edges']:
        restored=obs['edges'][tuple(edge['relation'])]
        assert restored['index'].tolist()==edge['index']
        assert restored['attrs'].tolist()==edge['attrs']
        assert restored['attrs'].ndim==2
        empty+=int(restored['attrs'].shape[0]==0)
    assert row['action'] in obs['active_action_ids']
    observations.append(obs)
torch.set_num_threads(1)
spec=importlib.util.spec_from_file_location('codec_graph',here.parents[1]/'research/recovered-graph.py')
graph=importlib.util.module_from_spec(spec);spec.loader.exec_module(graph)
pair=graph.RecoveredPair('/root/heroes3-ai-lab/models/graph-finetune/1792068859379237126/update-64.pt').eval()
cached=pair.encode_features(observations)
with torch.inference_mode():logits,values=pair(*graph.head_collate(cached))
mask=graph.head_collate(cached)[-1]
assert torch.isfinite(logits[mask]).all() and torch.isfinite(values).all()
atomic_json(here/'graph-codec-check.json',dict(passed=True,samples=len(rows),empty_relations_restored=empty,
    nodes_and_edge_values_preserved=True,real_cpu_batch_forward_finite=True,dataset_sha256=digest(path),
    codec_sha256=digest(here/'graph_observation_codec.py'),scope='Actual source demo roundtrip and model compatibility; not tactical efficacy'))
print('Actual four source demonstrations restored and CPU encoded successfully')
