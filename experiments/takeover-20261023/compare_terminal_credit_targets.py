"""CPU cross-arm data identity and actual target/parameter difference audit."""
from pathlib import Path
import json,sys,torch,numpy as np
torch.set_num_threads(1)
HERE=Path(__file__).resolve().parent
PACKAGE=HERE.parent/'battle-terminal-credit-native-20261023';sys.path.insert(0,str(PACKAGE))
import restore_learner as restore
root=Path('/root/heroes3-ai-lab/evaluations/battle-terminal-credit-01')
out=HERE/'terminal-credit-independent-01/MICRO_TARGET_COMPARISON.json'
assert not out.exists()
data_equal={}
for part in ('admitted-0','admitted-1','suffix'):
    paths={a:root/(a+'-micro/phase-0')/(part+'.pt') for a in ('control','candidate')}
    payload={a:torch.load(p,map_location='cpu',weights_only=False) for a,p in paths.items()}
    data_equal[part]={k:restore.digest(payload['control'][k])==restore.digest(payload['candidate'][k]) for k in ('arrays','raw')}
    del payload
target={a:torch.load(root/(a+'-micro/phase-0/TARGETS.pt'),map_location='cpu',weights_only=False)['targets'] for a in ('control','candidate')}
delta=target['candidate']['advantage']-target['control']['advantage']
models={a:restore.weight_state(torch.load(root/(a+'-micro/update-62.pt'),map_location='cpu',weights_only=True)) for a in ('control','candidate')}
sq=0.;changed=0;largest=0.
for n,t in models['control'].items():
    d=models['candidate'][n].double()-t.double()
    if torch.any(d!=0):changed+=1
    sq+=float(d.square().sum());largest=max(largest,float(d.abs().max()))
report={'same_native_data_before_first_differing_update':data_equal,'all_common_data_exact':all(all(v.values()) for v in data_equal.values()),
        'extension_eligible_workers':int(np.asarray(target['candidate']['eligible']).sum()),
        'target_changed_rows':int(np.count_nonzero(delta)),'target_max_abs_difference':float(np.abs(delta).max()),
        'update62_parameter_difference':{'changed_tensors':changed,'l2':sq**.5,'max_abs':largest},
        'new_native_games':0,'GPU_operations':0,'optimizer_steps':0,'strength_improvement_claim':False}
out.write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
