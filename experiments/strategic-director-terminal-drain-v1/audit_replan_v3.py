"""Director-drain v6 binding plus unchanged exhaustive bounded-commit audit.

No native execution, policy inference, optimizer, or training admission occurs here.
Historical auditor/runner inputs stay unchanged. CPU fixtures call narrow predicates
only; they can never produce this auditor's whole-game certification.
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TYPED = HERE.parent / 'strategic-typed-native-v1'
POLICY = HERE.parent / 'strategic-policy-v3'
CORE_RAW_FILES = {'client.log', 'typed.jsonl', 'strategy-decisions.jsonl',
                  'EXECUTION.json', 'PLAN.json'}
CORE_AUDITORS = {'audit_game_v6.py': HERE / 'audit_game_v6.py',
                 'raw_events_v4.py': TYPED / 'raw_events_v4.py',
                 'director_registry_v1.py': HERE / 'director_registry_v1.py'}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read(path):
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def verify_proof_bindings(root, proof):
    """Verify local hash/owner bindings; alone this is NOT a native certificate."""
    plan = json.loads((root / 'PLAN.json').read_text())
    require(plan.get('terminal_ack_scope')=='director' and proof.get('terminal_ack_scope')=='director',
            'Explicit new Director terminal scope required')
    from director_registry_v1 import verify as verify_registry
    registry=verify_registry((root/'client.log').read_text(errors='replace'),plan['owned_player'])
    require(proof.get('director_registry_proof')==registry,'Current Director registry proof mismatch')
    require(proof.get('whole_game_valid') is True and
            proof.get('native_game_completed') is True and
            proof.get('transport_drained') is True and
            proof.get('contract_errors') == [], 'Core native proof did not pass')
    require(type(plan.get('owned_player')) is int and plan['owned_player'] in (0, 1),
            'Invalid owned player')
    require(type(proof.get('owned_player')) is int and
            proof['owned_player'] == plan['owned_player'], 'Core proof owner mismatch')
    require(set(proof.get('raw_sha256', {})) == CORE_RAW_FILES,
            'Core proof raw hash coverage mismatch')
    for name, expected in proof['raw_sha256'].items():
        require(sha(root / name) == expected, 'Core proof raw SHA mismatch: ' + name)
    require(set(proof.get('auditor_sha256', {})) == set(CORE_AUDITORS),
            'Core proof auditor coverage mismatch')
    for name, path in CORE_AUDITORS.items():
        require(sha(path) == proof['auditor_sha256'][name],
                'Core auditor source SHA mismatch: ' + name)
    return plan


def selected(proposal):
    return proposal['request']['candidates'][proposal['response']['selected_index']]


def goal(candidate):
    return tuple(candidate['position']), candidate['kind']


def verify_proposal_files(root, proposals):
    """Exact request/action/proposal byte bindings; not execution certification."""
    sys.path.insert(0, str(POLICY))
    from broker import validate_response
    inputs, bindings = [], []
    for p in proposals:
        identity = p['request']['request_id']
        request_file = root / f'agent/request-{identity:08d}.json'
        action_file = root / f'agent/action-{identity:08d}.json'
        data = request_file.read_bytes()
        require(json.loads(data) == p['request'], 'Broker proposal/request JSON mismatch')
        require(p['request_sha256'] == hashlib.sha256(data).hexdigest(), 'Proposal/request byte SHA mismatch')
        validate_response(p['response'], p['request'], data)
        require(json.loads(action_file.read_bytes()) == p['response'], 'Broker proposal/action JSON mismatch')
        inputs += [request_file, action_file]
        bindings.append(dict(decision_id=identity, request_sha256=sha(request_file),
                             action_sha256=sha(action_file)))
    return inputs, bindings


def verify_commit_transitions(proposals, releases, mode, owned):
    """Exhaustive availability/commit rule, including unlogged extra releases.

    Narrow CPU predicate: validity here alone does NOT prove native execution.
    """
    require(mode in ('off', 'once'), 'Unknown replan mode')
    release_by_id = {}
    for event in releases:
        identity = event['decision_id']
        require(type(identity) is int and identity > 0 and identity not in release_by_id,
                'Duplicate/invalid release decision')
        release_by_id[identity] = event
    require(mode != 'off' or not releases, 'Off mode emitted a release')
    previous = {}
    budget = set()
    consumed_releases = set()
    details = []
    retained_checks = 0
    last_identity = 0
    for proposal in proposals:
        q, r = proposal['request'], proposal['response']
        identity = q['request_id']
        require(type(identity) is int and identity > last_identity,
                'Proposals are not strictly increasing by native decision ID')
        last_identity = identity
        require(q['player'] == owned and type(q['hero']) is int and
                type(q['own_turn']) is int and q['own_turn'] > 0, 'Proposal owner/turn mismatch')
        key = q['hero'], q['own_turn']
        moves = [c for c in q['candidates'] if c['op'] == 'move']
        retained = [c for c in moves if key in previous and goal(c) == previous[key]]
        event = release_by_id.get(identity)
        if retained:
            retained_checks += 1
            require(len(retained) == 1, 'Duplicate retained goal')
            if event is None:
                require(len(moves) == 1,
                        'Unlogged multi-move reopening of admissible committed goal at decision ' + str(identity))
        if event is not None:
            require(mode == 'once' and key not in budget,
                    'Release in off mode or repeated same-hero/turn budget')
            require(len(retained) == 1 and len(moves) > 1,
                    'Release lacks admissible previous goal or alternatives')
            require(event['event'] == 'bounded_threat_replan' and event['player'] == owned,
                    'Release event/player mismatch')
            require((event['hero'], event['own_turn'], event['day'], event['from']) ==
                    (q['hero'], q['own_turn'], q['day'], q['from']), 'Release context mismatch')
            require((tuple(event['previous_goal']), event['previous_kind']) == previous[key],
                    'Release does not reference latest same-hero/turn chosen goal')
            require(event['available_moves'] == len(moves), 'Release move count mismatch')
            require(event['own_army_value'] == q['own_army_value'] and q['own_army_value'] > 0,
                    'Release own strength mismatch')
            require(event['threat'] in q['visible_threats'], 'Release threat absent from current visible observation')
            h, t = q['from'], event['threat']['position']
            require(h[2] == t[2] and max(abs(h[0]-t[0]), abs(h[1]-t[1])) <= 12,
                    'Release outside same-level Chebyshev12')
            require(event['threat']['approx_army_value'] >= 1.5*q['own_army_value'],
                    'Release below pressure threshold')
            budget.add(key)
            consumed_releases.add(identity)
            choice = selected(proposal)
            details.append(dict(decision_id=identity, day=q['day'], hero=q['hero'], own_turn=q['own_turn'],
                                request_sha256=r['request_sha256'], available_moves=len(moves),
                                unique_next_tiles=len({tuple(c['next']) for c in moves}), selected_op=r['op'],
                                changed_goal=r['op'] == 'move' and goal(choice) != previous[key],
                                changed_next=r['op'] == 'move' and choice['next'] != retained[0]['next']))
        if r['op'] == 'move':
            previous[key] = goal(selected(proposal))
    require(consumed_releases == set(release_by_id), 'Release without a published proposal')
    return details, retained_checks


def audit(root, native_audit, out):
    root, native_audit, out = Path(root).resolve(), Path(native_audit).resolve(), Path(out).resolve()
    require(not out.exists(), 'Output must be a fresh independent directory')
    proof = json.loads(native_audit.read_text())
    plan = verify_proof_bindings(root, proof)
    owned, mode = plan['owned_player'], plan['threat_replan']
    require(mode in ('off', 'once'), 'Unknown mode')
    # Only standard-library modules are imported. No model/Torch loading occurs.
    sys.path.insert(0, str(POLICY))
    sys.path.insert(0, str(TYPED))
    from raw_events_v4 import extract
    from audit_typed_execution import audit as execution_contract
    raw = (root / 'client.log').read_text(errors='replace')
    require(re.findall(r'DirectorThreatReplanMode player=(\d+) mode=(off|once)', raw) == [(str(owned), mode)],
            'Startup mode/owner log mismatch')
    proposals = read(root / 'agent/typed-broker.jsonl')
    require(proposals, 'No policy proposals')
    inputs = [native_audit, Path(__file__), root / 'agent/typed-broker.jsonl']
    inputs += [root / name for name in sorted(CORE_RAW_FILES)]
    inputs += list(CORE_AUDITORS.values()) + [POLICY / name for name in
                                               ('broker.py', 'encoder.py', 'audit_typed_execution.py')]
    proposal_inputs, proposal_bindings = verify_proposal_files(root, proposals)
    inputs += proposal_inputs
    # Rerun the raw exact-request/actual-server-apply/ACK contract, rather than
    # treating a hash-bound green report as sufficient execution evidence.
    events, client_events, _, _ = extract(raw, owned)
    require(client_events == read(root / 'typed.jsonl'), 'Typed event mirror mismatch')
    contract = execution_contract(proposals, events, fixture=False)
    require(contract['valid'] and not contract['errors'], 'Current raw execution contract failed')
    require(contract['counts'] == proof['counts'], 'Core proof execution counts mismatch')
    mirror, release_positions, sent_positions = [], {}, {}
    for number, line in enumerate(raw.splitlines(), 1):
        if 'DirectorThreatReplan {' in line:
            e = json.JSONDecoder().raw_decode(line.split('DirectorThreatReplan ', 1)[1])[0]
            require(e['decision_id'] not in release_positions, 'Duplicate release log')
            mirror.append(e)
            release_positions[e['decision_id']] = number
        if 'DirectorTypedEvent ' in line:
            e = json.JSONDecoder().raw_decode(line.split('DirectorTypedEvent ', 1)[1])[0]
            if e['event'] == 'native_action_sent' and e.get('decision_id') is not None:
                require(e['decision_id'] not in sent_positions, 'Duplicate policy native action')
                sent_positions[e['decision_id']] = number
    sidecar = root / 'strategy-trace.jsonl.replan.jsonl'
    releases = read(sidecar)
    require(releases == mirror, 'Release log/sidecar mirror mismatch')
    if sidecar.exists():
        inputs.append(sidecar)
    for event in releases:
        identity = event['decision_id']
        require(identity in sent_positions and release_positions[identity] < sent_positions[identity],
                'Release not followed by matching real native requestSent')
    details, retained_checks = verify_commit_transitions(proposals, releases, mode, owned)
    hashes = {str(path): sha(path) for path in inputs}
    verify_proof_bindings(root, proof)
    require(all(sha(Path(path)) == expected for path, expected in hashes.items()), 'Audit inputs changed during review')
    report = dict(passed=True, schema='bounded-replan-independent-audit-v3', mode=mode,
                  terminal_ack_scope='director',director_registry_proof=proof['director_registry_proof'],
                  whole_game_execution_reaudited=True, fixture=False, releases=len(releases),
                  proposal_count=len(proposals), retained_commit_checks=retained_checks,
                  multiple_immediate_next_releases=sum(d['unique_next_tiles'] > 1 for d in details),
                  changed_goal=sum(d['changed_goal'] for d in details), changed_next=sum(d['changed_next'] for d in details),
                  details=details, proposal_file_bindings=proposal_bindings, input_sha256=hashes,
                  optimizer_steps=0, training_samples=0,
                  limitation='Availability/commit/native execution audit, not safe retreat, causal win improvement or expert behavior.')
    out.mkdir(parents=True, exist_ok=False)
    (out / 'AUDIT.json').write_text(json.dumps(report, indent=2))
    print(json.dumps({k:v for k,v in report.items() if k not in ('details', 'proposal_file_bindings', 'input_sha256')}, indent=2))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('root', type=Path)
    parser.add_argument('native_audit', type=Path)
    parser.add_argument('out', type=Path)
    args = parser.parse_args()
    audit(args.root, args.native_audit, args.out)
