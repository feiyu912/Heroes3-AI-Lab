"""Read-only comparison of the observed heap abort and its non-reproducing repeats."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

ROOT = Path('/root/heroes3-ai-lab/workers/adv-runs')
NAMES = ['development-01-15-2026101812-7whqgl65',
         'crash-audit-v5-2026101812-e9jfiqs2', 'crash-repeat-v5-2026101812-220p4ie_']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    reports = []
    traces = []
    for name in NAMES:
        run = ROOT / name
        log_path = run / 'client.log'
        text = re.sub(r'\x1b\[[0-9;]*m', '', log_path.read_text(errors='replace'))
        result = json.loads((run / 'result.json').read_text())
        plan = json.loads((run / 'plan.json').read_text())
        trace = run / 'strategy-trace.jsonl'
        trace_lines = trace.read_bytes().splitlines()
        traces.append(trace_lines)
        entries = re.findall(r'Player (\d+) \((\w+)\) starting turn, day (\d+)', text)
        counts = Counter(tuple(entry) for entry in entries)
        queries = re.findall(r'Entering virtual void NK2AI::AIGateway::yourTurn\(QueryID\): queryID [\x27\x22](-?\d+)', text)
        report = {'run': str(run), 'log_sha256': sha(log_path),
                  'log_hash_matches_runner': sha(log_path) == result.get('log_sha256'),
                  'strategy_trace_sha256': sha(trace), 'strategy_records': len(trace_lines),
                  'engine_exit': result.get('engine_exit'), 'completed': result.get('completed'),
                  'turn_entries': len(entries), 'last_turn_entries': entries[-4:],
                  'duplicated_same_player_day_starts': [{'entry': entry, 'count': count}
                    for entry, count in counts.items() if count > 1],
                  'your_turn_query_entries_parsed': len(queries),
                  'duplicated_query_ids': {query: count for query, count in Counter(queries).items() if count > 1},
                  'heap_messages': [line for line in text.splitlines()
                    if 'double free' in line or 'unaligned fastbin' in line],
                  'last_log_lines': text.splitlines()[-14:],
                  'binary_hashes': {Path(key).name: value for key, value in plan.get('hashes', {}).items()
                    if Path(key).name in ('vcmiclient', 'vcmiserver', 'libvcmi.so')}}
        reports.append(report)
    common = 0
    for before, after in zip(traces[0], traces[1]):
        if before != after:
            break
        common += 1
    output = {'status': 'HEAP_ABORT_OBSERVED_CAUSE_UNPROVEN_REPEATS_DID_NOT_REPRODUCE',
              'runs': reports,
              'repeat_strategy_traces_equal': traces[1] == traces[2],
              'crash_trace_prefix_equal_to_first_repeat_records': common,
              'all_recorded_binary_hashes_equal': all(
                  item['binary_hashes'] == reports[0]['binary_hashes'] for item in reports[1:]),
              'no_game_started': True, 'source_or_build_modified': False,
              'caveat': 'Log sequences have no thread ID or analyzer address; consecutive update messages do not prove concurrent access'}
    path = Path(__file__).parent / 'HEAP_FAILURE_LOG_AUDIT.json'
    if path.exists():
        raise FileExistsError(path)
    path.write_text(json.dumps(output, indent=2))
    print(json.dumps({key: value for key, value in output.items() if key != 'runs'}, indent=2))
    for report in reports:
        print(json.dumps({key: value for key, value in report.items()
                          if key not in ('last_log_lines', 'binary_hashes')}, indent=2))


if __name__ == '__main__':
    main()
