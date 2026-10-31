"""CPU state-machine qualification using simulated events, never native evidence."""
from pathlib import Path
import hashlib,json
class Slot:
    def __init__(self):self.native=0;self.admitted=0;self.suffix=0;self.updates=0;self.failed=False;self.ends=[]
    def stage(self):
        if self.failed:return 'failed'
        if self.native==32 and self.updates==0:return 'update1_barrier'
        if self.native==128 and self.updates==1:return 'update2_barrier'
        if self.updates==2:return 'complete'
        return 'admitted' if self.native<64 else 'suffix'
    def observe(self,terminal=False,truncated=False):
        assert self.stage() in ('admitted','suffix'),'Must honor optimizer/failure barrier'
        self.native+=1
        admitted=self.native<=64
        if admitted:self.admitted+=1
        else:self.suffix+=1
        if terminal or truncated:self.ends.append(dict(step=self.native,terminal=terminal,truncated=truncated))
        return dict(admitted=admitted,loss_weight=1 if admitted else 0)
    def update_barrier(self):
        assert self.stage() in ('update1_barrier','update2_barrier'),'No update during fixed behavior suffix'
        self.updates+=1
    def close(self):assert self.stage()=='complete','Do not close/drop a partial qualified phase'
    def fail(self):self.failed=True
def expect_reject(fn):
    try:fn()
    except AssertionError:return
    raise AssertionError('Invalid schedule accepted')
def main():
    results=[]
    for arm in ['control','candidate']:
        slots=[]
        for phase in range(4):
            for worker in range(16):
                s=Slot()
                for tick in range(128):
                    if s.stage()=='update1_barrier':s.update_barrier()
                    if tick in (64,80,96,112):expect_reject(s.update_barrier)
                    event=s.observe(terminal=((tick+worker+phase)%[17,29,61,200][worker%4]==0))
                    assert event['admitted']==(tick<64) and event['loss_weight']==int(tick<64)
                assert s.stage()=='update2_barrier';s.update_barrier();s.close();assert (s.native,s.admitted,s.suffix,s.updates)==(128,64,64,2);slots.append(s)
        results.append(dict(arm=arm,native=sum(s.native for s in slots),admitted=sum(s.admitted for s in slots),suffix=sum(s.suffix for s in slots),simulated_slot_updates=sum(s.updates for s in slots)))
    assert results[0]['native']==results[1]['native']==8192 and results[0]['admitted']==results[1]['admitted']==4096
    s=Slot();expect_reject(s.update_barrier);expect_reject(s.close)
    for _ in range(32):s.observe()
    expect_reject(s.observe);s.update_barrier()
    for _ in range(40):s.observe()
    counts=(s.native,s.admitted,s.suffix);s.fail();expect_reject(s.observe);expect_reject(s.close);assert counts==(72,64,8)
    report=dict(passed=True,stage='synthetic CPU scheduler events only',first_update_barrier=True,no_updates_during_suffix=True,update2_only_after64_suffix=True,early_terminals_do_not_reduce_native_budget=True,partial_failure_preserves_counts_and_no_loss_relabel=True,budgets=results,new_native_games=0,GPU_operations=0,actual_optimizer_steps=0,resource_locks_taken=False,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (Path(__file__).parent/'SCHEDULE_CPU.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
