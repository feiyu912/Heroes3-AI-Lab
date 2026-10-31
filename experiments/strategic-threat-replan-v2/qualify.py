"""Three fixed execution regressions, separate from the diagnostic paired score."""
import hashlib,json,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent;LAB=Path('/root/heroes3-ai-lab');TRAIN=HERE.parent/'strategic-typed-training-v1'
OUT=LAB/'evaluations/typed-bounded-replan-qualification-01';MODEL=TRAIN/'cuda-curriculum-ack-01/update-1.pt'
CAPSULE=LAB/'evaluations/typed-bounded-replan-capsule-01';LEGACY=LAB/'evaluations/typed-schema4-ack-drain-capsule-01'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
OUT.mkdir(exist_ok=False)
files=[Path(__file__),HERE/'PLAN.md',HERE/'run_game.py',HERE/'audit_replan.py',MODEL,CAPSULE/'EXECUTION.json',LEGACY/'EXECUTION.json']
frozen={str(p):sha(p) for p in files}
(OUT/'PLAN.json').write_text(json.dumps(dict(purpose='Old-capsule/off/once engineering regression before scored diagnostic pairs',
    job=dict(map='takeover-v2-train-01-mines',seed=2026110900,player=0,opponent='EmptyAI'),source_sha256=frozen,
    native_games=3,optimizer_steps=0,scored_pairs=0),indent=2))
reports=[]
for name,capsule,mode in [('legacy',LEGACY,'off'),('off',CAPSULE,'off'),('once',CAPSULE,'once')]:
    assert all(sha(Path(p))==h for p,h in frozen.items())
    root=OUT/name;root.mkdir()
    commands=[['/usr/bin/python3',HERE/'run_game.py','--capsule',capsule,'--checkpoint',MODEL,'--map','takeover-v2-train-01-mines',
        '--seed','2026110900','--player','0','--opponent','EmptyAI','--threat-replan',mode,'--out',root/'native'],
        [LAB/'venv/bin/python',HERE.parent/'strategic-typed-native-v1/audit_game_v5.py',root/'native',root/'raw-audit']]
    if name!='legacy':commands.append(['/usr/bin/python3',HERE/'audit_replan.py',root/'native',root/'raw-audit/AUDIT.json',root/'replan-audit'])
    for i,cmd in enumerate(commands):
        r=subprocess.run(list(map(str,cmd)),capture_output=True,text=True);(root/f'command-{i}.log').write_text(r.stdout+'\nSTDERR:\n'+r.stderr)
        assert r.returncode==0,'Qualification invalid, preserve and stop: '+str(root)
    report=json.loads((root/'raw-audit/AUDIT.json').read_text());assert report['whole_game_valid'] and report['transport_drained']
    reports.append(dict(arm=name,winner=report['winner'],counts=report['counts']))
    print(json.dumps(reports[-1]),flush=True)
names=lambda r:{str(p.relative_to(r)) for pattern in ['request-*.json','action-*.json'] for p in (r/'agent').glob(pattern)}
left=OUT/'legacy/native';expected=names(left)
checks={}
for name in ['off','once']:
    right=OUT/name/'native';assert names(right)==expected
    selected=sorted(expected)+['strategy-decisions.jsonl','strategy-trace.jsonl','strategy-trace.jsonl.targets.jsonl','agent/typed-broker.jsonl']
    checks[name]=dict(files=len(selected),exact=all(sha(left/n)==sha(right/n) for n in selected))
assert all(v['exact'] for v in checks.values()),checks
result=dict(passed=True,arms=reports,legacy_comparison=checks,optimizer_steps=0,scored_pairs=0,
    limitation='No threat release expected versus EmptyAI; binding once intervention still requires real NK evidence.')
(OUT/'RESULT.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
