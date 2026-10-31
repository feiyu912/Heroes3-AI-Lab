"""CPU-only prior-TRAIN tau provenance and final DEV NPC ordering projection."""
import collections,hashlib,json,sys
from pathlib import Path
OUT=Path(__file__).resolve().parent;HERE=OUT.parent;E=HERE.parent;LAB=Path('/root/heroes3-ai-lab')
sys.path[:0]=[str(HERE),str(E/'strategic-threat-replan-v2')]
import targets
from causal_stability_audit_v2 import parse_log,first_difference,movement_projection
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    prior=LAB/'evaluations/strategic-mainline-temperature2-train-02';elapsed=[];proofs=[];inputs=[Path(__file__),OUT/'AUDIT.json']
    for i in (0,1,4,5):
        directory=prior/f'cell-{i:02d}/admitted';_,_,_,e=targets.certify(directory);assert e['native_reward']==1
        elapsed.append(e['day_evidence']['elapsed_days']);proofs.append(e)
        inputs +=[directory/'AUDIT.json',directory/'episode.json']
    assert elapsed==[95,46,55,121] and (sorted(elapsed)[1]+sorted(elapsed)[2])/2==75
    b=LAB/'evaluations/strategic-efficiency-paired-dev-01/pair-07';projection={};metadata={}
    for arm in ('a','b'):
        native=b/arm/'native';log=native/'client.log';p=parse_log(log.read_text());projection[arm]=movement_projection(p['movements'])
        metadata[arm]=dict(last_policy_send_line=max(p['sent'].values()),server_movement_count=len(p['movements']))
        inputs.append(log)
    canonical=lambda x:json.dumps(x,sort_keys=True,separators=(',',':'))
    ca=collections.Counter(map(canonical,projection['a']));cb=collections.Counter(map(canonical,projection['b']))
    first=first_difference(projection['a'],projection['b']);assert first['index']==2324
    residual=dict(a_only=list((ca-cb).elements()),b_only=list((cb-ca).elements()))
    out=dict(passed=True,new_native_games=0,GPU_operations=0,optimizer_steps=0,
        tau_prior_TRAIN_win_elapsed_days=elapsed,tau_median=75,tau_raw_evidence_recertified_CPU=True,tau_evidence=proofs,
        pair07_first_server_projection_difference=first,pair07_projection_multiset_equal=ca==cb,pair07_projection_residual=residual,pair07_metadata=metadata,
        caveat='Exact movement multiset/order projection does not certify complete world or RNG equality.',input_sha256={str(p):sha(p) for p in inputs})
    (OUT/'SUPPLEMENT.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k not in ('input_sha256','tau_evidence')},indent=2))
if __name__=='__main__':main()
