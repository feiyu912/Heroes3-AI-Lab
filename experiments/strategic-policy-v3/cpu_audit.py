"""Counterexamples and real-parent numerical migration audit; no native engine or GPU."""
import argparse
import builtins
import copy
import hashlib
import json
from pathlib import Path
import sys
import types

import torch

from migrate_weights import load_file, migrate, typed, ROOT, PARENT_SHA256


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parent', type=Path, required=True)
    parser.add_argument('--requests', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    torch.set_num_threads(1)
    torch.manual_seed(2026101804)
    legacy_dir = ROOT.parent / 'strategic-policy-v2'
    legacy_encoder = load_file('_reference_v2_encoder', legacy_dir / 'encoder.py')
    # Model source executes in a private namespace whose encoder import is intercepted.
    # sys.modules['encoder'] is never overwritten or used for either implementation.
    legacy_model = types.ModuleType('_reference_v2_model')
    importer = builtins.__import__
    private_builtins = dict(vars(builtins))
    private_builtins['__import__'] = lambda name, *a, **kw: legacy_encoder if name == 'encoder' else importer(name, *a, **kw)
    legacy_model.__dict__['__builtins__'] = private_builtins
    exec(compile((legacy_dir / 'model.py').read_text(), str(legacy_dir / 'model.py'), 'exec'), legacy_model.__dict__)
    before_encoder_cache = sys.modules.get('encoder')
    old_model, old_bundle, old_sha = legacy_model.load_checkpoint_bundle(args.parent)
    model, bundle = migrate(args.parent)
    requests = [json.loads(path.read_text()) for path in sorted(args.requests.glob('request-*.json'))[:128]]
    if not requests:
        raise ValueError('No real schema3 requests supplied')
    def convert(request):
        result = copy.deepcopy(request)
        result.update(schema=typed.encoder.SCHEMA, own_hero_count=1, own_turn=1)
        result['candidates'] = [dict(candidate, op='move') for candidate in request['candidates']]
        return result
    typed_requests = [convert(request) for request in requests]
    old_batch = legacy_encoder.collate(requests)
    new_batch = typed.encoder.collate(typed_requests)
    assert torch.equal(old_batch['state'], new_batch['state'][:, :26])
    assert torch.equal(old_batch['candidates'], new_batch['candidates'][..., :23])
    with torch.no_grad():
        old_logits, old_value = old_model(**old_batch)
        new_logits, new_value = model(**new_batch)
    mask = old_batch['mask']
    numerical = dict(requests=len(requests), logits_max_abs=float((old_logits[mask]-new_logits[mask]).abs().max()),
                     value_max_abs=float((old_value-new_value).abs().max()),
                     logits_bitwise_equal=torch.equal(old_logits, new_logits), value_bitwise_equal=torch.equal(old_value, new_value))
    assert numerical['logits_max_abs'] < 1e-5 and numerical['value_max_abs'] < 1e-5
    base = typed_requests[0]
    tests = {}
    def reject(name, operation):
        try:
            operation()
        except (ValueError, TypeError, KeyError):
            tests[name] = True
        else:
            raise AssertionError(f'Accepted counterexample {name}')
    def changed(**values):
        return dict(copy.deepcopy(base), **values)
    reject('empty', lambda: typed.encoder.encode(changed(candidates=[])))
    reject('illegal_op', lambda: typed.encoder.encode(changed(candidates=[{'op':'retreat'}])))
    reject('missing_op', lambda: typed.encoder.encode(changed(candidates=requests[0]['candidates'])))
    reject('multihero_stop', lambda: typed.encoder.encode(changed(own_hero_count=2, candidates=[{'op':'end_turn'}])))
    reject('bool_hero_count', lambda: typed.encoder.encode(changed(own_hero_count=True)))
    reject('stop_move_payload', lambda: typed.encoder.encode(changed(candidates=[dict(base['candidates'][0],op='end_turn')])))
    reject('stop_invented_next', lambda: typed.encoder.encode(changed(candidates=[{'op':'end_turn','next':base['from']}])))
    reject('duplicate_stop', lambda: typed.encoder.encode(changed(candidates=[{'op':'end_turn'}]*2)))
    reject('turn_bool', lambda: typed.encoder.encode(changed(own_turn=True)))
    reject('turn_zero', lambda: typed.encoder.encode(changed(own_turn=0)))
    no_turn = copy.deepcopy(base); del no_turn['own_turn']
    reject('turn_missing', lambda: typed.encoder.encode(no_turn))
    reject('all_mask', lambda: model(**dict(new_batch,mask=torch.zeros_like(new_batch['mask']))))
    reject('old_checkpoint_format', lambda: typed.model_from_bundle(old_bundle))
    reject('optimizer_resume', lambda: typed.model_from_bundle(dict(bundle,optimizer={})))
    reject('rollout_resume', lambda: typed.model_from_bundle(dict(bundle,rollout=[])))
    reject('unknown_resume_key', lambda: typed.model_from_bundle(dict(bundle,optimizer_state={})))
    reject('resume_flag', lambda: typed.model_from_bundle(dict(bundle,resume_supported=True)))
    reject('missing_reset_lineage', lambda: typed.model_from_bundle(dict(bundle,lineage={})))
    reject('wrong_parent_sha', lambda: migrate(ROOT / 'encoder.py'))
    stop_only = changed(candidates=[{'op':'end_turn'}])
    stop_batch = typed.encoder.collate([stop_only])
    assert torch.equal(stop_batch['candidates'][..., :23], torch.zeros(1,1,23))
    model(**stop_batch)
    invalid_stop = {key: value.clone() for key,value in stop_batch.items()}
    invalid_stop['candidates'][0,0,13] = 1.
    reject('tensor_stop_move_payload', lambda: model(**invalid_stop))
    invalid_bits = {key: value.clone() for key,value in stop_batch.items()}
    invalid_bits['candidates'][0,0,-2:] = 0.
    reject('tensor_invalid_op_bits', lambda: model(**invalid_bits))
    mixed = changed(candidates=base['candidates'][:2]+[{'op':'end_turn'}])
    mixed_batch = typed.encoder.collate([mixed])
    logits, values = model(**mixed_batch)
    loss = -torch.log_softmax(logits, -1)[0,-1] + values.sum()
    loss.backward()
    gradients = dict(stop_bias=float(model.actor.stop_bias.grad),
        actor_new_state=float(model.actor[0].weight.grad[:,26].abs().sum()),
        actor_new_op_bits=[float(model.actor[0].weight.grad[:,i].abs().sum()) for i in (50,51)],
        critic_new_state=float(model.critic[0].weight.grad[:,26].abs().sum()),
        critic_new_op_bits=[float(model.critic[0].weight.grad[:,i].abs().sum()) for i in (50,51)])
    assert gradients['stop_bias'] != 0 and gradients['actor_new_state'] > 0 and gradients['critic_new_state'] > 0
    assert all(value > 0 for value in gradients['actor_new_op_bits']+gradients['critic_new_op_bits'])
    assert dict(model.named_parameters())['actor.stop_bias'] is model.actor.stop_bias
    # The separate bias adds only to stop; move heuristic is disabled on stop.
    with torch.no_grad():
        initial_logits, initial_values = model(**mixed_batch)
        model.actor.stop_bias.add_(1.)
        changed_logits, _ = model(**mixed_batch)
        assert torch.equal(initial_logits[:,:-1], changed_logits[:,:-1])
        assert torch.allclose(changed_logits[:,-1]-initial_logits[:,-1],torch.ones(1))
        model.actor.stop_bias.sub_(1.)
    target = args.out / 'typed-initial-v4.pt'
    typed.atomic_torch_save(bundle, target)
    loaded, loaded_bundle, checkpoint_sha = typed.load_checkpoint_bundle(target)
    assert all(torch.equal(value,loaded.state_dict()[key]) for key,value in model.state_dict().items())
    with torch.no_grad():
        loaded_logits, loaded_values = loaded(**mixed_batch)
        assert torch.equal(initial_logits,loaded_logits) and torch.equal(initial_values,loaded_values)
    assert sys.modules.get('encoder') is before_encoder_cache
    report = dict(passed=True,cpu_only=True,native_started=False,optimizer_steps=0,
        parent_sha256=old_sha,expected_parent_sha256=PARENT_SHA256,checkpoint_sha256=checkpoint_sha,
        schema=typed.encoder.SCHEMA,encoder_version=typed.ENCODER_VERSION,model_format=typed.PRIOR_FORMAT,
        state_dim=27,candidate_dim=25,move_only_mathematically_equivalent=True,numerical=numerical,
        mixed_or_stop_equivalence_claimed=False,stop_bias_initial=-4.,stop_prior_is_learned=False,
        counterexamples_rejected=tests,gradients=gradients,save_load_bitwise=True,module_cache_unchanged=True,
        source_sha256={str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in
            [ROOT/'encoder.py',ROOT/'model.py',ROOT/'migrate_weights.py',ROOT/'cpu_audit.py',
             legacy_dir/'encoder.py',legacy_dir/'model.py']})
    (args.out/'AUDIT.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
