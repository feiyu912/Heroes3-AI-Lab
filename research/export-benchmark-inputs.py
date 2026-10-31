import numpy as np
from decision_model import load_dataset, collate
samples = load_dataset('/root/heroes3-ai-lab/datasets/teacher-v2', 'train')
arrays = {}
for batch in [1, 12, 32, 64, 256]:
    values = collate([samples[i % len(samples)]['features'] for i in range(batch)])
    for index, value in enumerate(values):
        arrays[f'{batch}-{index}'] = value.numpy()
np.savez_compressed('/mnt/g/Heroes3-AI-Lab/research/gpu-benchmark-inputs.npz', **arrays)
print('Exported real v15 candidate batches')
