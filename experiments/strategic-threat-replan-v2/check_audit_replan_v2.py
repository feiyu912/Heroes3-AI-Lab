"""CPU fake-fixture rejection checks. These are NOT native games/certification."""
import argparse
import copy
import hashlib
import json
import tempfile
from pathlib import Path
import audit_replan_v2 as module


def dump(path, value):
    path.write_text(json.dumps(value) + '\n')


def move(x):
    return dict(op='move', kind=5, position=[x, 0, 0], next=[1 if x > 0 else -1, 0, 0],
                path_cost=1, heuristic_score=1)


def proposal(identity, candidates, index=0, turn=1):
    q = dict(schema='strategy-candidates-v4', request_id=identity, player=0, own_turn=turn,
             own_hero_count=1, day=turn, hero=3, gold=0, wood=0, ore=0, own_army_value=100,
             movement=1000, **{'from':[0,0,0]}, visible_threats=[dict(position=[6,0,0], approx_army_value=150)],
             own_towns=[], candidates=copy.deepcopy(candidates))
    raw = (json.dumps(q) + '\n').encode()
    digest = hashlib.sha256(raw).hexdigest()
    r = dict(schema='strategy-typed-action-response-v1', selected_index=index, decision_id=identity,
             player=0, hero=3, own_turn=turn, op=q['candidates'][index]['op'], request_sha256=digest,
             classification='diagnostic_only')
    return dict(request=q, response=r, request_sha256=digest)


def release(identity=2, turn=1):
    return dict(event='bounded_threat_replan', player=0, decision_id=identity, own_turn=turn,
                day=turn, hero=3, **{'from':[0,0,0]}, previous_goal=[3,0,0], previous_kind=5,
                available_moves=2, own_army_value=100,
                threat=dict(position=[6,0,0], approx_army_value=150))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    passed = []
    def reject(name, operation):
        try:
            operation()
        except (ValueError, AssertionError, KeyError, TypeError):
            passed.append(name)
        else:
            raise AssertionError('Invalid fake fixture accepted: ' + name)
    stop = dict(op='end_turn')
    p1 = proposal(1, [move(3), move(-3), stop])
    p2 = proposal(2, [move(3), move(-3), stop], index=1)
    p3 = proposal(3, [move(-3), stop])
    rows = [p1,p2,p3]
    events = [release()]
    details, count = module.verify_commit_transitions(rows, events, 'once', 0)
    assert len(details) == 1 and count == 2 and details[0]['changed_goal']
    # Retained goal invalidated naturally: multiple alternatives are permitted,
    # without consuming the one-interruption allowance.
    module.verify_commit_transitions([p1, proposal(2,[move(4),move(-3),stop])], [], 'off', 0)
    module.verify_commit_transitions([p1, proposal(2,[move(3),move(-3),stop],turn=2)], [], 'off', 0)
    reject('deleted_release_in_both_log_and_sidecar', lambda: module.verify_commit_transitions(rows, [], 'once', 0))
    reject('off_unlogged_multi_candidate', lambda: module.verify_commit_transitions(rows, [], 'off', 0))
    reject('off_logged_release', lambda: module.verify_commit_transitions(rows, events, 'off', 0))
    extra = proposal(3,[move(-3),move(3),stop])
    again = release(3);again['previous_goal'] = [-3,0,0]
    reject('budget_used_unlogged_reopening', lambda: module.verify_commit_transitions([p1,p2,extra],events,'once',0))
    reject('budget_used_logged_second_release', lambda: module.verify_commit_transitions([p1,p2,extra],events+[again],'once',0))
    wrong = release();wrong['previous_goal'] = [99,0,0]
    reject('wrong_previous_goal', lambda: module.verify_commit_transitions(rows,[wrong],'once',0))
    wrong = release();wrong['threat'] = dict(position=[6,0,0],approx_army_value=149)
    reject('unpublished_threat', lambda: module.verify_commit_transitions(rows,[wrong],'once',0))
    weakrows = copy.deepcopy(rows);weakrows[1]['request']['visible_threats'][0]['approx_army_value'] = 149
    reject('below_pressure_threshold', lambda: module.verify_commit_transitions(weakrows,[wrong],'once',0))
    reject('duplicate_release', lambda: module.verify_commit_transitions(rows,events+events,'once',0))
    reject('out_of_order_proposals', lambda: module.verify_commit_transitions([p2,p1],events,'once',0))
    with tempfile.TemporaryDirectory(prefix='fake-replan-cpu-only-') as temporary:
        root = Path(temporary)
        (root/'agent').mkdir()
        for name in module.CORE_RAW_FILES:
            (root/name).write_text('FAKE CPU FIXTURE; NOT A GAME\n')
        dump(root/'PLAN.json',dict(owned_player=0,threat_replan='once',fixture=True))
        proof = dict(whole_game_valid=True,native_game_completed=True,transport_drained=True,
                     contract_errors=[],owned_player=0,
                     raw_sha256={name:module.sha(root/name) for name in module.CORE_RAW_FILES},
                     auditor_sha256={name:module.sha(path) for name,path in module.CORE_AUDITORS.items()})
        module.verify_proof_bindings(root,proof)  # Hash-binding predicate ONLY.
        wrong = copy.deepcopy(proof);wrong['raw_sha256']['client.log'] = '0'*64
        reject('swapped_other_game_proof', lambda: module.verify_proof_bindings(root,wrong))
        wrong = copy.deepcopy(proof);wrong['owned_player'] = 1
        reject('wrong_proof_owner', lambda: module.verify_proof_bindings(root,wrong))
        wrong = copy.deepcopy(proof);del wrong['raw_sha256']['typed.jsonl']
        reject('missing_proof_file_hash', lambda: module.verify_proof_bindings(root,wrong))
        wrong = copy.deepcopy(proof);wrong['auditor_sha256']['raw_events_v4.py'] = '0'*64
        reject('wrong_core_auditor_source', lambda: module.verify_proof_bindings(root,wrong))
        (root/'client.log').write_text('FAKE fixture deleted release AND its mirror\n')
        reject('mutated_raw_with_old_core_proof', lambda: module.verify_proof_bindings(root,proof))
        for p in rows:
            identity = p['request']['request_id']
            dump(root/f'agent/request-{identity:08d}.json',p['request'])
            dump(root/f'agent/action-{identity:08d}.json',p['response'])
        module.verify_proposal_files(root,rows)
        wrong = copy.deepcopy(rows);wrong[0]['request_sha256'] = '0'*64
        reject('proposal_byte_hash_mismatch', lambda: module.verify_proposal_files(root,wrong))
        bad = copy.deepcopy(p1['response']);bad['selected_index'] = 1
        dump(root/'agent/action-00000001.json',bad)
        reject('mutated_action_file', lambda: module.verify_proposal_files(root,rows))
        dump(root/'agent/action-00000001.json',p1['response'])
        path = root/'agent/request-00000001.json';path.write_text(path.read_text()+' ')
        reject('request_semantics_equal_bytes_changed', lambda: module.verify_proposal_files(root,rows))
    args.out.mkdir(parents=True,exist_ok=False)
    report = dict(passed=True,fixture=True,real_execution_certified=False,native_games=0,
                  optimizer_steps=0,training_samples=0,rejection_checks=passed,
                  positive_predicate_checks=5,
                  source_sha256={str(p):module.sha(p) for p in (Path(__file__),Path(module.__file__))},
                  limitation='Artificial CPU predicate fixtures only; no native game or native certification.')
    (args.out/'AUDIT.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    main()
