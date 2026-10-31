"""Create an untrained prior/residual CPU checkpoint; no optimizer or game runs."""
import argparse
import hashlib
import json
from pathlib import Path
import torch
from encoder import ENCODER_VERSION, collate
from model import PriorCandidateActorCritic, PRIOR_FORMAT, load_checkpoint


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=Path(__file__).parent / 'checkpoints/prior-initial-v2.pt')
    parser.add_argument('--reference-agent-dir', type=Path)
    parser.add_argument('--seed', type=int, default=20261018)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('Refusing to overwrite an existing checkpoint')
    torch.set_num_threads(1)
    torch.manual_seed(args.seed)
    model = PriorCandidateActorCritic().cpu().eval()
    config = {'prior_scale': 64.0, 'prior_feature_index': 13}
    reference = []
    if args.reference_agent_dir:
        for path in sorted(args.reference_agent_dir.glob('request-????????.json')):
            request = json.loads(path.read_text())
            with torch.no_grad():
                logits, _ = model(**collate([request]))
                selected = int(logits.argmax(1)[0])
            expected = max(range(len(request['candidates'])),
                           key=lambda i: request['candidates'][i]['heuristic_score'])
            reference.append({'request': str(path), 'sha256': sha(path),
                              'model_action': selected, 'heuristic_action': expected,
                              'equal': selected == expected})
        if not reference or not all(row['equal'] for row in reference):
            raise AssertionError('Initial prior does not match all supplied reference actions')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    bundle = {'format': PRIOR_FORMAT, 'encoder_version': ENCODER_VERSION,
              'hidden': model.hidden, 'prior_config': config, 'state_dict': model.state_dict(),
              'trained': False, 'initialization_seed': args.seed,
              'training_updates': 0, 'value_is_win_probability': False}
    torch.save(bundle, args.output)
    restored = load_checkpoint(args.output)
    assert torch.equal(model.actor[-1].weight, restored.actor[-1].weight)
    report = {'format': PRIOR_FORMAT, 'checkpoint': str(args.output), 'checkpoint_sha256': sha(args.output),
              'encoder_version': ENCODER_VERSION, 'prior_config': config, 'device': 'cpu',
              'parameters': sum(parameter.numel() for parameter in model.parameters()),
              'actor_hidden_weights_random': bool(model.actor[0].weight.std() > 0),
              'actor_final_layer_zero': bool(torch.count_nonzero(model.actor[-1].weight) == 0
                                            and torch.count_nonzero(model.actor[-1].bias) == 0),
              'reference_requests': len(reference), 'reference_matches': sum(row['equal'] for row in reference),
              'reference_evidence': reference, 'trained': False, 'training_updates': 0,
              'value_is_win_probability': False, 'game_executed': False, 'cuda_training_started': False,
              'limitations': 'Positive monotone prior preserves ordering in the tested numeric range; extreme/near-equal floating scores may collapse after tanh/float32.'}
    args.output.with_suffix('.manifest.json').write_text(json.dumps(report, indent=2))
    print(json.dumps({key: value for key, value in report.items() if key != 'reference_evidence'}, indent=2))


if __name__ == '__main__':
    main()
