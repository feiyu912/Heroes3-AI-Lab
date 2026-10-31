"""Production float32 GAE, with independently tested terminal eligibility."""
import numpy as np
from masked_ppo import gae
from credit_reference import target as reference
KEYS=['reward','value','next_value','terminal','truncated']
def build(prefix,suffix,arm):
    assert arm in ('control','candidate')
    proof=reference(prefix,suffix)
    base,base_ret=gae(*(prefix[k] for k in KEYS),gamma=1.,lam=.95)
    joined={k:np.concatenate((prefix[k],suffix[k]),axis=0) for k in KEYS}
    ext,ext_ret=gae(*(joined[k] for k in KEYS),gamma=1.,lam=.95)
    mask=proof['eligible'][None,:]
    candidate=np.where(mask,ext[:32],base);candidate_ret=np.where(mask,ext_ret[:32],base_ret)
    assert np.allclose(base,proof['control_advantage'],atol=1e-6,rtol=0) and np.allclose(candidate,proof['candidate_advantage'],atol=1e-6,rtol=0)
    return dict(advantage=base if arm=='control' else candidate,returns=base_ret if arm=='control' else candidate_ret,
        base_advantage=base,base_returns=base_ret,candidate_advantage=candidate,candidate_returns=candidate_ret,
        eligible=proof['eligible'],reason=proof['reason'],first_suffix_end_step=proof['first_suffix_end_step'],suffix_loss_rows=0)
