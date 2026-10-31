"""Manual within-move exploration; no training, model changes or candidate merging."""
import math
import torch

TEMPERATURE = 0.25
EPOCH = 'strategic-within-move-temperature-TRAIN-calibration-v1'
TOLERANCES = {torch.float32: (3e-6, 3e-7), torch.float64: (3e-13, 3e-14)}


def transform_move_logits(logits, move_mask, temperature=TEMPERATURE):
    """Keep logsumexp(move) fixed while changing its conditional distribution.

    Input is one request's finite legal logits, without padded candidates.
    Zero/one move (and T=1) returns the exact input object. Non-move tensor
    entries are copied bitwise. Mass conservation is mathematical; floating
    arithmetic is checked against the explicit dtype tolerances below.
    """
    if isinstance(temperature, bool) or not isinstance(temperature, (int, float)):
        raise ValueError('temperature must be a finite positive real scalar')
    if not math.isfinite(temperature) or temperature <= 0:
        raise ValueError('temperature must be finite and positive')
    if not isinstance(logits, torch.Tensor) or logits.dtype not in TOLERANCES:
        raise ValueError('finite float32/float64 logits required')
    if logits.ndim != 1 or logits.numel() == 0 or not bool(torch.isfinite(logits).all()):
        raise ValueError('one nonempty finite legal-logit vector required')
    if (not isinstance(move_mask, torch.Tensor) or move_mask.dtype != torch.bool
            or move_mask.shape != logits.shape or move_mask.device != logits.device):
        raise ValueError('same-shape same-device boolean move mask required')
    if int(move_mask.sum()) <= 1 or temperature == 1:
        return logits
    moves = logits[move_mask]
    scaled = moves / temperature
    if not bool(torch.isfinite(scaled).all()):
        raise ValueError('temperature scaling overflow')
    adjusted = scaled + (torch.logsumexp(moves, 0) - torch.logsumexp(scaled, 0))
    if not bool(torch.isfinite(adjusted).all()):
        raise ValueError('nonfinite transformed logits')
    result = logits.clone()
    result[move_mask] = adjusted
    return result


def operation_mass(probabilities, candidates):
    """Every original candidate remains distinct, including destination/kind."""
    if probabilities.ndim != 1 or len(candidates) != probabilities.numel():
        raise ValueError('one probability for each original candidate required')
    operations = sorted({c['op'] for c in candidates})
    return {op: probabilities[[i for i, c in enumerate(candidates) if c['op'] == op]].sum()
            for op in operations}


def effective_distribution(logits, candidates, temperature=TEMPERATURE):
    mask = torch.tensor([c['op'] == 'move' for c in candidates], device=logits.device, dtype=torch.bool)
    effective = transform_move_logits(logits, mask, temperature)
    raw_logp = logits.log_softmax(-1)
    effective_logp = effective.log_softmax(-1)
    if not bool(torch.isfinite(raw_logp).all() and torch.isfinite(effective_logp).all()):
        raise ValueError('nonfinite legal log probabilities')
    raw_mass = operation_mass(raw_logp.exp(), candidates)
    effective_mass = operation_mass(effective_logp.exp(), candidates)
    rtol, atol = TOLERANCES[logits.dtype]
    if not torch.equal(logits[~mask], effective[~mask]):
        raise AssertionError('Non-move logits changed')
    for op in raw_mass:
        if not torch.allclose(raw_mass[op], effective_mass[op], rtol=rtol, atol=atol):
            raise AssertionError('Operation probability mass changed: ' + op)
    return effective, raw_logp, effective_logp, raw_mass, effective_mass
