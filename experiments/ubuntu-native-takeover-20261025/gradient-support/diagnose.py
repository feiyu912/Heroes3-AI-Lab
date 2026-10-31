"""CPU-only TRAIN parameter-support audit; no optimizer or native environment.

Uses exactly the common theta61 and recorded 512-row phase0 TRAIN batch from
the historical observed-MC experiment. No DEV graph enters this analysis.
"""
import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path

import torch

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
sys.path[:0] = [str(PROJECT / 'research'), str(PROJECT / 'experiments/battle-terminal-credit-native-20261023')]
import full_graph_policy as graph
import restore_learner as restore
from masked_ppo import distribution

CHECKPOINT_SHA = '4725dab0332ad93f3806084ce1fc01803e77f5e5ee6ca861d452b63892062840'
PREFIX_SHA = 'fd86a735a7e8597fd3329c999169dfb538cb484743b952bbced04f39751b0d16'
TARGETS_SHA = '46778f1e791f7f06475168f4b857577894c2e520599edfb248fede73dd0f19ac'


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def topology(model, name):
    role = name.split('.')[1]
    key = name.split('.weights.', 1)[1].replace('__', '.')
    match = re.fullmatch(r'gnn\.convs\.2\.(\d+)\.(.+)', key)
    if match:
        edge = model.models[role].edges[int(match[1])]
        return dict(role=role, node_output=edge[2], relation=list(edge), kind='last_layer_relation')
    match = re.fullmatch(r'gnn\.norms\.2\.norms\.(Action|Global)\.(weight|bias)', key)
    if match:
        return dict(role=role, node_output=match[1], kind='last_layer_node_norm')
    raise AssertionError('Unexpected trainable body tensor: ' + name)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--prefix', type=Path, required=True)
    parser.add_argument('--targets', type=Path, default=PROJECT / 'experiments/battle-observed-MC-probe-20261024/MC_TARGETS.pt')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    torch.set_num_threads(2)
    assert not torch.cuda.is_initialized()
    for path, expected in ((args.checkpoint, CHECKPOINT_SHA), (args.prefix, PREFIX_SHA), (args.targets, TARGETS_SHA)):
        assert sha(path) == expected, str(path)
    checkpoint = torch.load(args.checkpoint, map_location='cpu', weights_only=True)
    prefix = torch.load(args.prefix, map_location='cpu', weights_only=False)
    targets = torch.load(args.targets, map_location='cpu', weights_only=False)
    assert checkpoint['finetuning_mode'] == 'last'
    assert prefix['behavior_checkpoint_sha256'] == targets['behavior_sha256'] == CHECKPOINT_SHA
    source_paths = [Path(graph.__file__), PROJECT / 'research/recovered-graph.py']
    source_hashes = {str(path): sha(path) for path in source_paths}
    old_frozen = checkpoint['frozen_inputs']['input_sha256']
    for path in source_paths:
        assert old_frozen['/mnt/g/Heroes3-AI-Lab/research/' + path.name] == sha(path)
    with torch.random.fork_rng(devices=[]):
        model = graph.FullGraphPair(args.checkpoint, 'last').cpu().eval()
    before = restore.digest(model.state_dict())
    rng = torch.get_rng_state().clone()
    named = [(name, parameter) for name, parameter in model.named_parameters()
             if parameter.requires_grad and 'policy_head__' not in name and 'value_head__' not in name]
    assert named
    assert all(('gnn__convs__2__' in name or 'gnn__norms__2__' in name) for name, _ in named)
    structure = {name: topology(model, name) | dict(shape=list(parameter.shape), elements=parameter.numel())
                 for name, parameter in named}
    assert all(item['node_output'] in ('Action', 'Global') for item in structure.values())
    stats = {name: dict(actor_nonzero_batches=0, critic_nonzero_batches=0, tensor_overlap_batches=0,
                       scalar_overlap_elements_total=0, actor_max_nonzero_elements=0, critic_max_nonzero_elements=0,
                       actor_max_norm=0.0, critic_max_norm=0.0) for name, _ in named}
    parameters = [parameter for _, parameter in named]
    observations = prefix['raw']['samples']
    actions = torch.tensor(prefix['raw']['actions'])
    old_logp = torch.tensor(prefix['raw']['old_logp'])
    assert len(observations) == 512
    rows = []
    maximum_logp_error = 0.0
    for target in ('reference', 'mc'):
        advantages = torch.as_tensor(targets[target + '_advantages'].reshape(-1))
        advantages = (advantages - advantages.mean()) / advantages.std(unbiased=False).clamp_min(1e-8)
        returns = torch.as_tensor(targets[target + '_returns'].reshape(-1))
        for start in range(0, 512, 16):
            batch = graph.collate(observations[start:start + 16], 'cpu')
            logits, values = model(*batch)
            dist = distribution(logits, batch[-1])
            logp = dist.log_prob(actions[start:start + 16])
            error = float((logp - old_logp[start:start + 16]).abs().max().detach())
            maximum_logp_error = max(maximum_logp_error, error)
            assert error < 2e-4
            ratio = (logp - old_logp[start:start + 16]).exp()
            actor = -torch.minimum(ratio * advantages[start:start + 16],
                                   ratio.clamp(.8, 1.2) * advantages[start:start + 16]).mean() - .005 * dist.entropy().mean()
            critic = .5 * ((values - returns[start:start + 16]) ** 2).mean()
            actor_grad = torch.autograd.grad(actor, parameters, retain_graph=True, allow_unused=True)
            critic_grad = torch.autograd.grad(critic, parameters, allow_unused=True)
            current = {role: dict(target=target, chronological_batch=start // 16, role=role,
                                  actor_nonzero_tensors=0, critic_nonzero_tensors=0, tensor_support_intersection=0,
                                  scalar_support_intersection=0, actor_norm_squared=0.0,
                                  critic_norm_squared=0.0, dot=0.0) for role in ('attacker', 'defender')}
            for (name, parameter), actor_g, critic_g in zip(named, actor_grad, critic_grad):
                if actor_g is not None:
                    assert torch.isfinite(actor_g).all()
                if critic_g is not None:
                    assert torch.isfinite(critic_g).all()
                actor_nonzero = int(torch.count_nonzero(actor_g)) if actor_g is not None else 0
                critic_nonzero = int(torch.count_nonzero(critic_g)) if critic_g is not None else 0
                overlap = int(torch.count_nonzero((actor_g != 0) & (critic_g != 0))) if actor_g is not None and critic_g is not None else 0
                actor_norm = float(torch.linalg.vector_norm(actor_g.double())) if actor_g is not None else 0.0
                critic_norm = float(torch.linalg.vector_norm(critic_g.double())) if critic_g is not None else 0.0
                item = structure[name]
                if actor_nonzero:
                    assert item['node_output'] == 'Action', name
                if critic_nonzero:
                    assert item['node_output'] == 'Global', name
                summary = stats[name]
                summary['actor_nonzero_batches'] += bool(actor_nonzero)
                summary['critic_nonzero_batches'] += bool(critic_nonzero)
                summary['tensor_overlap_batches'] += bool(actor_nonzero and critic_nonzero)
                summary['scalar_overlap_elements_total'] += overlap
                summary['actor_max_nonzero_elements'] = max(summary['actor_max_nonzero_elements'], actor_nonzero)
                summary['critic_max_nonzero_elements'] = max(summary['critic_max_nonzero_elements'], critic_nonzero)
                summary['actor_max_norm'] = max(summary['actor_max_norm'], actor_norm)
                summary['critic_max_norm'] = max(summary['critic_max_norm'], critic_norm)
                row = current[item['role']]
                row['actor_nonzero_tensors'] += bool(actor_nonzero)
                row['critic_nonzero_tensors'] += bool(critic_nonzero)
                row['tensor_support_intersection'] += bool(actor_nonzero and critic_nonzero)
                row['scalar_support_intersection'] += overlap
                row['actor_norm_squared'] += actor_norm ** 2
                row['critic_norm_squared'] += critic_norm ** 2
                if actor_g is not None and critic_g is not None:
                    row['dot'] += float((actor_g.double() * critic_g.double()).sum())
            for row in current.values():
                assert row['tensor_support_intersection'] == row['scalar_support_intersection'] == 0
                aa, vv = row.pop('actor_norm_squared'), row.pop('critic_norm_squared')
                row['actor_norm'] = math.sqrt(aa)
                row['weighted_critic_norm'] = math.sqrt(vv)
                row['cosine'] = row['dot'] / math.sqrt(aa * vv) if aa and vv else None
                rows.append(row)
            (args.out / 'PROGRESS.json').write_text(json.dumps(dict(target=target, processed_TRAIN_rows=start + 16)))
    assert restore.digest(model.state_dict()) == before
    assert torch.equal(rng, torch.get_rng_state())
    assert all(parameter.grad is None for parameter in model.parameters())
    assert not torch.cuda.is_initialized()
    support = {}
    for role in ('attacker', 'defender'):
        names = [name for name in structure if structure[name]['role'] == role]
        actor_names = [name for name in names if stats[name]['actor_nonzero_batches']]
        critic_names = [name for name in names if stats[name]['critic_nonzero_batches']]
        intersection = sorted(set(actor_names) & set(critic_names))
        assert not intersection
        support[role] = dict(trainable_body_tensors=len(names),
                             topology_Action_tensors=sum(structure[name]['node_output'] == 'Action' for name in names),
                             topology_Global_tensors=sum(structure[name]['node_output'] == 'Global' for name in names),
                             actor_nonzero_tensor_names=actor_names, critic_nonzero_tensor_names=critic_names,
                             union_tensor_intersection=intersection,
                             all_checked_batches=64)
    report = dict(passed=True, environment='native Ubuntu CPU', source_sha256=source_hashes,
                  checkpoint=dict(path=str(args.checkpoint), sha256=CHECKPOINT_SHA),
                  prefix=dict(path=str(args.prefix), sha256=PREFIX_SHA),
                  targets=dict(path=str(args.targets), sha256=TARGETS_SHA),
                  script_sha256=sha(__file__), finetuning_mode='last', TRAIN_rows=512,
                  target_variants=['reference_lambda095', 'MC_lambda1'], chronological_groups_per_variant=32,
                  role_summaries=support, parameter_topology_and_support={name: structure[name] | stats[name] for name in structure},
                  rows=rows, maximum_CPU_behavior_logp_error=maximum_logp_error,
                  model_unchanged=True, CPU_RNG_unchanged=True, parameter_grads_unpopulated=True,
                  GPU_initialized=False, optimizer_steps=0, new_native_games=0, DEV_rows_used=0,
                  scope='Exact nonzero supports at common theta61, both targets, 32 chronological16-row TRAIN batches. '
                        'Source topology separates final Action/Global relation and node-norm tensors because earlier blocks are frozen. '
                        'Global gradient clipping still couples magnitudes. No claim about actual shuffled optimizer gradients, later weights, '
                        'fully unfrozen models, or a causal explanation of evaluation wins.')
    (args.out / 'AUDIT.json').write_text(json.dumps(report, indent=2))
    print(json.dumps({key: value for key, value in report.items() if key not in ('rows', 'parameter_topology_and_support')}, indent=2))


if __name__ == '__main__':
    main()
