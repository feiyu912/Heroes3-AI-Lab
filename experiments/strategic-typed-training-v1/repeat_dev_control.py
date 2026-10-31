"""One prespecified same-policy replay: engine variability control, not score selection."""
import hashlib,json,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent;LAB=Path('/root/heroes3-ai-lab')
OUT=LAB/'evaluations/typed-curriculum-paired-dev-03/pair-03/a'
CHECKPOINT=HERE/'cuda-update-engineering-01/update-1.pt'
CAPSULE=LAB/'evaluations/typed-schema4-ack-drain-capsule-01'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,indent=2))
OUT.mkdir(parents=True,exist_ok=False)
sources=[Path(__file__),HERE/'evaluate_game_v2.py',HERE/'live_jsonl.py',HERE/'evaluation_broker.py',HERE/'model_io.py',CHECKPOINT,CAPSULE/'EXECUTION.json']
frozen={str(p):sha(p) for p in sources}
write(OUT/'CONTROL_PLAN.json',dict(purpose='One same-baseline-policy repeat of previously divergent pair3, retained regardless of outcome',
    reference=str(LAB/'evaluations/typed-curriculum-paired-dev-02/pair-03/a'),
    map='takeover-v2-dev-01-river',opponent='Nullkiller2',player=1,seed=2026110603,
    native_games_planned=1,optimizer_steps=0,training_samples=0,finaltest_touched=False,input_sha256=frozen,
    limitation='Diagnostic control outside the completed eight-pair endpoint. No changed opponent, model, rules or tie-breaking.'))
cmd=['/usr/bin/python3',str(HERE/'evaluate_game_v2.py'),'--capsule',str(CAPSULE),'--checkpoint',str(CHECKPOINT),
     '--player','1','--opponent','Nullkiller2','--map','takeover-v2-dev-01-river','--seed','2026110603','--out',str(OUT/'native')]
r=subprocess.run(cmd,capture_output=True,text=True);(OUT/'execution.log').write_text(r.stdout+'\nSTDERR:\n'+r.stderr)
assert r.returncode==0,'Control game launcher failed; preserve evidence and do not retry silently'
cmd=[str(LAB/'venv/bin/python'),str(HERE.parent/'strategic-typed-native-v1/audit_game_v5.py'),str(OUT/'native'),str(OUT/'audit')]
r=subprocess.run(cmd,capture_output=True,text=True);(OUT/'audit.log').write_text(r.stdout+'\nSTDERR:\n'+r.stderr)
assert r.returncode==0 and all(sha(Path(p))==h for p,h in frozen.items())
a=json.loads((OUT/'audit/AUDIT.json').read_text());assert a['whole_game_valid'] and a['native_game_completed'] and a['transport_drained'] and not a['contract_errors']
report=dict(passed=True,winner=a['winner'],counts=a['counts'],audit_sha256=sha(OUT/'audit/AUDIT.json'),optimizer_steps=0,training_samples=0,native_games=1)
write(OUT/'CONTROL_RESULT.json',report);print(json.dumps(report),flush=True)
