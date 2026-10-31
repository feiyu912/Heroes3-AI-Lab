"""Synthetic trainer invalid-wave, partial-checkpoint and protocol rejection tests."""
import json
from pathlib import Path
import subprocess
import sys

if len(sys.argv)>1 and sys.argv[1]=='--invalid-wave-child':
    import parallel_trainer as trainer
    real=trainer.collect_parallel
    calls=0
    def injected(*args,**kwargs):
        global calls
        calls+=1
        if calls==2:
            kwargs['synthetic_failure_kind']='move'
        return real(*args,**kwargs)
    trainer.collect_parallel=injected
    sys.argv=[str(Path(trainer.__file__)), '--out',sys.argv[2], '--execute','--synthetic','--updates','1',
              '--environments','2','--epochs','2','--minibatch-size','16','--inference-schedule','barrier']
    raise SystemExit(trainer.main())

from parallel_trainer import read_bundle,sha
root=Path(sys.argv[1]);out=root/'trainer-failure-paths-cpu-03';out.mkdir(exist_ok=False)
here=Path(__file__).resolve().parent
def run(name,command):
    answer=subprocess.run(command,capture_output=True,text=True)
    (out/(name+'.log')).write_text(answer.stdout+answer.stderr)
    return answer
invalid=out/'invalid-wave'
a=run('invalid-wave',[sys.executable,str(Path(__file__).resolve()),'--invalid-wave-child',str(invalid)])
report=json.loads((invalid/'training.json').read_text())
partial,_=read_bundle(invalid/'failed-partial-not-resumable.pt')
zero,_=read_bundle(invalid/'update-0.pt')
invalid_ok=(a.returncode!=0 and report['optimizer_steps_total']==0 and report['optimizer_steps_this_run']==0 and
            partial['optimizer_steps_total']==0 and not partial['complete_update_boundary'] and
            not (invalid/'update-1.pt').exists() and not partial['optimizer']['state'])
base=[sys.executable,str(here/'parallel_trainer.py'),'--execute','--synthetic','--updates','2',
      '--epochs','2','--minibatch-size','16','--inference-schedule','barrier']
b=run('partial-resume',base+['--out',str(out/'partial-resume'),'--environments','2','--resume',str(invalid/'failed-partial-not-resumable.pt')])
c=run('protocol-resume',base+['--out',str(out/'protocol-resume'),'--environments','4','--resume',str(root/'trainer-cpu-split-04/update-1.pt')])
result=dict(synthetic_CPU_only=True,invalid_second_wave_after_valid_first_wave=dict(
    passed=invalid_ok,valid_episodes_preserved=len(report['episodes']),optimizer_steps=report['optimizer_steps_total'],
    completed_updates=len(report['updates']),partial_resumable=partial['complete_update_boundary']),
    partial_resume_rejected=b.returncode!=0 and 'not resumable' in b.stderr,
    changed_environments_resume_rejected=c.returncode!=0 and 'protocol/source/runtime changed' in c.stderr,
    harness_notice='Invalid-wave test intentionally monkeypatches only this private CPU subprocess to inject a real fake-engine move_failed event on wave2. Production trainer/collector sources remain unchanged.')
result['passed']=invalid_ok and result['partial_resume_rejected'] and result['changed_environments_resume_rejected']
(out/'AUDIT.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
raise SystemExit(0 if result['passed'] else 1)
