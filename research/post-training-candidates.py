"""Validate derived candidates before releasing the original final-test selector."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time
from lab_io import atomic_json
from goal_selection import score


ROOT=Path(__file__).resolve().parent
STATUS=ROOT/'post-training-candidates-control.json'
HELD=False


def selector_exists(pid):
    try:args=(Path('/proc')/str(pid)/'cmdline').read_bytes().split(b'\0')
    except FileNotFoundError:return False
    return len(args)>1 and args[1]==str(ROOT/'select-challenge-final.py').encode()


def run(command,log,env=None):
    with (ROOT/log).open('ab') as stream:
        subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT,check=True,timeout=3600,env=env)


def evaluate(path,name,manifest,role_sources=None):
    row=dict(name=name,checkpoint=str(path),policy='recovered',iteration=0,finetuning_mode='derived',
             derivation_manifest=str(manifest))
    for filename,indices,seeds,prefix in [('scenarios-v2.json',range(20,26),4,''),
                                         ('diverse-curriculum.json',range(192,204),2,'development_')]:
        for opponent,label in [('BattleAI',''),('MMAI_MODEL','upstream_')]:
            key=prefix+label+'validation_report';output=ROOT/f'{name}-{prefix}{label}validation.json'
            command=['python3',str(ROOT/'evaluate-battles.py'),'--checkpoint',str(path),'--policies','recovered',
                     '--scenario-file',str(ROOT/filename),'--scenarios',*map(str,indices),'--seeds',str(seeds),
                     '--workers','12','--opponent',opponent,'--output',str(output)]
            if opponent=='MMAI_MODEL':command+=['--opponent-model-template','DATA/MMAI/models/lab-upstream-{role}.onnx']
            run(command,output.stem+'.log')
            data=json.loads(output.read_text());assert data['checkpoint']==str(path)
            summary=data['summary'][0]
            assert summary['battles']==48 and summary['invalid_actions']==0 and summary['truncated']==0
            assert summary['non_normal_terminations']==0 and data['artifacts_checked_before_and_after']
            if role_sources:
                for role,source in role_sources.items():
                    original=json.loads(Path(source[key]).read_text())
                    expected={(x['scenario'],x['role'],x['seed']):x for x in original['battles'] if x['role']==role}
                    for actual in (x for x in data['battles'] if x['role']==role):
                        prior=expected[actual['scenario'],role,actual['seed']]
                        for field in ['success','steps','terminal_outcome','action_types']:
                            assert actual[field]==prior[field],f'Role-combination mismatch: {field}'
            row[key]=str(output);row[prefix+label+'validation']=summary
    score(row)
    return row


def main(pid):
    global HELD
    assert selector_exists(pid),'Original selector must be live; do not start a duplicate final suite'
    assert not list(ROOT.glob('fresh-*-vs-*.json')),'Final suite already started; use a new confirmation protocol'
    atomic_json(ROOT/'post-training-candidates-plan.json',dict(created_unix=time.time(),final_test_read=False,
        basis='Observed B64/B128 validation trade-off, before any fresh final testing',
        candidates='Best predicted role combination if better than any single; three weight interpolations alpha .25/.50/.75',
        donors='Scheduled recovered candidates only. Goal-score leader and development BattleAI leader; if identical, highest-scoring different checkpoint.',
        selection_rule='Fair-mirror primary goal_selection.score v2 (goal-selection-mirror-alignment.json); old unequal-army stress only for diagnostics/ties. All derived candidates require four real 48-battle validations; final criteria unchanged.',
        source='https://proceedings.mlr.press/v162/wortsman22a.html',
        caveat='Weight averaging evidence in vision is only motivation; improvement in this RL task must be measured.'))
    os.kill(pid,signal.SIGSTOP)
    HELD=True
    atomic_json(STATUS,dict(state='waiting_for_full_graph_validation',selector_pid=pid,selector_intentionally_held=True))
    while True:
        control=json.loads((ROOT/'goal-v5-control.json').read_text())
        assert control['state']!='failed','Scheduled experiments failed; repair before final testing'
        if control['state']=='experiments_complete':break
        time.sleep(10)
    from derived_models import materialize
    original=json.loads((ROOT/'goal-v5-validation.json').read_text())
    rows=[row for row in original if not row['name'].startswith('v6-')]
    bases=[row for row in rows if row['policy']=='recovered']
    for filename in ['goal-v5-selection.json','goal-v5-validation.json']:
        backup=ROOT/(filename+'.before-derived')
        if not backup.exists():shutil.copyfile(ROOT/filename,backup)
    atomic_json(STATUS,dict(state='validating_derived_candidates',selector_pid=pid,selector_intentionally_held=True))
    run(['/root/heroes3-ai-lab/venv/bin/python',str(ROOT/'propose-role-portfolio.py')],'post-training-role-proposal.log')
    proposal=json.loads((ROOT/'role-portfolio-proposal.json').read_text())
    if proposal['promising']:
        names={row['name']:row for row in bases};best=proposal['best_portfolio']
        sources={role:names[best[role]] for role in ['attacker','defender']}
        path,manifest=materialize('roles',sources['attacker']['checkpoint'],sources['defender']['checkpoint'])
        rows.append(evaluate(path,'v6-role-portfolio',manifest,sources))
        atomic_json(ROOT/'goal-v5-validation.json',rows)
    left=max(bases,key=score)
    right=max(bases,key=lambda row:(row['development_validation']['win_rate'],row['development_upstream_validation']['win_rate'],score(row)))
    if left['checkpoint']==right['checkpoint']:
        right=max((row for row in bases if row['checkpoint']!=left['checkpoint']),key=score)
    for alpha in [.25,.50,.75]:
        path,manifest=materialize('lerp',left['checkpoint'],right['checkpoint'],alpha)
        rows.append(evaluate(path,f'v6-soup-{int(alpha*100):03}',manifest))
        atomic_json(ROOT/'goal-v5-validation.json',rows)
    best=dict(max(rows,key=score))
    best['selection']='Validation only, fair-mirror primary normalized goal score v2. Old unequal-army stress retained as diagnostic/tie-breaker. Added independently verified role combinations and three interpolations before any final test; final criteria unchanged and fresh outcomes never inspected.'
    best['validation_score']=score(best)
    atomic_json(ROOT/'goal-v5-selection.json',best)
    # Native export is deployment QA on training maps, and shares the simulator
    # lock with the final all-layer continuation probe.
    if best['policy']=='recovered':
        with Path('/root/heroes3-ai-lab/evaluations/.pool-lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            command=['bash',str(ROOT/'run-lab.sh'),str(ROOT/'verify-selected-native-export.py'),
                     '--checkpoint',best['checkpoint'],'--output-dir',str(ROOT.parent/'models/goal-v5-native-selected')]
            run(command,'selected-native-export.log',dict(os.environ,LAB_PYTHON='/root/heroes3-ai-lab/gpu-venv/bin/python'))
    from final_policy_freeze import save as freeze_selection
    freeze_selection(best)
    control.update(selected=best['name'],score=best['validation_score'],post_training_candidates_complete=True,updated_unix=time.time())
    atomic_json(ROOT/'goal-v5-control.json',control)
    atomic_json(STATUS,dict(state='completed',selected=best['name'],selector_pid=pid,
        selector_intentionally_held=False,candidate_reports=len(rows),final_test_read=False))
    assert selector_exists(pid)
    os.kill(pid,signal.SIGCONT)
    print('Derived candidates verified; final selector released:',best['name'],flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--selector-pid',type=int,required=True)
    args=parser.parse_args()
    try:main(args.selector_pid)
    except BaseException as error:
        atomic_json(STATUS,dict(state='failed',error=repr(error),selector_pid=args.selector_pid))
        if HELD:
            control=json.loads((ROOT/'goal-v5-control.json').read_text())
            control.update(state='failed',post_training_error=repr(error))
            atomic_json(ROOT/'goal-v5-control.json',control)
            if selector_exists(args.selector_pid):os.kill(args.selector_pid,signal.SIGCONT)
        raise
