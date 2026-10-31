"""Keep simulator subprocesses free of the trainer's Torch/CUDA dependency."""
from pathlib import Path

root = Path('/mnt/g/Heroes3-AI-Lab/research')
path = root / 'decision_model.py'
text = path.read_text()
if 'from battle_features import' not in text:
    start = text.index('FEATURE_VERSION =')
    end = text.index('def collate(')
    (root / 'battle_features.py').write_text('"""NumPy-only v15 feature extraction for isolated simulator workers."""\nimport numpy as np\n\n' + text[start:end])
    text = text[:start] + 'from battle_features import FEATURE_VERSION, ENTITY_DIM, CANDIDATE_DIM, features\n\n\n' + text[end:]
    path.write_text(text)
path = root / 'vector_env.py'
text = path.read_text().replace('from decision_model import features', 'from battle_features import features')
path.write_text(text)
path = root / 'train-ppo.py'
text = path.read_text()
for line in ['import torch\n', 'from decision_model import collate, load_model, save_model\n', 'from masked_ppo import distribution, gae, update\n']:
    if line in text:
        text = text.replace(line, '', 1)
if '    import torch\n' not in text:
    text = text.replace('def main():\n', 'def main():\n    import torch\n    from decision_model import collate, load_model, save_model\n    from masked_ppo import distribution, gae, update\n')
path.write_text(text)
print('Simulator feature extraction no longer imports Torch')
