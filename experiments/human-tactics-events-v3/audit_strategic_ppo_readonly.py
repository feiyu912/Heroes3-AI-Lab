"""CPU inference-only audit of the failed frozen strategic pilot. No training."""
import hashlib
import json
from pathlib import Path
import sys
import torch
from torch.distributions import Categorical

ROOT=Path('/mnt/g/Heroes3-AI-Lab/experiments/strategic-policy-v1')
sys.path.insert(0,str(ROOT))
from model import load_checkpoint
from encoder import collate


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    torch.set_num_threads(1)
    frozen=ROOT/'ppo-pilot-01'
    report=json.loads((frozen/'training.json').read_text())
    checkpoint=frozen/'update-0.pt'
    bundle=torch.load(checkpoint,map_location='cpu',weights_only=True)
    model=load_checkpoint(checkpoint,'cpu')
    expected=load_checkpoint(ROOT/'checkpoints/prior-initial-v2.pt','cpu')
    same=all(torch.equal(value,expected.state_dict()[key]) for key,value in model.state_dict().items())
    episodes=[]
    for ep in report['episodes']:
        trace=Path(ep['rollout_dir'])/'rollout.jsonl'
        rows=[json.loads(line) for line in trace.read_text().splitlines()]
        invalid_unlabelled=not ep['valid'] and ep['reward'] is None
        if not ep['valid']:
            episodes.append(dict(valid=False,decisions=len(rows),reward=ep['reward'],invalid_not_counted_as_loss=invalid_unlabelled))
            continue
        native_path=Path(ep['native']['run_dir'])/'strategy-decisions.jsonl'
        native=[json.loads(line) for line in native_path.read_text().splitlines()]
        exact_ack=len(native)==len(rows) and all(
            n['selected_candidate']==r['action'] and n['player']==r['request']['player']
            and n['hero']==r['request']['hero'] and n['day']==r['request']['day']
            and n['from']==r['request']['from'] and n['candidates']==r['request']['candidates']
            for n,r in zip(native,rows))
        max_logp=0.;max_value=0.;max_padding_mass=0.
        with torch.no_grad():
            for i in range(0,len(rows),32):
                batch=rows[i:i+32]
                data=collate([r['request'] for r in batch],'cpu')
                logits,values=model(**data)
                dist=Categorical(logits=logits)
                actions=torch.tensor([r['action'] for r in batch])
                current=dist.log_prob(actions)
                old=torch.tensor([r['old_logprob'] for r in batch])
                old_values=torch.tensor([r['old_value'] for r in batch])
                max_logp=max(max_logp,float((current-old).abs().max()))
                max_value=max(max_value,float((values-old_values).abs().max()))
                if (~data['mask']).any():
                    max_padding_mass=max(max_padding_mass,float(dist.probs[~data['mask']].abs().max()))
        episodes.append(dict(valid=True,reward=ep['reward'],decisions=len(rows),native_rows=len(native),
                             exact_native_intent_ack=exact_ack,
                             max_abs_cpu_vs_saved_cuda_logprob=max_logp,
                             max_abs_cpu_vs_saved_cuda_value=max_value,max_padding_probability=max_padding_mass,
                             rollout_sha256=sha(trace),native_trace_sha256=sha(native_path)))
    result=dict(audit_mode='CPU inference and file comparison only',game_started=False,gpu_started=False,
                optimizer_step_executed=False,
                frozen_trainer_sha256=sha(frozen/'sources/train_ppo_pilot.py'),
                working_trainer_sha256_at_audit=sha(ROOT/'train_ppo_pilot.py'),
                failed_report_sha256=sha(frozen/'training.json'),
                recorded_updates=len(report['updates']),checkpoint_training_updates=bundle['training_updates'],
                checkpoint_optimizer_entries=len(bundle['optimizer']['state']),
                checkpoint_model_identical_to_initial=same,
                checkpoint_load_weights_only_cpu_passed=True,episodes=episodes)
    Path(__file__).with_name('STRATEGIC_PPO_READONLY_EVIDENCE.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result))


if __name__=='__main__':main()
