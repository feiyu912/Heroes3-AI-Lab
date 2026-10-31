"""Create an isolated derivative; never rewrite the original running trainer."""
import hashlib
from pathlib import Path
from lab_io import atomic_json

here=Path(__file__).resolve().parent
source=here.parents[1]/'research/train-recovered-heads.py'
text=source.read_text()


def replace(old,new):
    global text
    assert text.count(old)==1,(old,text.count(old))
    text=text.replace(old,new)


replace('    import torch\n','    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")\n    import torch\n')
replace('    from masked_ppo import gae,distribution,update','    from masked_ppo import gae,distribution\n    from reference_ppo import update,encode_reference')
replace("    p.add_argument('--workers'", "    p.add_argument('--reference-coef',type=float,default=.1)\n    p.add_argument('--workers'")
replace('    torch.set_num_threads(2);torch.manual_seed(args.seed)',
    '    torch.set_num_threads(2);torch.manual_seed(args.seed)\n    torch.use_deterministic_algorithms(True)')
replace('    fixed_opponent=configure_training(args,graph,pair)',
    '''    fixed_opponent=configure_training(args,graph,pair)
    assert fixed_opponent is not None, 'Use explicit MMAI_GPU to share a frozen public reference'
    reference=fixed_opponent.pair
    assert all(not p.requires_grad for p in reference.parameters())
    args.reference_checkpoint=args.fixed_opponent_checkpoint
    reference_versions=[p._version for p in reference.parameters()]''')
replace("folder=Path('/root/heroes3-ai-lab/models/recovered-ppo')/run_id",
    "folder=Path('/root/heroes3-ai-lab/models/conservative-ppo-v1')/run_id")
replace("    source_snapshot=capture_source(folder,'train-recovered-heads.py')",
    '''    source_snapshot=capture_source(folder,'train-recovered-heads.py')
    import shutil,hashlib
    extra=[]
    for path in [Path(__file__),Path(__file__).with_name('reference_ppo.py')]:
        target=Path(source_snapshot)/path.name;shutil.copyfile(path,target)
        extra.append(dict(file=path.name,sha256=hashlib.sha256(target.read_bytes()).hexdigest()))
    atomic_json(Path(source_snapshot)/'conservative-source.json',dict(actual_trainer=Path(__file__).name,
        files=extra,original_trainer_copy='train-recovered-heads.py',
        reference_checkpoint=args.reference_checkpoint,
        reference_sha256=hashlib.sha256(Path(args.reference_checkpoint).read_bytes()).hexdigest()))''')
replace('            samples=[];actions=[];old_logp=[];values=[];next_values=[];rewards=[];terminated=[];truncated=[]',
    '            samples=[];actions=[];old_logp=[];values=[];next_values=[];rewards=[];terminated=[];truncated=[]\n            reference_log_probs=[];reference_action_ids=[];candidate_action_ids=[]')
replace("            for _ in range(args.rollout):\n                with torch.inference_mode():",
    '''            for _ in range(args.rollout):
                raw=[state['features'] for state in vector.states]
                encoded_reference=encode_reference(reference,raw,graph.head_collate,batch_size=args.workers)
                reference_log_probs.extend(encoded_reference['log_probs'])
                reference_action_ids.extend(encoded_reference['action_ids'])
                candidate_action_ids.extend([sample[2].tolist() for sample in current])
                with torch.inference_mode():''')
replace('                recompute_atol=2e-4,recompute_rtol=0.)',
    '''                recompute_atol=2e-4,recompute_rtol=0.,recompute_batch_size=args.workers,
                collate_fn=graph.head_collate,reference_coef=args.reference_coef,
                reference_log_probs=reference_log_probs,reference_action_ids=reference_action_ids,
                candidate_action_ids=candidate_action_ids,reference_parameters=tuple(reference.parameters()))
            assert reference_versions==[p._version for p in reference.parameters()]''')
replace("                wins+=sum(s['terminated'] and s['reward']>0 for s in transitions)",
    "                wins+=sum(s['terminated'] and not s['truncated'] and s['outcome'] and s['outcome']['result_type']==0 and s['outcome']['winner']==int(config['role']=='defender') for s,config in zip(transitions,configs))")
replace("pair.save(str(folder/f'update-{previous_updates+iteration+1}.pt'),completed_updates=previous_updates+iteration+1,",
    "pair.save(str(folder/f'update-{previous_updates+iteration+1}.pt'),finetuning_mode='heads',algorithm='reference-PPO',completed_updates=previous_updates+iteration+1,")
replace("wall_seconds=time.monotonic()-started,source='Official v15 attacker/defender, frozen graph encoder, head-only PPO')",
    "wall_seconds=time.monotonic()-started,CUDA_training=True,source='Public v15 frozen graph, conservative head-only PPO with independent frozen reference KL')")
destination=here/'train_conservative_heads.py'
assert not destination.exists(), 'Preserve previously generated source; review changes explicitly'
destination.write_text(text)
atomic_json(here/'trainer-derivation.json',dict(source=str(source),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
    derivative=str(destination),derivative_sha256=hashlib.sha256(destination.read_bytes()).hexdigest(),
    original_modified=False,trained=False,method='Independent raw-observation public reference KL; frozen graph and 24-worker rollout recomputation'))
print('Created isolated trainer; not launched')
