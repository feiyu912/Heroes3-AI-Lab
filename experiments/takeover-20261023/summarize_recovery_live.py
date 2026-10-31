"""Compact read-only progress view for the active recovery run."""
import json
from pathlib import Path

RUN = Path('/root/heroes3-ai-lab/evaluations/battle-terminal-credit-recovery-20261023-01')
for stage in ['candidate-phase-1', 'control-phase-2', 'candidate-phase-2',
              'control-phase-3', 'candidate-phase-3']:
    folder = RUN / stage
    print('==', stage, '==')
    result = folder / 'RESULT.json'
    progress = folder / 'PROGRESS.json'
    if result.exists():
        d = json.loads(result.read_text())
        print('RESULT passed', d.get('passed'), 'Adam', d.get('actual_Adam_steps'),
              'error', d.get('error'))
        for r in d.get('records', []):
            print(' update', r['update'], 'actual', r['actual_Adam'],
                  'cumulative', r['cumulative_Adam'],
                  'admitted', r['admitted_stage_rows'],
                  'suffix', r['suffix_stage_rows'],
                  'native', r['native_stage_rows'],
                  'resources', r.get('resources'))
    elif progress.exists():
        d = json.loads(progress.read_text())
        print('in progress; records', [(r['update'], r['actual_Adam'],
                                       r['cumulative_Adam'], r.get('resources'))
                                      for r in d.get('records', [])])
    else:
        print('not started or no progress file')
