"""Read-only byte, native consumption and execution audit of an accepted vector batch."""
import argparse
import json
from pathlib import Path

from collect_vector import validate,audit_native_events,sha


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    if a.out.exists():raise ValueError('Refuse overwrite')
    plan=json.loads((a.run/'plan.json').read_text());batch=json.loads((a.run/'batch.json').read_text())
    accepted=[json.loads(line)for line in (a.run/'accepted-rollout.jsonl').open()]
    report=dict(plan_sha256=sha(a.run/'plan.json'),batch_sha256=sha(a.run/'batch.json'),
                accepted_rollout_sha256=sha(a.run/'accepted-rollout.jsonl'),episodes=[])
    errors=[]
    changed=[path for path,value in plan['hashes'].items()if sha(Path(path))!=value]
    for episode in batch['episodes']:
        index=episode['episode_index'];directory=a.run/f'env-{index:03d}';agent=directory/'agent'
        rows=[json.loads(line)for line in (directory/'committed.jsonl').open()]
        native=episode['native'];run=Path(native['run_dir'])
        choices=[json.loads(line)for line in (run/'strategy-decisions.jsonl').open()]
        io_ok=len(rows)==len(choices)==episode['decisions']
        for number,(row,choice)in enumerate(zip(rows,choices),1):
            path=agent/f'request-{number:08d}.json';request=validate(json.loads(path.read_text()),number)
            candidate=request['candidates'][row['action']]
            io_ok=io_ok and row['request']==request and sha(path)==row['request_sha256'] and (
                (agent/f'action-{number:08d}.json').read_bytes()==f"{row['action']}\n".encode() and
                choice['selected_candidate']==row['action'] and choice['candidates']==request['candidates'] and
                all(choice[key]==request[key]for key in ('player','day','hero','from')) and
                choice['destination']==candidate['position'] and choice['step']==candidate['next'])
        events=audit_native_events(run,len(rows),native['completed'],rows[-1]if rows else None)
        raw_hashes=(sha(run/'client.log')==native['log_sha256'] and sha(run/'strategy-trace.jsonl')==native['strategy_trace_sha256'] and
                    sha(run/'strategy-decisions.jsonl')==native['strategy_decisions_sha256'])
        archived=[row for row in accepted if row['episode_index']==index]
        expected=[dict(row,**{'return':episode['reward']})for row in rows]
        archive_ok=archived==expected
        row=dict(index=index,config=episode['config'],decisions=len(rows),native_days=native['native_calendar_last_day'],
                 native_winner=native['winner'],raw_hashes_verified=raw_hashes,io_and_consumption_verified=bool(io_ok),
                 accepted_rows_exactly_commits_plus_terminal_return=archive_ok,event_audit=events,
                 native_result_sha256=sha(run/'result.json'),worker_log_sha256=sha(directory/'worker.log'))
        report['episodes'].append(row)
        if not all((raw_hashes,io_ok,archive_ok,events['valid'],episode['valid'],native['completed'])):
            errors.append(f'episode-{index} evidence failure')
    report.update(total_samples=len(accepted),recorded_optimizer_steps=batch['actual_optimizer_steps'],
        frozen_input_changes=changed,policy_unchanged=batch['policy_unchanged'],remaining_processes_report=batch['remaining_processes'],errors=errors)
    report['passed']=not errors and not changed and batch['status']=='complete_on_policy_batch' and len(accepted)==batch['accepted_samples'] and not batch['remaining_processes'] and batch['policy_unchanged'] and batch['actual_optimizer_steps']==0
    a.out.write_text(json.dumps(report,indent=2));print(json.dumps(dict(passed=report['passed'],samples=len(accepted),errors=errors,changed=changed)))
    return 0 if report['passed']else 1


if __name__=='__main__':raise SystemExit(main())
