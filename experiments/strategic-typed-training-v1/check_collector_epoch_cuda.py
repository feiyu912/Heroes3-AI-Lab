"""Exercise real trainer entrypoint: source/runtime resume mismatches stop before Adam."""
import json,sys
from pathlib import Path
import torch
import train_update_v3 as trainer
HERE=Path(__file__).resolve().parent;OUT=HERE/'collector-epoch-cuda-check-01';OUT.mkdir(exist_ok=False)
count=0;original=torch.optim.Adam.step
def forbid_step(*args,**kwargs):
    global count
    count+=1
    raise AssertionError('Epoch preflight reached forbidden Adam step')
torch.optim.Adam.step=forbid_step
cases=[('legacy_admission',HERE/'admitted-episode-02','Collector/source epoch differs'),
       ('new_collector_old_resume',HERE/'admitted-observer-v5-01','Resume protocol/source/runtime changed')]
results=[]
try:
    for name,admission,message in cases:
        sys.argv=['train_update_v3.py','--resume',str(HERE/'cuda-curriculum-ack-01/update-1.pt'),
            '--admission',str(admission),'--capsule','/root/heroes3-ai-lab/evaluations/typed-schema4-ack-drain-capsule-01',
            '--out',str(OUT/name)]
        try:trainer.main()
        except (AssertionError,ValueError) as error:
            assert message in str(error),(name,repr(error))
            results.append(dict(case=name,rejected=str(error),optimizer_step_calls=count))
        else:raise AssertionError('Invalid epoch was accepted')
    assert count==0
    report=dict(passed=True,device='cuda',cases=results,optimizer_steps=0,
        actual_entrypoint=True,limitation='Rejection and source-epoch gates only; no continuous-vs-split native training equivalence claim.')
    (OUT/'AUDIT.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
finally:torch.optim.Adam.step=original
