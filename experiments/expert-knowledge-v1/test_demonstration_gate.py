"""Meaningful rejection checks, including actual engine-generated legacy data."""
import copy
import json
from pathlib import Path
import subprocess
import sys
from validate_demonstration import adapt_legacy, load

HERE = Path(__file__).resolve().parent
LEGACY = HERE.parent/'human-tactics-v1/runs/expert-dragon-breath-train-0-attacker.json.gz'


def run(path, mode, name, expected):
    result_path = HERE/(name+'.json')
    proc = subprocess.run([sys.executable,str(HERE/'validate_demonstration.py'),str(path),
        '--mode',mode,'--output',str(result_path)],capture_output=True,text=True)
    result = json.loads(result_path.read_text())
    assert result['passed'] is expected, (name,result)
    assert proc.returncode == (0 if expected else 2), (name,proc.returncode)
    return result


def main():
    records = []
    good = run(LEGACY,'bc-exploratory','legacy-exploratory-gate',True)
    records.append(dict(case='actual legacy Q2 accepted only for exploratory BC',passed=True,samples=good['samples']))
    denied = run(LEGACY,'bc-q3','legacy-q3-rejection',False)
    assert not denied['bc_q3_eligible'] and denied['q3_denials']
    records.append(dict(case='actual legacy Q2 rejected by verified Q3 gate',passed=True))
    fixture = adapt_legacy(load(LEGACY))
    fixture['source'].update(kind='human_structured',trajectory_origin='human_recorded',
        creator='SYNTHETIC VALIDATOR FIXTURE; no real human data',source_reference=None,
        permission=None,synthetic_test_fixture=True)
    for record in fixture['decisions']:
        record['action_origin'] = 'human_recorded'
    illegal = copy.deepcopy(fixture)
    illegal['decisions'][0]['expert_action'] = -999999
    path = HERE/'synthetic-illegal-human-example.jsonl'
    with path.open('w') as stream:
        stream.write(json.dumps(dict(record_type='episode',schema=illegal['schema'],source=illegal['source'],episode=illegal['episode']))+'\n')
        for record in illegal['decisions']:
            stream.write(json.dumps(dict(record_type='decision',**record))+'\n')
    denied = run(path,'audit','synthetic-illegal-action-rejection',False)
    assert any('expert action not legal' in message for message in denied['errors'])
    records.append(dict(case='synthetic human JSONL illegal action rejected',passed=True))
    video = copy.deepcopy(fixture)
    video['decisions'][0]['action_origin'] = 'video_guess'
    video_path = HERE/'synthetic-video-guess-example.json'
    video_path.write_text(json.dumps(video))
    denied = run(video_path,'audit','synthetic-video-rejection',False)
    assert any('video-guessed' in message for message in denied['errors'])
    records.append(dict(case='video-guessed action rejected as structured trajectory',passed=True))
    unknown = copy.deepcopy(fixture)
    unknown['episode']['outcome'] = None
    unknown['episode']['permanent_army_loss'] = None
    unknown_path = HERE/'synthetic-unknown-outcome-example.json'
    unknown_path.write_text(json.dumps(unknown))
    denied = run(unknown_path,'bc-q3','synthetic-unknown-outcome-rejection',False)
    assert not denied['normal_terminal'] and not denied['bc_q3_eligible']
    records.append(dict(case='unknown terminal outcome rejected by BC Q3 gate',passed=True))
    report = dict(passed=True,checks=records,real_human_trajectories_used=False,
        limitations='Gate checks integrity and required evidence; no game replay, teacher optimality or human identity authentication occurs here.')
    (HERE/'demonstration-gate-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False))


if __name__ == '__main__':
    main()
