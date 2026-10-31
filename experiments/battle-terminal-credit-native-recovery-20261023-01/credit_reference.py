"""CPU reference target and exact admission/native-budget ledger. No environments."""
import numpy as np
PREFIX=32
DRAIN=64
WORKERS=16
def gae(reward,value,next_value,terminal,truncated,gamma=1.,lam=.95):
    reward,value,next_value=[np.asarray(x,np.float64) for x in (reward,value,next_value)]
    terminal,truncated=[np.asarray(x,bool) for x in (terminal,truncated)]
    assert reward.shape==value.shape==next_value.shape==terminal.shape==truncated.shape
    answer=np.zeros_like(reward);tail=np.zeros(reward.shape[1:])
    for tick in range(len(reward)-1,-1,-1):
        delta=reward[tick]+gamma*next_value[tick]*(~terminal[tick])-value[tick]
        tail=delta+gamma*lam*(~(terminal[tick]|truncated[tick]))*tail;answer[tick]=tail
    return answer,answer+value
def target(prefix,suffix):
    """Only continuing final fragments with observed normal suffix terminal extend.

    Return original prefix targets for a cap/nonterminal truncation, and always
    preserve prefix loss membership. Suffix rows never receive PPO loss weight.
    Arrays carry already-shaped real rewards; this function creates no rewards.
    """
    keys=['reward','value','next_value','terminal','truncated']
    assert all(np.asarray(prefix[k]).shape==(PREFIX,WORKERS) for k in keys)
    assert all(np.asarray(suffix[k]).shape==(DRAIN,WORKERS) for k in keys)
    base,base_return=gae(*(prefix[k] for k in keys));joined={k:np.concatenate((prefix[k],suffix[k]),axis=0) for k in keys}
    extended,extended_return=gae(*(joined[k] for k in keys));eligible=np.zeros(WORKERS,bool);reason=[];first_end=[]
    for slot in range(WORKERS):
        if prefix['terminal'][-1,slot] or prefix['truncated'][-1,slot]:
            reason.append('prefix_already_ended');first_end.append(None);continue
        ends=np.flatnonzero(suffix['terminal'][:,slot]|suffix['truncated'][:,slot])
        if not len(ends):reason.append('cap_no_terminal_keep_original_bootstrap');first_end.append(None);continue
        tick=int(ends[0]);first_end.append(tick+1)
        if suffix['terminal'][tick,slot]:eligible[slot]=True;reason.append('real_terminal_extension')
        else:reason.append('nonterminal_truncation_keep_original_bootstrap')
    candidate=np.where(eligible[None,:],extended[:PREFIX],base);returns=np.where(eligible[None,:],extended_return[:PREFIX],base_return)
    return dict(control_advantage=base,control_return=base_return,candidate_advantage=candidate,candidate_return=returns,eligible=eligible,reason=reason,first_suffix_end_step=first_end,prefix_loss_rows=PREFIX*WORKERS,suffix_loss_rows=0)
class Budget:
    """Fixed128 real native transitions/slot/phase, exactly64 admitted rows."""
    def __init__(self,phases=4):self.phases=phases;self.counts={};self.updates=[]
    def phase(self,phase,slot_keys):
        assert 0<=phase<self.phases and len(slot_keys)==WORKERS and len(set(slot_keys))==WORKERS
        assert phase not in self.counts
        self.counts[phase]=[dict(key=key,admitted=64,suffix_observed=64,suffix_loss_rows=0,native=128) for key in slot_keys]
        self.updates.extend([60+phase*2+1,60+phase*2+2])
    def summary(self):
        rows=[r for phase in sorted(self.counts) for r in self.counts[phase]]
        return dict(phases=len(self.counts),admitted=sum(r['admitted'] for r in rows),suffix_observed=sum(r['suffix_observed'] for r in rows),native=sum(r['native'] for r in rows),loss_rows=sum(r['admitted']+r['suffix_loss_rows'] for r in rows),global_updates=self.updates,planned_Adam_calls=128*len(self.updates),actual_Adam_calls_not_certified=True)
