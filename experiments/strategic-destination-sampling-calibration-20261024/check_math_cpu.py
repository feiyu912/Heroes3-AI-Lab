"""CPU-only numerical and gradient checks; never loads policy/native/CUDA."""
import argparse
import hashlib
import json
from pathlib import Path
import torch
from movement_exploration import transform_move_logits, effective_distribution, TOLERANCES


def main():
    p = argparse.ArgumentParser(); p.add_argument('--out', type=Path, required=True); a = p.parse_args()
    torch.set_num_threads(1)
    generator = torch.Generator(device='cpu').manual_seed(2026102401)
    checked = 0; max_mass_error = 0.; rejected = 0
    for dtype in TOLERANCES:
        for n in (1, 2, 5, 51, 100):
            for count in sorted({0, 1, n // 2, n}):
                for scale in (.01, 1., 20.):
                    raw = torch.randn(n, generator=generator, dtype=dtype) * scale
                    raw.requires_grad_(); mask = torch.arange(n) < count
                    candidates = [{'op': 'move' if i < count else ('build', 'recruit', 'end')[i % 3]}
                                  for i in range(n)]
                    effective, _, lp, before, after = effective_distribution(raw, candidates)
                    assert torch.equal(effective[~mask], raw[~mask])
                    if count <= 1: assert effective is raw
                    if count > 1:
                        rtol, atol = TOLERANCES[dtype]
                        expected = (raw[mask] / .25).softmax(0)
                        assert torch.allclose(lp.exp()[mask] / lp.exp()[mask].sum(), expected,
                                              rtol=rtol * 10, atol=atol * 10)
                    for op in before: max_mass_error = max(max_mass_error, abs(float((before[op] - after[op]).detach())))
                    assert torch.isfinite(effective).all() and torch.isfinite(lp).all()
                    loss = lp.square().mean(); loss.backward()
                    assert raw.grad is not None and torch.isfinite(raw.grad).all()
                    assert transform_move_logits(raw, mask, 1.) is raw
                    checked += 1
    valid = torch.tensor([.2, -.7, .8]); mask = torch.tensor([True, True, False])
    invalid = []
    for t in (True, False, 0, -1, float('nan'), float('inf'), '0.25', None):
        invalid.append(lambda t=t: transform_move_logits(valid, mask, t))
    invalid.extend([
        lambda: transform_move_logits(valid.long(), mask),
        lambda: transform_move_logits(valid.reshape(1, -1), mask),
        lambda: transform_move_logits(torch.tensor([]), torch.tensor([], dtype=torch.bool)),
        lambda: transform_move_logits(torch.tensor([float('nan')]), torch.tensor([False])),
        lambda: transform_move_logits(valid, mask.long()),
        lambda: transform_move_logits(valid, mask[:2]),
        lambda: transform_move_logits(torch.tensor([3e38, 2e38]), torch.tensor([True, True])),
    ])
    for case in invalid:
        try: case()
        except ValueError: rejected += 1
        else: raise AssertionError('Invalid input accepted')
    # Finite-difference comparison tests the coupled normalizer, not just that a gradient exists.
    x = torch.tensor([.2, -.1, .7, .3], dtype=torch.float64, requires_grad=True)
    m = torch.tensor([True, True, True, False])
    assert torch.autograd.gradcheck(lambda v: transform_move_logits(v, m), (x,), eps=1e-6,
                                    atol=1e-5, rtol=1e-4)
    report = dict(passed=True, device='cpu', native_runs=0, GPU_operations=0, optimizer_steps=0,
                  distributions_checked=checked, invalid_cases_rejected=rejected,
                  max_absolute_operation_mass_error=max_mass_error, autograd_gradcheck=True,
                  tolerances={str(k): list(v) for k, v in TOLERANCES.items()},
                  zero_one_move_identity=True, non_move_logits_bitwise=True,
                  source_sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                                 for p in (Path(__file__), Path(__file__).with_name('movement_exploration.py'))})
    a.out.write_text(json.dumps(report, indent=2) + '\n'); print(json.dumps(report))


if __name__ == '__main__': main()
