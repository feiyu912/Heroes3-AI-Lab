"""Read-only native strategic trace audit. Request success alone is never proof."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

KINDS = {'before_build': 'build', 'before_recruit': 'recruit',
         'before_army_transfer': 'army_transfer'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def army(objects):
    result = Counter()
    for obj in objects:
        for creature, amount in obj.get('army', []):
            result[str(creature)] += amount
    return result


def delta(before, after):
    return {key: after.get(key, 0) - before.get(key, 0)
            for key in set(before) | set(after)
            if after.get(key, 0) != before.get(key, 0)}


def inspect_pair(before, after):
    kind = KINDS[before['event']]
    resources = {key: after[key] - before[key] for key in ('gold', 'wood', 'ore')}
    old_towns = {str(t['id']): t for t in before['towns']}
    new_towns = {str(t['id']): t for t in after['towns']}
    same_towns = old_towns.keys() == new_towns.keys()
    added = {key: sorted(set(new_towns[key]['buildings']) - set(old_towns[key]['buildings']))
             for key in old_towns.keys() & new_towns.keys()}
    added = {key: value for key, value in added.items() if value}
    removed = {key: sorted(set(old_towns[key]['buildings']) - set(new_towns[key]['buildings']))
               for key in old_towns.keys() & new_towns.keys()}
    removed = {key: value for key, value in removed.items() if value}
    offer_deltas = {}
    for key in old_towns.keys() & new_towns.keys():
        old, new = old_towns[key].get('available', []), new_towns[key].get('available', [])
        if len(old) == len(new):
            diff = [b - a for a, b in zip(old, new)]
            if any(diff):
                offer_deltas[key] = diff
    town_delta = delta(army(before['towns']), army(after['towns']))
    hero_delta = delta(army(before['heroes']), army(after['heroes']))
    total_delta = delta(army(before['towns'] + before['heroes']),
                        army(after['towns'] + after['heroes']))
    facts = {'kind': kind, 'resource_delta_observed': resources,
             'buildings_added_by_town': added, 'buildings_removed_by_town': removed,
             'recruit_offer_delta_by_town_level': offer_deltas,
             'town_army_delta_by_creature': town_delta, 'hero_army_delta_by_creature': hero_delta,
             'combined_army_delta_by_creature': total_delta}
    paid = any(value < 0 for value in resources.values()) and all(value <= 0 for value in resources.values())
    if kind == 'build':
        passed = same_towns and bool(added) and not removed and paid and not total_delta
    elif kind == 'recruit':
        depleted = sum(-min(value, 0) for diffs in offer_deltas.values() for value in diffs)
        gains = sum(total_delta.values())
        passed = (same_towns and paid and not added and not removed and depleted > 0
                  and total_delta and all(value > 0 for value in total_delta.values())
                  and gains == depleted
                  and all(value <= 0 for diffs in offer_deltas.values() for value in diffs))
    else:
        transferred = any(value > 0 and town_delta.get(creature) == -value
                          for creature, value in hero_delta.items())
        passed = (same_towns and transferred and not total_delta and not added and not removed
                  and not offer_deltas and all(value == 0 for value in resources.values()))
    facts['verified_state_transition'] = bool(passed)
    return facts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--compare-run', type=Path, help='Compare a real restored run to this original run')
    args = parser.parse_args()
    trace = args.run_dir / 'strategy-trace.jsonl'
    records = [json.loads(line) for line in trace.read_text().splitlines() if line.strip()]
    proofs, rejected, missing = [], [], []
    for index, before in enumerate(records):
        if before.get('event') not in KINDS:
            continue
        after = records[index + 1] if index + 1 < len(records) else None
        if (not after or after.get('event') not in ('economy_applied', 'economy_failed')
                or any(before.get(key) != after.get(key) for key in ('player', 'own_turn'))):
            missing.append({'before_line': index + 1, 'kind': KINDS[before['event']],
                            'reason': 'No immediately following same-player/same-turn economy acknowledgment'})
            continue
        facts = inspect_pair(before, after)
        facts.update(before_line=index + 1, after_line=index + 2,
                     player=before['player'], own_turn=before['own_turn'])
        facts['native_request_reported_applied'] = after['event'] == 'economy_applied'
        if facts['verified_state_transition'] and facts['native_request_reported_applied']:
            proofs.append(facts)
        else:
            rejected.append(facts)
    result_path = args.run_dir / 'result.json'
    result = json.loads(result_path.read_text()) if result_path.exists() else {}
    declared_sha = result.get('strategy_trace_sha256')
    digest = sha(trace)
    report = {'schema': 'strategic-economy-state-audit-v1', 'run_dir': str(args.run_dir),
              'trace_sha256': digest, 'trace_records': len(records),
              'trace_matches_runner_sha': declared_sha == digest if declared_sha else None,
              'runner_completed': result.get('completed'),
              'verified_counts': dict(Counter(item['kind'] for item in proofs)),
              'verified_pairs': proofs, 'rejected_pairs': rejected, 'unpaired_before_events': missing,
              'limitations': [
                  'Trace does not contain request IDs; only adjacent same-player/same-turn acknowledgment pairs accepted.',
                  'Resource audit covers logged gold/wood/ore; exact native price tables and other resources are not logged.',
                  'Army counts are compared by creature type, not treated as equal strategic value.',
                  'Same-state/no-op requests are rejected even when native callback reports success.',
                  'Complete economy mechanics do not demonstrate a strong learned strategic policy.']}
    report['all_three_mechanics_observed'] = all(
        report['verified_counts'].get(kind, 0) > 0 for kind in ('build', 'recruit', 'army_transfer'))
    if args.compare_run:
        restored = args.compare_run
        restored_trace = restored / 'strategy-trace.jsonl'
        restored_records = [json.loads(line) for line in restored_trace.read_text().splitlines() if line.strip()]
        restored_result = json.loads((restored / 'result.json').read_text())
        original_log, restored_log = ((path / 'client.log').read_text(errors='replace')
                                      for path in (args.run_dir, restored))
        markers = ['Preparing to start loaded game', 'Game has been successfully loaded!',
                   'Game loaded, initialize interfaces.']
        marker_checks = {marker: marker in restored_log for marker in markers}
        source_save = Path(restored_result['config']['save_file'])
        copied_save = restored / 'data/vcmi/Saves/takeover-resume-snapshot.vsgm1'
        source_hash, copied_hash = sha(source_save), sha(copied_save)
        original_plan, restored_plan = (json.loads((path / 'plan.json').read_text())
                                       for path in (args.run_dir, restored))
        binaries = {}
        for name in ('vcmiclient', 'vcmiserver', 'libvcmi.so'):
            old = {value for key, value in original_plan['hashes'].items() if Path(key).name == name}
            new = {value for key, value in restored_plan['hashes'].items() if Path(key).name == name}
            binaries[name] = len(old) == 1 and old == new
        moves = lambda text: re.findall(r'DirectorAI: step finished[^\n\r]*', text)
        same_trace = trace.read_bytes() == restored_trace.read_bytes()
        pair = {'restored_run_dir': str(restored), 'restored_completed': restored_result.get('completed'),
                'restored_log_sha_matches_runner': sha(restored / 'client.log') == restored_result.get('log_sha256'),
                'original_log_sha_matches_runner': sha(args.run_dir / 'client.log') == result.get('log_sha256'),
                'load_markers_read_directly_from_native_log': marker_checks,
                'source_save_path': str(source_save), 'source_save_sha256': source_hash,
                'source_save_bytes': source_save.stat().st_size,
                'copied_save_sha256': copied_hash, 'source_and_copy_equal': source_hash == copied_hash,
                'source_file_listed_in_original_result': any(
                    item['sha256'] == source_hash and Path(item['path']) == source_save
                    for item in result.get('save_files', [])),
                'recorded_binaries_equal': binaries,
                'initial_observed_state_equal': bool(records and restored_records and records[0] == restored_records[0]),
                'recorded_strategy_trace_bytes_equal': same_trace,
                'restored_trace_sha256': sha(restored_trace),
                'restored_trace_records': len(restored_records),
                'restored_trace_sha_matches_runner': sha(restored_trace) == restored_result.get('strategy_trace_sha256'),
                'move_reply_sequences_equal': moves(original_log) == moves(restored_log),
                'original_move_replies': len(moves(original_log)),
                'restored_move_replies': len(moves(restored_log)),
                'terminal_results_equal': all(result.get(key) == restored_result.get(key)
                    for key in ('winner', 'turns', 'engine_exit', 'failed_move_replies')),
                'restore_scope': 'Only observed start-of-turn checkpoint; AI private state is not serialized; not arbitrary mid-action restore',
                'trace_scope': 'Recorded player-visible strategy states and DirectorAI move replies; not all native engine events or hidden state'}
        pair['checkpoint_restore_verified'] = bool(
            result.get('completed') and restored_result.get('completed') and all(marker_checks.values())
            and pair['source_and_copy_equal'] and pair['source_file_listed_in_original_result']
            and all(binaries.values()) and pair['initial_observed_state_equal']
            and pair['recorded_strategy_trace_bytes_equal'] and pair['move_reply_sequences_equal']
            and pair['terminal_results_equal'] and pair['restored_trace_sha_matches_runner']
            and pair['restored_log_sha_matches_runner'] and pair['original_log_sha_matches_runner'])
        report['restore_pair_audit'] = pair
    output = args.output or args.run_dir / 'economy-audit.json'
    if output.exists():
        raise FileExistsError(f'Refusing to overwrite prior audit: {output}')
    output.write_text(json.dumps(report, indent=2))
    print(json.dumps({key: value for key, value in report.items()
                     if key not in ('verified_pairs', 'rejected_pairs', 'unpaired_before_events')}, indent=2))
    print('OUTPUT=' + str(output))


if __name__ == '__main__':
    main()
