"""Original timeout seed and learned weights under repaired native target protocol."""
import fcntl
import json
from pathlib import Path
import random
import torch
from model import load_checkpoint
from train_ppo_pilot import collect, sha, atomic_json

HERE = Path(__file__).resolve().parent
out = HERE / 'takeover-03/timeout-regression-01'
out.mkdir(exist_ok=False)
torch.set_num_threads(1)
torch.use_deterministic_algorithms(True)
source = HERE / 'ppo-pilot-02/update-2.pt'
runtime = Path('/root/heroes3-ai-lab/src/vcmi-adv-build/bin')
files = [source, Path(__file__), HERE / 'train_ppo_pilot.py', HERE / 'model.py', HERE / 'encoder.py',
         HERE.parent / 'adventure_runner_v5.py'] + [runtime / n for n in ['vcmiclient', 'vcmiserver', 'libvcmi.so']]
hashes = {str(p): sha(p) for p in files}
atomic_json(out / 'plan.json', dict(hashes=hashes, protocol_change='Native within-turn target commitment and visible neutral army clearance.',
    optimizer_steps=0, CUDA_training=False, training_samples_accepted=False, independent_evaluation=False))
with Path('/root/heroes3-ai-lab/evaluations/.gpu-learner-lock').open('a') as lock:
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    model = load_checkpoint(source, 'cuda')
    bundle = torch.load(source, map_location='cpu', weights_only=True)
    torch.set_rng_state(bundle['torch_rng'])
    torch.cuda.set_rng_state_all(bundle['cuda_rng'])
    random.setstate(bundle['python_rng'])
    rows, episode = collect(model, dict(map='Maps/adv/takeover-v2-train-01-mines', red='DirectorAI',
        blue='EmptyAI', seed=2026101930), out / 'episode', torch.device('cuda'))
    unchanged = all(sha(Path(p)) == h for p, h in hashes.items())
    atomic_json(out / 'result.json', dict(episode=episode, inputs_unchanged=unchanged,
        CUDA_training=False, optimizer_steps=0, training_samples_accepted=False,
        passed=bool(episode['valid'] and unchanged), note='Engineering regression only; no learning gain inferred.'))
    print(json.dumps(dict(valid=episode['valid'], reward=episode['reward'], decisions=episode['decisions'],
        turns=episode['native'].get('turns'), run_dir=episode['native'].get('run_dir'))), flush=True)
