"""Read historical pilot02 execution evidence; never rewrite training history."""
import json
from pathlib import Path
import sys

from collect_vector import audit_native_events, sha

training=Path(sys.argv[1]);out=Path(sys.argv[2])
out.mkdir(parents=True,exist_ok=False)
before=sha(training)
report=json.loads(training.read_text())
episodes=[]
for index,episode in enumerate(report['episodes']):
    run=Path(episode['native']['run_dir'])
    rollout=Path(episode['rollout_dir'])/'rollout.jsonl'
    rows=[json.loads(line) for line in rollout.open()]
    audit=audit_native_events(run,len(rows),bool(episode['native'].get('completed')),rows[-1] if rows else None)
    lines=(run/'client.log').read_text(errors='replace').splitlines()
    last_step=max((i for i,line in enumerate(lines) if 'DirectorAI: step hero' in line),default=0)
    tail=[dict(line=i+1,text=lines[i]) for i in range(max(0,last_step-15),min(len(lines),last_step+80))]
    episodes.append(dict(index=index,config=episode['config'],historical_valid=episode['valid'],historical_reward=episode['reward'],
        decisions=len(rows),rollout_sha256=sha(rollout),log_sha256=sha(run/'client.log'),
        historical_log_sha_matches=sha(run/'client.log')==episode['native']['log_sha256'],
        current_execution_audit=audit,last_action=rows[-1] if rows else None,last_step_context=tail))
result=dict(historical_training_sha256=before,training_unchanged=sha(training)==before,episodes=episodes,
    original_updates_preserved=report['updates'],
    note='Two real PPO updates remain established by saved model/Adam evidence. Historical decision-consumption checks did not guarantee every chosen action executed. This separate stricter audit does not rewrite rewards/results/checkpoints or retroactively claim corrected training data.')
(out/'AUDIT.json').write_text(json.dumps(result,indent=2))
bad=[e for e in episodes if e['historical_valid'] and not e['current_execution_audit']['valid']]
(out/'RESULTS.md').write_text('# Historical pilot02 terminal execution audit\n\n'
    f'Original training.json SHA256 `{before}` is unchanged. The original two real PPO updates and weight files are retained.\n\n'
    f'{len(bad)} previously valid episodes fail the new stricter execution/event gate; inspect AUDIT.json for exact raw log lines, action records and classifications. '
    'This identifies a historical consumption-versus-execution gap and does not revise old rewards, wins/losses or optimizer history.\n\n'
    'For the first EmptyAI victory, a new DirectorAI move is issued after BattleEnded and before gameOver, without a matching service-side move/reply. '
    'It must not be treated as an executed training action merely because the preceding battle won. '
    'A missing final ACK after actual execution is separately classified; real final military visits may instead be confirmed by the server request, same-hero visit and native battle/capture outcome.\n')
print(json.dumps(dict(training_unchanged=result['training_unchanged'],historically_valid_but_currently_rejected=len(bad),episodes=len(episodes))))
