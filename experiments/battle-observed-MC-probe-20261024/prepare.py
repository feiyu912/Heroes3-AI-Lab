"""Build one TRAIN-only MC fragment intervention, without environments or updates."""
from pathlib import Path
import hashlib,json,shutil,sys
import numpy as np
import torch
HERE=Path(__file__).resolve().parent;EXP=HERE.parent;NATIVE=EXP/'battle-terminal-credit-native-20261023'
sys.path[:0]=[str(NATIVE),str(EXP.parent/'research'),'/root/heroes3-ai-lab/src/gym']
import full_graph_policy as graph
from masked_ppo import gae
SOURCE=Path('/root/heroes3-ai-lab/evaluations/battle-terminal-credit-01/candidate-micro')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    assert not (HERE/'MC_TARGETS.pt').exists() and not torch.cuda.is_initialized()
    diagnosis=EXP/'takeover-20261023/battle-terminal-credit-TRAIN-diagnosis-02/AUDIT.json';assert json.loads(diagnosis.read_text())['passed']
    p=SOURCE/'phase-0';prefix=torch.load(p/'admitted-1.pt',map_location='cpu',weights_only=False);suffix=torch.load(p/'suffix.pt',map_location='cpu',weights_only=False);saved=torch.load(p/'TARGETS.pt',map_location='cpu',weights_only=False)
    parent=SOURCE/'update-61.pt';reference=SOURCE/'update-62.pt'
    assert sha(parent)=='4725dab0332ad93f3806084ce1fc01803e77f5e5ee6ca861d452b63892062840'
    assert sha(reference)=='ec26fe4bcd0987a01821f2076a4d076589008a88f6a41a63d00d5c9c0cfd0eec'
    assert prefix['behavior_checkpoint_sha256']==suffix['behavior_checkpoint_sha256']==sha(parent)
    a=prefix['arrays'];s=suffix['arrays'];keys=['reward','value','next_value','terminal','truncated'];joined={k:np.concatenate([a[k],s[k]],axis=0) for k in keys}
    g1,r1=gae(*(joined[k] for k in keys),gamma=1.,lam=1.)
    old=saved['targets'];adv=old['candidate_advantage'].copy();ret=old['candidate_returns'].copy();mask=np.zeros((32,16),bool);workers=[]
    for slot in range(16):
        if not old['eligible'][slot]:continue
        prior=np.flatnonzero(a['terminal'][:,slot]|a['truncated'][:,slot]);start=int(prior[-1])+1 if len(prior) else 0
        stop=32+int(np.flatnonzero(s['terminal'][:,slot]|s['truncated'][:,slot])[0]);assert joined['terminal'][stop,slot] and start<32
        for tick in range(start,32):
            value=float(np.sum(joined['reward'][tick:stop+1,slot],dtype=np.float64));obs=prefix['raw']['samples'][tick*16+slot]
            assert min(abs(value+.5*graph.potential(obs)-1),abs(value+.5*graph.potential(obs)+1))<2e-5
            assert abs(value-float(r1[tick,slot]))<2e-5
            ret[tick,slot]=value;adv[tick,slot]=ret[tick,slot]-a['value'][tick,slot];mask[tick,slot]=True
        workers.append(dict(slot=slot,start=start,terminal_index=stop,rows=32-start))
    assert mask.sum()==253 and np.array_equal(ret[~mask],old['candidate_returns'][~mask]) and np.array_equal(adv[~mask],old['candidate_advantage'][~mask])
    files=dict(json.loads((SOURCE/'FREEZE.json').read_text())['input_sha256']) if (SOURCE/'FREEZE.json').exists() else dict(json.loads((SOURCE.parent/'FREEZE.json').read_text())['input_sha256'])
    for item in prefix['journal']+suffix['journal']:assert sha(item['path'])==item['sha256'];files[item['path']]=item['sha256']
    for f in [parent,reference,p/'admitted-1.pt',p/'suffix.pt',p/'TARGETS.pt',p/'WORKERS.json',diagnosis]:files[str(f)]=sha(f)
    shutil.copy2(NATIVE/'leases.py',HERE/'leases.py')
    torch.save(dict(schema='observed-terminal-MC-fragment-targets-v1',reference_advantages=old['candidate_advantage'],reference_returns=old['candidate_returns'],mc_advantages=adv,mc_returns=ret,changed_fragment_mask=mask,workers=workers,behavior_sha256=sha(parent),source_prefix_sha256=sha(p/'admitted-1.pt'),source_suffix_sha256=sha(p/'suffix.pt')),HERE/'MC_TARGETS.pt')
    report=dict(passed=True,TRAIN_only=True,existing_admitted_rows=512,existing_suffix_rows_zero_loss=1024,fragment_rows=int(mask.sum()),target_rows_actually_changed=int(np.count_nonzero(adv!=old['candidate_advantage'])),max_abs_advantage_change=float(np.max(np.abs(adv-old['candidate_advantage']))),earlier_fragments_unchanged=True,MC_return_native_outcome_potential_identity_verified=True,independent_GAE_lambda1_agreement=True,parent61_sha256=sha(parent),reference62_sha256=sha(reference),new_native_games=0,GPU_operations=0,optimizer_steps=0)
    (HERE/'CPU_AUDIT.json').write_text(json.dumps(report,indent=2));files[str(HERE/'MC_TARGETS.pt')]=sha(HERE/'MC_TARGETS.pt');files[str(HERE/'CPU_AUDIT.json')]=sha(HERE/'CPU_AUDIT.json')
    (HERE/'PREPARED_INPUTS.json').write_text(json.dumps(files,indent=2));print(json.dumps(report,indent=2))
if __name__=='__main__':main()
