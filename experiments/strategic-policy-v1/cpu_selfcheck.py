"""Synthetic CPU checks only. No VCMI, CUDA learner, or installed dependencies."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import torch
from encoder import validate, collate
from model import PriorCandidateActorCritic
from broker import atomic


def example(request_id=1):
    return {'schema': 'strategy-candidates-v2', 'request_id': request_id,
        'player': 0, 'day': 1, 'hero': 0, 'from': [6, 10, 0],
        'gold': 7500, 'wood': 18, 'ore': 18, 'own_army_value': 3000, 'movement': 1560,
        'candidates': [
            dict(kind=3, position=[9, 11, 0], next=[7, 10, 0], path_cost=450, heuristic_score=1),
            dict(kind=2, position=[6, 15, 0], next=[6, 11, 0], path_cost=750, heuristic_score=9)]}


def main():
    torch.set_num_threads(1)
    torch.manual_seed(7)
    first, second = example(), example(2)
    second['candidates'] = second['candidates'][:1]
    batch = collate([first, second], 'cpu')
    model = PriorCandidateActorCritic().cpu()
    logits, value = model(**batch)
    assert logits.shape == (2, 2) and value.shape == (2,)
    assert torch.isneginf(logits[1, 1]) and torch.isfinite(value).all()
    assert all(batch['mask'][i, int(logits.argmax(1)[i])] for i in range(2))
    assert logits.argmax(1).tolist() == [1, 0]
    assert model.actor[0].weight.std() > 0
    assert torch.count_nonzero(model.actor[-1].weight) == 0
    negative_scores = example(4)
    for candidate, score in zip(negative_scores['candidates'], [-80.0, -10.0]):
        candidate['heuristic_score'] = score
    with torch.no_grad():
        negative_logits, _ = model(**collate([negative_scores]))
    assert int(negative_logits.argmax(1)[0]) == 1
    poisoned = {key: tensor.clone() for key, tensor in batch.items()}
    poisoned['candidates'][~poisoned['mask']] = float('nan')
    p_logits, p_value = model(**poisoned)
    assert torch.equal(logits, p_logits) and torch.equal(value, p_value)
    permuted = copy.deepcopy(first)
    permuted['candidates'].reverse()
    original_logits, original_value = model(**collate([first]))
    other_logits, other_value = model(**collate([permuted]))
    assert torch.allclose(original_logits.flip(1), other_logits, atol=1e-6)
    assert torch.allclose(original_value, other_value, atol=1e-6)
    loss = -torch.distributions.Categorical(logits=logits).log_prob(torch.tensor([1, 0])).mean()
    loss += (value - torch.tensor([1., -1.])).square().mean()
    loss.backward()
    assert all(parameter.grad is not None and torch.isfinite(parameter.grad).all()
               for parameter in model.parameters())
    assert any(parameter.grad.abs().sum() > 0 for parameter in model.actor.parameters())
    assert any(parameter.grad.abs().sum() > 0 for parameter in model.critic.parameters())
    invalid = example(3)
    invalid['candidates'][0]['kind'] = 99
    try:
        validate(invalid)
        raise AssertionError('Invalid kind admitted')
    except ValueError:
        pass
    root = Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory(prefix='strategy-broker-cpu-') as temporary:
        directory = Path(temporary)
        process = subprocess.Popen([sys.executable, str(root / 'broker.py'), '--agent-dir', str(directory),
            '--max-requests', '3', '--idle-seconds', '10'], stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True)
        try:
            deadline = time.monotonic() + 8
            while not (directory / 'broker-ready.json').exists():
                assert process.poll() is None, 'Broker exited early'
                if time.monotonic() > deadline:
                    raise TimeoutError('Synthetic broker readiness timeout')
                time.sleep(.01)
            for request in [first, second, invalid]:
                atomic(directory / f'request-{request["request_id"]:08d}.json', json.dumps(request).encode())
            stdout, _ = process.communicate(timeout=8)
            assert process.returncode == 0, stdout
            assert (directory / 'action-00000001.json').read_text().strip() == '1'
            assert (directory / 'action-00000002.json').read_text().strip() == '0'
            assert not (directory / 'action-00000003.json').exists()
            events = [json.loads(line) for line in (directory / 'broker-trace.jsonl').read_text().splitlines()]
            assert sum(event['event'] == 'response_written' for event in events) == 2
            assert sum(event['event'] == 'protocol_error' for event in events) == 1
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
    report = {'status': 'PASSED', 'device': 'cpu', 'torch_version': torch.__version__,
              'parameter_count': sum(parameter.numel() for parameter in model.parameters()),
              'checks': ['variable_candidate_padding_mask', 'argmax_legal', 'nan_padding_ignored',
                  'candidate_permutation_equivariance', 'actor_critic_gradients_finite_nonzero',
                  'atomic_file_protocol_heuristic_argmax', 'invalid_request_no_action', 'io_id_audit',
                  'positive_heuristic_prior_argmax', 'negative_score_prior_order',
                  'random_hidden_zero_residual_output_layer'],
              'game_executed': False, 'cuda_training_started': False,
              'synthetic_backward_only': True, 'training_gain_claimed': False}
    (root / 'CPU_SELFCHECK_v2.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
