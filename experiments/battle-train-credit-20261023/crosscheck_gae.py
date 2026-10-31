"""Independent direct finite-sum check of actual54 saved TRAIN GAE arrays."""
import hashlib,json,sys
from pathlib import Path
import numpy as np
import torch
ROOT=Path(__file__).resolve().parent.parent.parent;sys.path.insert(0,str(ROOT/'research'))
from masked_ppo import gae
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
records=[];maximum=0.
for arm in ['control','candidate']:
    t=json.loads((Path('/root/heroes3-ai-lab/evaluations/battle-continuation-lr-paired-01')/arm/'training.json').read_text())
    for record in t['records'][:27]:
        path=Path(record['rollout']['path']);assert sha(path)==record['rollout']['sha256'];r=torch.load(path,map_location='cpu',weights_only=False)
        expected,_=gae(r['rewards'],r['values'],r['next_values'],r['terminated'],r['truncated'],gamma=1.,lam=.95)
        reward,value,nxt=[np.asarray(r[k],np.float64) for k in ['rewards','values','next_values']];term,trunc=[np.asarray(r[k],bool) for k in ['terminated','truncated']];delta=reward+nxt*(~term)-value
        direct=np.zeros((32,16),np.float64)
        for tick in range(32):
            for slot in range(16):
                for future in range(tick,32):
                    direct[tick,slot]+=(.95**(future-tick))*delta[future,slot]
                    if term[future,slot] or trunc[future,slot]:break
        error=float(np.max(np.abs(direct-expected)));assert error<1e-6;maximum=max(maximum,error);records.append(dict(arm=arm,update=record['update'],rollout_sha256=sha(path),maximum_absolute_error=error))
assert len(records)==54
out=Path(__file__).parent/'GAE_DIRECT_CHECK.json';out.write_text(json.dumps(dict(passed=True,rollouts=54,actual_rows=27648,independent_direct_finite_sum=True,maximum_absolute_error=maximum,absolute_tolerance=1e-6,records=records,new_native_games=0,GPU_operations=0,optimizer_steps=0,source_sha256=sha(Path(__file__))),indent=2)+'\n')
print(json.dumps(dict(passed=True,maximum_absolute_error=maximum)))
