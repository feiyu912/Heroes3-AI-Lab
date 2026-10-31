"""Recovery-only Q2 policy-head BC using shape-safe decoded original episodes."""
import argparse
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import time
import torch
from lab_io import atomic_json
from recovery_utils import HERE,V1,RESEARCH,digest,eligible_sources,frozen_recovery


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--checkpoint',required=True)
    parser.add_argument('--output',required=True)
    parser.add_argument('--steps',type=int,default=60)
    args = parser.parse_args()
    output = Path(args.output)
    assert not output.exists() and not (V1/'bc-training.json').exists(), 'Never overwrite prior model or BC report'
    with Path('/root/heroes3-ai-lab/evaluations/.pool-lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        for entry in Path('/proc').iterdir():
            if not entry.name.isdigit() or int(entry.name)==os.getpid():
                continue
            try:
                command = (entry/'cmdline').read_bytes().split(b'\0')
            except OSError:
                continue
            names = [Path(os.fsdecode(value)).name for value in command[:4]]
            assert not any(name.startswith(('train-graph-finetune','train-recovered-heads','train-reference','train-conservative'))
                           for name in names), 'Preserve one GPU learner'
        assert torch.cuda.is_available()
        torch.set_num_threads(2)
        torch.manual_seed(2026102901)
        frozen = frozen_recovery()
        observations,labels,sources = eligible_sources(args.checkpoint)
        spec = importlib.util.spec_from_file_location('recovery_bc_graph',RESEARCH/'recovered-graph.py')
        graph = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(graph)
        pair = graph.RecoveredPair(args.checkpoint).cuda().eval()
        started = time.monotonic()
        cached = []
        for start in range(0,len(observations),8):
            cached.extend(pair.encode_features(observations[start:start+8]))
        heads = [name for name,_ in pair.named_parameters() if 'policy_head__' in name]
        before = {name:parameter.detach().cpu().clone() for name,parameter in pair.named_parameters()}
        for name,parameter in pair.named_parameters():
            parameter.requires_grad_(name in heads)
        optimizer = torch.optim.Adam([parameter for parameter in pair.parameters() if parameter.requires_grad],lr=1e-4)
        def loss_for(indices):
            batch = graph.head_collate([cached[index] for index in indices],'cuda')
            logits,_ = pair(*batch)
            return torch.nn.functional.cross_entropy(logits,torch.tensor([labels[index] for index in indices],device='cuda'))
        def mean_loss():
            with torch.inference_mode():
                values = [float(loss_for(list(range(start,min(start+16,len(cached))))))*min(16,len(cached)-start)
                          for start in range(0,len(cached),16)]
            return sum(values)/len(cached)
        initial = mean_loss()
        for _ in range(args.steps):
            indices = torch.randint(len(cached),(min(16,len(cached)),)).tolist()
            loss = loss_for(indices)
            assert torch.isfinite(loss)
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            norm = torch.nn.utils.clip_grad_norm_(pair.parameters(),.5)
            assert torch.isfinite(norm)
            optimizer.step()
        final = mean_loss()
        assert final < initial, 'BC did not fit the Q2 training labels'
        changed = []
        for name,parameter in pair.named_parameters():
            if not torch.equal(before[name],parameter.detach().cpu()):
                changed.append(name)
                assert name in heads, 'Frozen graph or value weights changed'
        assert changed
        assert frozen_recovery()==frozen, 'Recovery implementation changed during BC'
        bundle = dict(models={role:dict(weights={key.replace('__','.'):value.detach().cpu()
            for key,value in model.weights.items()},metadata=model.metadata) for role,model in pair.models.items()},
            source='Human tactics v1 Q2 exploratory coverage/search BC; codec recovery v2',
            algorithm='BC',finetuning_mode='heads',completed_updates=0,environment_steps=0,
            bc_steps=args.steps,config=vars(args),optimizer_state_dict=optimizer.state_dict(),
            torch_rng_state=torch.get_rng_state(),cuda_rng_states=torch.cuda.get_rng_state_all(),
            resume_note='BC optimizer is not a PPO optimizer; use fresh PPO optimizer.')
        output.parent.mkdir(parents=True,exist_ok=True)
        temporary = output.with_name(output.name+'.tmp')
        assert not temporary.exists()
        torch.save(bundle,temporary)
        with temporary.open('rb') as stream:
            os.fsync(stream.fileno())
        os.replace(temporary,output)
        loaded = torch.load(output,map_location='cpu',weights_only=True)
        assert loaded['algorithm']=='BC'
        report = dict(completed=True,CUDA_training=True,checkpoint=str(output),sha256=digest(output),
            initial_checkpoint=args.checkpoint,initial_sha256=digest(args.checkpoint),
            samples=len(cached),source_episodes=sources,gradient_steps=args.steps,
            initial_training_nll=initial,final_training_nll=final,changed_policy_parameters=len(changed),
            graph_and_value_weights_unchanged=True,wall_seconds=time.monotonic()-started,
            recovery_version='human-tactics-recovery-v2',recovery_artifacts=frozen,
            generalization_proven=False,human_video_trajectories_used=False,quality_tier='Q2-exploratory',
            limitations='Label fit only, not Q3 teacher strength or tactic competence; original failure preserved.')
        atomic_json(V1/'bc-training.json',report)
        print(json.dumps(report),flush=True)


if __name__ == '__main__':
    main()
