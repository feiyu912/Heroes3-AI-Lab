"""Strict reuse of frozen v1 artifacts; no v1 source or historical report edits."""
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
V1 = HERE.parent/'human-tactics-v1'
KNOWLEDGE = HERE.parent/'expert-knowledge-v1'
RESEARCH = HERE.parents[1]/'research'
sys.path.insert(0,str(KNOWLEDGE))
import audit_human_pilot as integrity
from graph_observation_codec import unpack


def digest(path):
    return integrity.digest(path)


def read(path):
    return json.loads(Path(path).read_text())


def validate_episode(row,index,role,policy,checkpoint):
    case = read(V1/'scenarios.json')[index]
    expected = dict(scenario=case['id'],role=role,policy=policy,checkpoint=str(checkpoint),
                    seed=2026102801+index*100,split=case['split'],tactic_id=case['tactic_id'])
    for key,value in expected.items():
        assert row.get(key) == value, ('Reused episode identity differs',key,row.get(key),value)
    assert row.get('completed') is True
    assert row['frozen_artifacts'].get(str(checkpoint)) == digest(checkpoint), 'Checkpoint bytes changed'
    integrity.ERRORS.clear()
    integrity.audit_episode(row,{case['id']:case},'recovery-v2')
    assert not integrity.ERRORS, integrity.ERRORS
    return row


def training_rows(checkpoint):
    path = V1/'pilot-training-battles.json'
    rows = read(path)
    assert len(rows) == 24, 'Preserve and reuse the complete v1 collection'
    expected = {(index,role,policy) for index in [0,1,8,9,16,17]
                for role in ['attacker','defender'] for policy in ['expert','model']}
    cases = read(V1/'scenarios.json')
    ids = {case['id']:index for index,case in enumerate(cases)}
    seen = set()
    for row in rows:
        key = (ids[row['scenario']],row['role'],row['policy'])
        assert key in expected and key not in seen
        seen.add(key)
        validate_episode(row,*key,checkpoint)
    assert seen == expected
    return rows


def eligible_sources(checkpoint):
    observations,labels,sources = [],[],[]
    for row in training_rows(checkpoint):
        outcome = row.get('terminal_outcome')
        eligible = (row['policy']=='expert' and row['split']=='train' and row['success']
                    and row['terminated'] and not row['truncated'] and outcome and outcome['result_type']==0)
        if not eligible:
            continue
        with gzip.open(row['demonstrations'],'rt') as stream:
            data = json.load(stream)
        for record in data['decisions']:
            assert record['expert_action'] in record['legal_actions']
            observation = unpack(record['observation'],record['actor_side'])
            observations.append(observation)
            labels.append(record['legal_actions'].index(record['expert_action']))
        path = V1/'runs'/(row['battle_id']+'.json')
        sources.append(dict(report=str(path),sha256=digest(path),samples=len(data['decisions']),
            filter='Q2 exploratory normal-win candidate; not Q3 tactic/source verified'))
    assert observations and {observation['lab_side'] for observation in observations} == {0,1}
    return observations,labels,sources


def validate_bc(checkpoint,output,steps=60):
    report = read(V1/'bc-training.json')
    assert report.get('completed') is True and report.get('recovery_version') == 'human-tactics-recovery-v2'
    assert report['initial_checkpoint'] == str(checkpoint) and report['initial_sha256'] == digest(checkpoint)
    assert report['checkpoint'] == str(output) and report['sha256'] == digest(output)
    assert report['gradient_steps'] == steps and report['graph_and_value_weights_unchanged']
    _,_,sources = eligible_sources(checkpoint)
    assert report['source_episodes'] == sources, 'BC source selection changed'
    assert report['samples'] == sum(source['samples'] for source in sources)
    for path,sha in report['recovery_artifacts'].items():
        assert digest(path) == sha, 'Recovery implementation changed: '+path
    return report


def frozen_recovery():
    paths = list(HERE.glob('*.py'))+[KNOWLEDGE/'graph_observation_codec.py',KNOWLEDGE/'audit_human_pilot.py']
    return {str(path):digest(path) for path in paths}
