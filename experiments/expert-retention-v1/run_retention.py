"""Fixed development retention diagnostics. Preparation never starts evaluations."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[1]
RESEARCH = LAB/'research'
sys.path.insert(0,str(RESEARCH))
from lab_io import atomic_json
from battle_outcome_audit import audit

V1 = LAB/'experiments/human-tactics-v1'
WAIT = LAB/'experiments/expert-knowledge-v1/wait-variant-v2'
B64 = '/root/heroes3-ai-lab/models/graph-finetune/1792068859379237126/update-64.pt'
SCENARIOS = RESEARCH/'diverse-curriculum.json'
INDICES = list(range(192,240))
TEMPLATE = 'DATA/MMAI/models/lab-upstream-{role}.onnx'
MODELS = [dict(name='b64-baseline',checkpoint=B64,report=None,freeze=None,control=None),
    dict(name='human-q2-bc',checkpoint=str(V1/'models/bc-policy.pt'),report=str(V1/'bc-training.json'),
         freeze=str(V1/'pilot-policy-freeze.json'),control=str(LAB/'experiments/human-tactics-recovery-v2/pilot-control.json')),
    dict(name='source-wait-bc',checkpoint=str(WAIT/'models/source-wait-bc.pt'),report=str(WAIT/'source-bc-training.json'),
         freeze=str(WAIT/'source-bc-freeze.json'),control=str(WAIT/'source-bc-control.json'))]
CACHE = {}


def digest(path):
    path = Path(path)
    stat = path.stat()
    key = (str(path),stat.st_size,stat.st_mtime_ns)
    if key not in CACHE:
        hasher = hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda:stream.read(1024*1024),b''):
                hasher.update(block)
        CACHE[key] = hasher.hexdigest()
    return CACHE[key]


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def prepare():
    cases = read(SCENARIOS)
    assert len(cases) >= 240
    selected = [cases[index] for index in INDICES]
    assert len({case['id'] for case in selected}) == 48
    maps = {}
    for case in selected:
        path = Path('/root/heroes3-ai-lab/data/vcmi/Maps')/case['map']
        maps[str(path)] = digest(path)
        assert not case.get('sha256') or maps[str(path)]==case['sha256']
    public = {str(Path('/root/heroes3-ai-lab/data/vcmi/Data/MMAI/models')/('lab-upstream-'+role+'.onnx')):
              digest(Path('/root/heroes3-ai-lab/data/vcmi/Data/MMAI/models')/('lab-upstream-'+role+'.onnx'))
              for role in ['attacker','defender']}
    plan = dict(schema='expert-retention-plan-v1',scope='Development retention diagnosis; never independent confirmation or test-based model selection',
        models=MODELS,baseline_sha256=digest(B64),scenario_file=str(SCENARIOS),scenario_sha256=digest(SCENARIOS),
        scenario_indices=INDICES,scenario_ids=[case['id'] for case in selected],map_sha256=maps,
        roles=['attacker','defender'],seeds_per_scenario_role=1,
        seed_formula='2026101400 + scenario_index * 100 + 0',opponents=['BattleAI','MMAI_MODEL'],
        opponent_model_template=TEMPLATE,public_opponent_sha256=public,policies=['recovered'],
        workers=12,battles_per_model_opponent=96,total_planned_battles=576,
        source_quality='Human 185 Q2 labels and four source WAIT first actions remain unproven optimal; aging confound retained',
        controller_sha256=digest(__file__),evaluator_sha256=digest(RESEARCH/'evaluate-battles.py'))
    destination = HERE/'retention-plan.json'
    if destination.exists():
        assert read(destination)==plan, 'Frozen retention plan differs; preserve evidence and repair explicitly'
    else:
        atomic_json(destination,plan)
    return plan


def validate_model(model,plan):
    if model['name']=='b64-baseline':
        assert digest(model['checkpoint'])==plan['baseline_sha256']
        return dict(checkpoint=model['checkpoint'],sha256=plan['baseline_sha256'])
    report_path,freeze_path = Path(model['report']),Path(model['freeze'])
    if model.get('control') and Path(model['control']).exists():
        state = read(model['control']).get('state','')
        if state in ['failed','repair_needed','needs_repair']:
            raise AssertionError(model['name']+': explicit upstream failure; preserve artifacts and repair upstream')
    if not report_path.exists() or not freeze_path.exists():
        return None
    report,frozen = read(report_path),read(freeze_path)
    assert report.get('completed') is True, model['name']+': training report is not completed'
    assert report.get('checkpoint')==model['checkpoint'] and frozen.get('checkpoint')==model['checkpoint']
    sha = digest(model['checkpoint'])
    assert report.get('sha256')==sha and frozen.get('sha256')==sha, model['name']+': report/freeze/model SHA mismatch'
    initial_path = report.get('initial_checkpoint',report.get('initial'))
    assert initial_path==B64 and report.get('initial_sha256')==plan['baseline_sha256']
    assert frozen.get('initial')==B64 and frozen.get('initial_sha256')==plan['baseline_sha256']
    assert frozen.get('test_read',False) is False and frozen.get('test_results_read',False) is False
    if model['name']=='human-q2-bc':
        assert report.get('quality_tier')=='Q2-exploratory' and report.get('gradient_steps')==60
        assert report.get('recovery_version')=='human-tactics-recovery-v2'
        assert report.get('source_episodes')
        for source in report['source_episodes']:
            assert digest(source['report'])==source['sha256']
            row = read(source['report'])
            assert row['split']=='train' and row['policy']=='expert' and row['success']
            assert row['frozen_artifacts'].get(B64)==plan['baseline_sha256']
        for path,expected in report['recovery_artifacts'].items():
            assert digest(path)==expected
    else:
        assert report.get('samples')==4 and report.get('steps')==60 and report.get('trained_on_human_replay') is False
        assert digest(report['dataset'])==report['dataset_sha256']
        assert digest(WAIT/'heldout-scenarios.json')==frozen['heldout_definition_sha256']
    return dict(checkpoint=model['checkpoint'],sha256=sha,training_report_sha256=digest(report_path),freeze_sha256=digest(freeze_path))


def verify_report(path,model,model_freeze,opponent,plan):
    data = read(path)
    assert data['checkpoint']==model['checkpoint'] and data['scenario_file']==str(SCENARIOS)
    assert data['scenario_ids']==INDICES and data['opponent']==opponent
    assert data.get('workers')==12
    assert data.get('opponent_model_template')==(TEMPLATE if opponent=='MMAI_MODEL' else None)
    assert data.get('opponent_model_dir') is None and data.get('teacher_turns')==2
    assert [row['policy'] for row in data['summary']]==['recovered']
    assert len(data['battles'])==96 and data.get('artifacts_checked_before_and_after') is True
    frozen = data['frozen_artifacts']
    assert frozen.get(model['checkpoint'])==model_freeze['sha256']
    assert frozen.get(str(SCENARIOS))==plan['scenario_sha256']
    assert frozen.get(str(RESEARCH/'evaluate-battles.py'))==plan['evaluator_sha256']
    for name,sha in plan['map_sha256'].items():
        assert frozen.get(name)==sha
    if opponent=='MMAI_MODEL':
        for name,sha in plan['public_opponent_sha256'].items():
            assert frozen.get(name)==sha
    for filename,expected in frozen.items():
        assert digest(filename)==expected, 'Frozen evaluation artifact changed: '+filename
    cases = read(SCENARIOS)
    expected = {(cases[index]['id'],role,2026101400+index*100) for index in INDICES for role in ['attacker','defender']}
    seen = set()
    for row in data['battles']:
        key = (row['scenario'],row['role'],row['seed'])
        assert key in expected and key not in seen
        seen.add(key)
        assert row['engine_seed']==row['seed'] and row['checkpoint']==model['checkpoint']
        assert row['policy']=='recovered' and row['opponent']==opponent and row['invalid_actions']==0
        expected_model = TEMPLATE.format(role='defender' if row['role']=='attacker' else 'attacker') if opponent=='MMAI_MODEL' else None
        assert row.get('opponent_model')==expected_model
    assert seen==expected
    audited = audit(data['battles'])
    summary = data['summary'][0]
    assert summary['battles']==96 and summary['wins']==audited['verified_wins']
    assert summary['truncated']==sum(row['truncated'] for row in data['battles'])
    return data


def command(model,opponent,output):
    result = [sys.executable,str(RESEARCH/'evaluate-battles.py'),'--checkpoint',model['checkpoint'],
        '--policies','recovered','--scenario-file',str(SCENARIOS),'--scenarios',*map(str,INDICES),
        '--seeds','1','--workers','12','--opponent',opponent,'--output',str(output)]
    if opponent=='MMAI_MODEL':
        result.extend(['--opponent-model-template',TEMPLATE])
    return result


def execute(plan):
    results = []
    for model in MODELS:
        while True:
            pinned = validate_model(model,plan)
            if pinned:
                break
            atomic_json(HERE/'control.json',dict(state='waiting_for_upstream_report_and_freeze',model=model['name'],poll_seconds=30))
            time.sleep(30)
        for opponent in plan['opponents']:
            assert prepare()==plan
            output = HERE/(model['name']+'-'+opponent+'-development.json')
            atomic_json(HERE/'control.json',dict(state='development_retention_evaluation',model=model['name'],opponent=opponent,
                workers=12,independent_confirmation=False))
            if not output.exists():
                # evaluate-battles owns the shared flock for its entire 12-worker job.
                # Do not acquire it here as well: that would deadlock the subprocess.
                with (HERE/(output.stem+'.log')).open('ab') as log:
                    subprocess.run(command(model,opponent,output),stdout=log,stderr=subprocess.STDOUT,check=True)
            data = verify_report(output,model,pinned,opponent,plan)
            results.append(dict(model=model['name'],opponent=opponent,checkpoint_sha256=pinned['sha256'],report=str(output),
                report_sha256=digest(output),summary=data['summary'][0],
                role_wins={role:sum(row['success'] for row in data['battles'] if row['role']==role) for role in ['attacker','defender']}))
            atomic_json(HERE/'development-results.json',dict(complete=False,results=results,scope=plan['scope']))
    assert len(results)==6
    atomic_json(HERE/'development-results.json',dict(complete=True,results=results,scope=plan['scope'],
        goal_achieved=False,independent_confirmation_run=False,total_battles=576))
    atomic_json(HERE/'control.json',dict(state='development_retention_complete',goal_achieved=False,independent_confirmation_run=False))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--prepare-only',action='store_true')
    args = parser.parse_args()
    plan = prepare()
    if args.prepare_only:
        jobs = [command(model,opponent,HERE/(model['name']+'-'+opponent+'-development.json'))
                for model in MODELS for opponent in plan['opponents']]
        assert len(jobs)==6 and plan['total_planned_battles']==6*48*2
        assert all(command_.count('--seeds')==1 and command_[command_.index('--seeds')+1]=='1' for command_ in jobs)
        assert all(command_[command_.index('--workers')+1]=='12' for command_ in jobs)
        atomic_json(HERE/'static-check.json',dict(passed=True,evaluation_started=False,GPU_started=False,
            fixed_models=[model['name'] for model in MODELS],jobs=len(jobs),total_battles=576,
            plan_sha256=digest(HERE/'retention-plan.json'),commands=jobs))
        print(json.dumps(dict(prepared=True,evaluation_started=False,jobs=len(jobs),total_battles=576)),flush=True)
        return
    execute(plan)


if __name__=='__main__':
    try:
        main()
    except BaseException as error:
        atomic_json(HERE/'control.json',dict(state='repair_needed',error=repr(error),results_fabricated=False,independent_confirmation=False))
        raise
