"""CPU-only cross-arm check before the first differing target update."""
from pathlib import Path
import json,sys,torch
torch.set_num_threads(1)
HERE=Path(__file__).resolve().parent
PACKAGE=HERE.parent/'battle-terminal-credit-native-20261023'
sys.path.insert(0,str(PACKAGE))
import restore_learner as restore
base=Path('/root/heroes3-ai-lab/evaluations/battle-terminal-credit-01')
out=HERE/'terminal-credit-independent-01';out.mkdir(exist_ok=False)
arms={a:torch.load(base/(a+'-micro/update-61.pt'),map_location='cpu',weights_only=True) for a in ('control','candidate')}
fields=('models','optimizer_state_dict','torch_rng_state','cuda_rng_states','python_rng_state','numpy_rng_state')
checks={name:restore.digest(arms['control'][name])==restore.digest(arms['candidate'][name]) for name in fields}
assert all(x['actual_Adam_steps']==7808 and x['completed_updates']==61 for x in arms.values())
result={'completed_update':61,'actual_Adam_each':7808,'first_target_difference_update':62,'exact_cross_arm_fields':checks,
        'same_first_update_confirmed':all(checks.values()),'native_runs':0,'GPU_operations':0,'optimizer_steps':0,
        'checkpoint_sha256':{a:restore.sha(base/(a+'-micro/update-61.pt')) for a in arms}}
(out/'COMMON_FIRST_UPDATE.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
