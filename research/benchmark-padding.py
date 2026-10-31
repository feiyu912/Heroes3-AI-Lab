import json
from pathlib import Path
import time
import numpy as np
import torch
from decision_model import load_dataset, load_model, collate

torch.set_num_threads(2)
torch.set_num_interop_threads(1)
data = load_dataset('/root/heroes3-ai-lab/datasets/teacher-balanced-v1', 'validation')
rng = np.random.default_rng(20261014)
indices = rng.choice(len(data), size=1024, replace=False)
features = [data[i]['features'] for i in indices]
model, _ = load_model('/root/heroes3-ai-lab/models/ppo-1791984957445079862/latest.pt')
model.cuda().eval()
rows = []
for batch_size in [32, 64, 128, 256]:
    for scheme in ['random-padded', 'candidate-count-buckets']:
        for repeat in range(3):
            start = time.perf_counter()
            order = np.arange(len(features))
            if scheme == 'candidate-count-buckets':
                order = np.array(sorted(order, key=lambda i: len(features[i][1])))
            padded = real = 0
            logits_checksum = 0.0
            with torch.inference_mode():
                for offset in range(0, len(order), batch_size):
                    samples = [features[i] for i in order[offset:offset+batch_size]]
                    padded += len(samples) * max(len(s[1]) for s in samples)
                    real += sum(len(s[1]) for s in samples)
                    inputs = collate(samples, 'cuda')
                    logits, value = model(*inputs)
                    assert torch.isfinite(logits[inputs[-1]]).all()
                    logits_checksum += logits[inputs[-1]].sum().item()
            torch.cuda.synchronize()
            elapsed = time.perf_counter()-start
            row = dict(batch_size=batch_size, scheme=scheme, repeat=repeat,
                       wall_seconds=elapsed, states_per_second=len(features)/elapsed,
                       real_candidates=real, padded_candidate_slots=padded,
                       padding_fraction=1-real/padded, logits_checksum=logits_checksum)
            rows.append(row)
            print(row, flush=True)
Path('/mnt/g/Heroes3-AI-Lab/research/padding-benchmark.json').write_text(json.dumps(dict(
    scope='Same1024real validation states, GNN checkpoint; FP32 GPU inference including CPU collation/transfer and sorting;3 repeats; warmup effects retained in first repeat', rows=rows), indent=2))
