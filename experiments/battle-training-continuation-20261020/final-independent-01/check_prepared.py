"""CPU fake incomplete-result rejection only; not game/learning evidence."""
import ast,importlib.util,json,tempfile,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('audit_final',HERE/'audit_final.py');audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
checks=[]
for p in (HERE/'audit_final.py',HERE.parent/'monitor-independent-01/compact_status.py'):ast.parse(p.read_text())
with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp)
    for stage,result in enumerate((None,dict(passed=False),dict(passed=True,training_completed=False),dict(passed=True,training_completed=True,arms={'control':{}},DEV=[]))):
        if result is not None:(root/'RESULT.json').write_text(json.dumps(result))
        try:audit.gate(root)
        except (FileNotFoundError,AssertionError,KeyError):checks.append(dict(stage=stage,rejected=True))
        else:raise AssertionError('Fake incomplete experiment passed final gate')
report=dict(passed=True,prepared_only=True,fake_incomplete_cases=checks,new_native_games=0,GPU_operations=0,optimizer_steps_performed=0,actual_final_evidence_checked=False,
    source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path(__file__),HERE/'audit_final.py',HERE.parent/'monitor-independent-01/compact_status.py')})
(HERE/'PREPARATION_CPU_CHECKS.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
