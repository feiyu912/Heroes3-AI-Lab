"""Read-only integrity audit of completed pilot artifacts; no simulator or GPU."""
import gzip
import hashlib
import json
from pathlib import Path
import time


HERE = Path(__file__).resolve().parent
PILOT = HERE.parent / 'human-tactics-v1'
CACHE = {}
ERRORS = []
WARNINGS = []


def digest(path):
    path = Path(path)
    stat = path.stat()
    key = (str(path), stat.st_size, stat.st_mtime_ns)
    if key not in CACHE:
        value = hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda: stream.read(1024*1024), b''):
                value.update(block)
        CACHE[key] = value.hexdigest()
    return CACHE[key]


def check(condition, message):
    if not condition:
        ERRORS.append(message)


def condition(row):
    return (row.get('scenario'), row.get('role'), row.get('seed'), row.get('policy'))


def read(path):
    return json.loads(Path(path).read_text())


def audit_episode(row, cases, context):
    prefix = context + '/' + row.get('battle_id', 'unknown')
    check(row.get('completed') is True, prefix + ': not completed')
    case = cases.get(row.get('scenario'))
    check(case is not None, prefix + ': unknown scenario')
    if case is None:
        return
    check(row.get('split') == case['split'], prefix + ': split differs from scenario registry')
    check(row.get('tactic_id') == case['tactic_id'], prefix + ': tactic differs from scenario registry')
    check(row.get('role') in ['attacker', 'defender'], prefix + ': invalid role')
    frozen = row.get('frozen_artifacts', {})
    checkpoint = row.get('checkpoint')
    check(checkpoint in frozen, prefix + ': checkpoint not frozen')
    map_path = '/root/heroes3-ai-lab/data/vcmi/Maps/' + case['map']
    check(frozen.get(map_path) == case['sha256'], prefix + ': map SHA differs from registry')
    for filename, expected in frozen.items():
        try:
            check(digest(filename) == expected, prefix + ': frozen artifact changed: ' + filename)
        except OSError as error:
            ERRORS.append(prefix + ': frozen artifact unavailable: ' + filename + ': ' + str(error))
    for script in ['experts.py', 'run_episode.py', 'generate_scenarios.py', 'test_experts.py']:
        check(str(PILOT/script) in frozen, prefix + ': required script not frozen: ' + script)
    report_path = PILOT/'runs'/(row['battle_id']+'.json')
    check(report_path.exists(), prefix + ': canonical report missing')
    if report_path.exists():
        check(read(report_path) == row, prefix + ': aggregate differs from canonical report')
    try:
        archive = row['demonstrations']
        check(digest(archive) == row['demonstration_sha256'], prefix + ': gzip SHA mismatch')
        with gzip.open(archive, 'rt') as stream:
            data = json.load(stream)
        inner = data['episode']
        for key, value in inner.items():
            check(row.get(key) == value, prefix + ': gzip episode differs at ' + key)
        records = data['decisions']
        check(len(records) == row['steps'], prefix + ': decision count mismatch')
        for index, record in enumerate(records):
            where = prefix + '/step-' + str(index)
            legal = record['legal_actions']
            check(legal == record['observation']['active_action_ids'], where + ': legal list differs from observation')
            check(len(legal) == len(set(legal)) and bool(legal), where + ': duplicate or empty legal IDs')
            check(record['executed_action'] in legal, where + ': illegal executed action')
            for key in ['tactic_id', 'battle_id', 'scenario_seed', 'policy']:
                outer_key = 'seed' if key == 'scenario_seed' else key
                check(record.get(key) == row.get(outer_key), where + ': record differs at ' + key)
            check(record['actor_side'] == int(row['role'] == 'defender'), where + ': actor role mismatch')
            if row['policy'] != 'model':
                check(record['expert_action'] == record['executed_action'] and record['expert_action'] in legal,
                      where + ': expert label differs from legal execution')
            else:
                check(record['expert_action'] is None, where + ': model action labeled as expert')
    except (OSError, KeyError, ValueError, TypeError) as error:
        ERRORS.append(prefix + ': demonstration unreadable: ' + repr(error))
    outcome = row.get('terminal_outcome')
    expected_win = bool(row.get('terminated') and not row.get('truncated') and outcome
                        and outcome.get('result_type') == 0
                        and outcome.get('winner') == int(row['role'] == 'defender'))
    check(row.get('success') == expected_win, prefix + ': win differs from raw flags')
    check(row.get('invalid_actions') == 0, prefix + ': invalid actions reported')
    if row.get('terminated') and outcome and outcome.get('result_type') == 0 and outcome.get('winner') in [0, 1]:
        winner = str(outcome['winner'])
        loser = str(1-outcome['winner'])
        initial = outcome['initial_armies']
        casualties = outcome['casualties']
        for creature, count in initial[int(loser)].items():
            check(casualties[loser].get(creature, 0) == count, prefix + ': normal loser has survivors')
        check(sum(count-casualties[winner].get(creature, 0) for creature, count in initial[int(winner)].items()) > 0,
              prefix + ': normal winner has no survivors')
    if outcome:
        losses = outcome['casualties'][str(int(row['role'] == 'defender'))]
        check(row.get('permanent_army_loss_by_creature') == losses, prefix + ': casualty breakdown differs')
        check(row.get('permanent_army_loss_units') == sum(losses.values()), prefix + ': casualty total differs')
    elif row.get('permanent_army_loss_units') == 0:
        WARNINGS.append(prefix + ': unknown terminal losses encoded as zero; exclude from loss mean')


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--control',help='Optional isolated recovery control; original failure control remains preserved')
    args = parser.parse_args()
    scenarios = read(PILOT/'scenarios.json')
    cases = {case['id']: case for case in scenarios}
    case_indices = {case['id']: index for index, case in enumerate(scenarios)}
    control_path = Path(args.control) if args.control else PILOT/'pilot-control.json'
    status = read(control_path) if control_path.exists() else {}
    manifests = {}
    summaries = {}
    for name, expected_split, expected_indices in [
        ('pilot-training-battles', 'train', {0, 1, 8, 9, 16, 17}),
        ('pilot-heldout-battles', 'test', {6, 7, 14, 15, 22, 23}),
    ]:
        path = PILOT/(name+'.json')
        rows = read(path) if path.exists() else []
        manifests[name] = rows
        seen = set()
        for row in rows:
            audit_episode(row, cases, name)
            key = condition(row) + (row.get('checkpoint'),)
            check(key not in seen, name + ': duplicate episode condition ' + repr(key))
            seen.add(key)
            index = case_indices.get(row.get('scenario'))
            check(index in expected_indices, name + ': unexpected scenario index ' + repr(index))
            check(row.get('split') == expected_split, name + ': wrong data split')
            if index is not None:
                check(row.get('seed') == 2026102801+index*100, name + ': unexpected seed')
        with_outcome = [row for row in rows if row.get('terminal_outcome') is not None]
        known = [row for row in rows if row.get('terminated') and not row.get('truncated')
                 and row.get('terminal_outcome') and row['terminal_outcome'].get('result_type') == 0
                 and row['terminal_outcome'].get('winner') in [0, 1]]
        summaries[name] = dict(completed_reports=len(rows), expected_reports=24,
            wins=sum(bool(row.get('success')) for row in rows),
            truncations=sum(bool(row.get('truncated')) for row in rows),
            missing_terminal_outcome=len(rows)-len(with_outcome),
            unknown_final_losses=len(rows)-len(known),
            known_loss_mean=sum(row['permanent_army_loss_units'] for row in known)/len(known) if known else None,
            known_loss_denominator=len(known),
            unfiltered_loss_mean_valid=len(known) == len(rows),
            note='Counts of units are not creature-value-weighted losses; summarize paired conditions separately.')
    train_ids = {row['scenario'] for row in manifests['pilot-training-battles']}
    heldout_ids = {row['scenario'] for row in manifests['pilot-heldout-battles']}
    check(not train_ids.intersection(heldout_ids), 'Training/heldout scenario overlap')
    bc_path = PILOT/'bc-training.json'
    bc_summary = dict(present=bc_path.exists())
    if bc_path.exists():
        bc = read(bc_path)
        check(bc.get('completed') is True, 'BC report not completed')
        check(digest(bc['checkpoint']) == bc['sha256'], 'BC checkpoint SHA differs from training report')
        check(digest(bc['initial_checkpoint']) == bc['initial_sha256'], 'BC initial SHA differs from current source')
        bc_seen = set()
        total_samples = 0
        training_conditions = {condition(row) for row in manifests['pilot-training-battles']}
        for source in bc['source_episodes']:
            check(digest(source['report']) == source['sha256'], 'BC source report SHA differs')
            row = read(source['report'])
            check(row.get('split') == 'train' and row.get('success') and row.get('completed'), 'BC source not completed training win')
            check(row.get('policy') == 'expert', 'BC source not an expert-policy candidate')
            check(row['checkpoint'] == bc['initial_checkpoint'], 'BC source references different checkpoint')
            check(row['frozen_artifacts'].get(row['checkpoint']) == bc['initial_sha256'], 'BC source initial model SHA mismatch')
            key = condition(row)
            check(key not in bc_seen, 'BC duplicated condition ' + repr(key))
            bc_seen.add(key)
            check(key in training_conditions, 'BC source outside pilot training conditions: ' + repr(key))
            check(row['scenario'] not in heldout_ids, 'BC source has heldout scenario')
            audit_episode(row, cases, 'BC-source')
            check(source['samples'] == row['steps'], 'BC source sample count mismatch')
            total_samples += source['samples']
        check(total_samples == bc['samples'], 'BC total samples differ from source manifest')
        bc_summary.update(samples=bc['samples'], source_episodes=len(bc_seen),
            label_quality='Q2 normal-win coverage/search candidates, not validated human expert or tactic-optimal labels')
    freeze_path = PILOT/'pilot-policy-freeze.json'
    if freeze_path.exists():
        frozen = read(freeze_path)
        check(digest(frozen['checkpoint']) == frozen['sha256'], 'Frozen BC policy changed')
        check(digest(frozen['initial']) == frozen['initial_sha256'], 'Frozen initial policy changed')
        for row in manifests['pilot-heldout-battles']:
            expected = frozen['sha256'] if row['checkpoint'] == frozen['checkpoint'] else frozen['initial_sha256']
            check(row['checkpoint'] in [frozen['checkpoint'], frozen['initial']], 'Heldout uses unfrozen checkpoint')
            check(row['frozen_artifacts'].get(row['checkpoint']) == expected, 'Heldout checkpoint freeze differs')
    complete = status.get('state') == 'completed_BC_pilot'
    if complete:
        check(all(len(rows) == 24 for rows in manifests.values()), 'Completed pilot missing expected episode reports')
        check(bc_path.exists() and freeze_path.exists(), 'Completed pilot missing BC/freeze')
    result = dict(schema='human-pilot-integrity-audit-v1', audited_unix=time.time(),
        passed=not ERRORS, partial=not complete, pilot_state=status.get('state'),control_path=str(control_path),
        scope='Read-only integrity of currently completed artifacts, not teacher strength or curriculum completion',
        manifests=summaries, bc=bc_summary, errors=ERRORS, warnings=WARNINGS,
        limitations=['Current test uses the same creature recipes as training; no cross-creature or arbitrary-position generalization proof.',
                    'Normal winning trajectories do not prove each action is optimal, tactic use successful, or the teacher stronger.',
                    'Freeze chronology and unseen-test selection cannot be proven solely from self-reported timestamps.',
                    'Process exit status is not authoritative; this audit checks actual completed artifacts.',
                    'Files may be added while this partial audit runs; rerun after pilot completion.'])
    destination = HERE/'pilot-integrity-audit.json'
    temporary = destination.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    temporary.replace(destination)
    print(json.dumps(dict(passed=result['passed'], partial=result['partial'], pilot_state=result['pilot_state'],
        manifests=summaries, bc=bc_summary, errors=ERRORS, warnings=WARNINGS), ensure_ascii=False))


if __name__ == '__main__':
    main()
