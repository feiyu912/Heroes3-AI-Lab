"""Small CUDA behavior-cloning pilot on outcome-filtered training episodes."""
import argparse
import fcntl
import gzip
import importlib.util
import json
import os
from pathlib import Path
import time
import torch
from lab_io import atomic_json
from evaluation_provenance import digest
from run_episode import unpack


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--checkpoint', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--steps', type=int, default=60)
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    research = here.parents[1]/'research'
    with Path('/root/heroes3-ai-lab/evaluations/.pool-lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        for entry in Path('/proc').iterdir():
            if not entry.name.isdigit():
                continue
            try:
                command = (entry/'cmdline').read_bytes().split(b'\0')
            except OSError:
                continue
            assert not (len(command)>1 and Path(os.fsdecode(command[1])).name in
                        ['train-graph-finetune.py', 'train-recovered-heads.py']), 'Preserve one GPU learner'
        assert torch.cuda.is_available()
        torch.set_num_threads(2)
        torch.manual_seed(2026102901)
        spec = importlib.util.spec_from_file_location('tactic_bc_graph', research/'recovered-graph.py')
        graph = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(graph)
        pair = graph.RecoveredPair(args.checkpoint).cuda().eval()
        observations, labels, sources = [], [], []
        conditions = set()
        for path in sorted((here/'runs').glob('expert-*-train-*.json')):
            episode = json.loads(path.read_text())
            if not episode.get('completed') or episode.get('split')!='train' or not episode['success']:
                continue
            condition = (episode['scenario'],episode['role'],episode['seed'],episode['policy'])
            if condition in conditions:
                continue
            conditions.add(condition)
            with gzip.open(episode['demonstrations'], 'rt') as stream:
                data = json.load(stream)
            assert digest(episode['demonstrations']) == episode['demonstration_sha256']
            for record in data['decisions']:
                assert record['expert_action'] in record['legal_actions']
                observations.append(unpack(record['observation'], record['actor_side']))
                labels.append(record['legal_actions'].index(record['expert_action']))
            sources.append(dict(report=str(path), sha256=digest(path), samples=len(data['decisions']),
                filter='normal win; coverage/search teacher remains potentially suboptimal'))
        assert observations and {obs['lab_side'] for obs in observations} == {0,1}, 'Need eligible examples for both roles'
        started = time.monotonic()
        cached = []
        for start in range(0, len(observations), 8):
            cached.extend(pair.encode_features(observations[start:start+8]))
        head_names = [name for name, parameter in pair.named_parameters() if 'policy_head__' in name]
        before = {name: parameter.detach().cpu().clone() for name, parameter in pair.named_parameters()}
        for name, parameter in pair.named_parameters():
            parameter.requires_grad_(name in head_names)
        optimizer = torch.optim.Adam([parameter for parameter in pair.parameters() if parameter.requires_grad], lr=1e-4)
        def loss_for(indices):
            batch = graph.head_collate([cached[i] for i in indices], 'cuda')
            logits, _ = pair(*batch)
            return torch.nn.functional.cross_entropy(logits, torch.tensor([labels[i] for i in indices], device='cuda'))
        def mean_loss():
            with torch.inference_mode():
                values = [float(loss_for(list(range(start,min(start+16,len(cached))))))*min(16,len(cached)-start)
                          for start in range(0,len(cached),16)]
            return sum(values)/len(cached)
        initial = mean_loss()
        losses = []
        for _ in range(args.steps):
            indices = torch.randint(len(cached), (min(16,len(cached)),)).tolist()
            loss = loss_for(indices)
            assert torch.isfinite(loss)
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            norm = torch.nn.utils.clip_grad_norm_(pair.parameters(), 0.5)
            assert torch.isfinite(norm)
            optimizer.step()
            losses.append(float(loss.detach()))
        final = mean_loss()
        assert final < initial, 'Small BC pilot failed to learn its training labels'
        changed = []
        for name, parameter in pair.named_parameters():
            if not torch.equal(before[name],parameter.detach().cpu()):
                changed.append(name)
                assert name in head_names, 'BC changed frozen graph or value head'
        assert changed
        output = Path(args.output)
        output.parent.mkdir(parents=True,exist_ok=True)
        bundle = dict(models={role: dict(weights={key.replace('__','.'):value.detach().cpu()
            for key,value in model.weights.items()}, metadata=model.metadata) for role,model in pair.models.items()},
            source='Human Tactics v1: coverage/search demonstrations, supervised policy-head adaptation',
            algorithm='BC', finetuning_mode='heads', completed_updates=0, environment_steps=0,
            bc_steps=args.steps, config=vars(args), optimizer_state_dict=optimizer.state_dict(),
            torch_rng_state=torch.get_rng_state(), cuda_rng_states=torch.cuda.get_rng_state_all(),
            resume_note='BC optimizer is not a PPO optimizer. Start PPO with fresh optimizer from these weights.')
        temporary = output.with_name(output.name+'.tmp')
        torch.save(bundle,temporary)
        with temporary.open('rb') as stream:
            os.fsync(stream.fileno())
        os.replace(temporary,output)
        loaded = torch.load(output,map_location='cpu',weights_only=True)
        assert loaded['algorithm']=='BC'
        report = dict(completed=True, CUDA_training=True, checkpoint=str(output), sha256=digest(output),
            initial_checkpoint=args.checkpoint, initial_sha256=digest(args.checkpoint),
            samples=len(cached), source_episodes=sources, gradient_steps=args.steps,
            initial_training_nll=initial, final_training_nll=final, changed_policy_parameters=len(changed),
            graph_and_value_weights_unchanged=True, wall_seconds=time.monotonic()-started,
            generalization_proven=False, human_video_trajectories_used=False,
            limitations='Learning these labels is only a fit check, not evidence of better tactics or battle strength.')
        atomic_json(here/'bc-training.json',report)
        print(json.dumps(report),flush=True)


if __name__ == '__main__':
    main()
