"""CPU/static checks; temporary fixtures are not native evidence or training."""
import ast,hashlib,importlib.util,json,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('audit_final',HERE/'audit_final.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
checks=[]
with tempfile.TemporaryDirectory() as tmp:
    p=Path(tmp)
    for stage in range(4):
        if stage==1:(p/'RESULT.json').write_text(json.dumps(dict(passed=False)))
        if stage==2:(p/'training.json').write_text(json.dumps(dict(completed=True,records=[{}]*29)))
        if stage==3:
            (p/'RESULT.json').write_text(json.dumps(dict(passed=True,training_completed=True,DEV=[])))
            (p/'training.json').write_text(json.dumps(dict(completed=True,records=[{}]*30)))
        try:mod.gate(p)
        except (ValueError,FileNotFoundError):checks.append(dict(stage=stage,rejected=True))
        else:raise AssertionError('Incomplete fake fixture admitted')
support=(HERE.parent/'support.py').read_text();trainer=(HERE.parent/'train_last_graph.py').read_text();curriculum=(HERE.parent/'curriculum.py').read_text()
for text in (support,trainer,curriculum):ast.parse(text)
assert "assert sha(a.checkpoint)==B64 and not a.resume" in support
branch=trainer.split('if args.resume:',1)[1].split('    cases=',1)[0]
assert 'optimizer.load_state_dict' in branch and 'torch.set_rng_state' in branch
assert 'setstate' not in branch and 'numpy_rng_state' not in branch and "counter['steps']" not in branch
assert 'phase=(previous+iteration)//args.rotate_every' in trainer and '0<=phase<PHASES' in curriculum and 'PHASES=15' in curriculum
report=dict(passed=True,scope='Static source and fake incomplete-final fixtures only; no training/native recovery executed',gate_negative_tests=checks,
    resume_CLI_qualified=False,resume_explicitly_rejected=True,latent_branch_missing_restores=['Python RNG','NumPy RNG','cumulative optimizer hook counter'],
    phase_after_completed_30=30//2,registered_phase_count=15,native_environment_restorable=False,
    new_native_games=0,GPU_operations=0,optimizer_steps_performed=0,
    source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (HERE/'audit_final.py',HERE.parent/'support.py',HERE.parent/'train_last_graph.py',HERE.parent/'curriculum.py',Path(__file__))})
(HERE/'READINESS_CPU_CHECKS.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
