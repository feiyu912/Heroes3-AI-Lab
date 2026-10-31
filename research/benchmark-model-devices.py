import argparse
import json
from pathlib import Path
import time
import numpy as np
import torch
from decision_model import DecisionModel

parser = argparse.ArgumentParser()
parser.add_argument('--input', required=True)
parser.add_argument('--output', required=True)
args = parser.parse_args()
torch.set_num_threads(2)
torch.set_num_interop_threads(1)
assert torch.cuda.is_available()
archive = np.load(args.input, allow_pickle=False)
records = []
for architecture in ['mlp', 'attention', 'gnn']:
    for batch_size in [1, 12, 32, 64, 256]:
        cpu_input = tuple(torch.from_numpy(archive[f'{batch_size}-{i}']) for i in range(5))
        for device in ['cpu', 'cuda']:
            torch.manual_seed(20261014)
            model = DecisionModel(architecture).to(device).eval()
            input_values = tuple(v.to(device) for v in cpu_input)
            sync = lambda: torch.cuda.synchronize() if device == 'cuda' else None
            if device == 'cuda':
                torch.cuda.reset_peak_memory_stats()
            for _ in range(5):
                with torch.inference_mode():
                    model(*input_values)
            sync()
            timings = []
            with torch.inference_mode():
                for _ in range(20):
                    start = time.perf_counter()
                    values = tuple(v.to(device) for v in cpu_input)
                    logits, value = model(*values)
                    logits.argmax(1).cpu()
                    value.cpu()
                    sync()
                    timings.append(1000 * (time.perf_counter()-start))
            row = dict(architecture=architecture, batch=batch_size, device=device,
                       inference_including_transfer_ms_p50=float(np.median(timings)))
            if batch_size >= 32:
                model.train()
                optimizer = torch.optim.Adam(model.parameters(), lr=3e-4)
                labels = input_values[-1].float().argmax(1)
                timings = []
                for i in range(25):
                    start = time.perf_counter()
                    values = tuple(v.to(device) for v in cpu_input)
                    logits, value = model(*values)
                    loss = torch.nn.functional.cross_entropy(logits, labels) + value.square().mean()
                    optimizer.zero_grad(set_to_none=True)
                    loss.backward()
                    optimizer.step()
                    sync()
                    if i >= 5:
                        timings.append(1000 * (time.perf_counter()-start))
                row['update_including_transfer_ms_p50'] = float(np.median(timings))
            if device == 'cuda':
                row['cuda_peak_allocated_mib'] = torch.cuda.max_memory_allocated() / 1024**2
            records.append(row)
            print(row, flush=True)
            Path(args.output).write_text(json.dumps(dict(torch_version=torch.__version__,
                                                        gpu=torch.cuda.get_device_name(0), cpu_threads=2,
                                                        warmup=5, repetitions=20, records=records), indent=2))
