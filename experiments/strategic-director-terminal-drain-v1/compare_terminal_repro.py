"""Read-only old timeout/new completion comparison; no retroactive old score."""
import argparse,hashlib,json,itertools
from pathlib import Path
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('old',type=Path);p.add_argument('new',type=Path);p.add_argument('proof',type=Path);p.add_argument('out',type=Path);a=p.parse_args()
    old=json.loads((a.old/'EXECUTION.json').read_text());new=json.loads((a.new/'EXECUTION.json').read_text());proof=json.loads(a.proof.read_text())
    assert old['client_exit']!=0 and not old['transport_drained']
    assert new['client_exit']==0 and proof['whole_game_valid'] and proof['native_game_completed'] and proof['transport_drained']
    comparisons={}
    for pattern in ('agent/request-*.json','agent/action-*.json'):
        left=sorted(a.old.glob(pattern));right=sorted(a.new.glob(pattern));diff=[]
        for x,y in itertools.zip_longest(left,right):
            if x is None or y is None or x.name!=y.name or sha(x)!=sha(y):diff.append(dict(old=None if x is None else x.name,new=None if y is None else y.name))
        comparisons[pattern]=dict(old_count=len(left),new_count=len(right),all_bytes_exact=not diff,first_difference=diff[:1])
    for name in ('strategy-trace.jsonl','strategy-decisions.jsonl','strategy-trace.jsonl.targets.jsonl','strategy-trace.jsonl.replan.jsonl'):
        x=a.old/name;y=a.new/name
        comparisons[name]=dict(old_exists=x.exists(),new_exists=y.exists(),bytes_exact=x.exists() and y.exists() and sha(x)==sha(y))
    inputs=[Path(__file__),a.proof,a.old/'EXECUTION.json',a.new/'EXECUTION.json',a.old/'client.log',a.new/'client.log']
    report=dict(passed=True,new_execution_certified=True,old_timeout_invalid_unscored=True,comparisons=comparisons,
                new_registry=proof['director_registry_proof'],optimizer_steps=0,training_samples=0,expert_labels=0,
                input_sha256={str(p):sha(p) for p in inputs},
                limitation='Comparison does not require or imply a deterministic hidden world. Original timeout is never rescored; this is an engineering regression, not ability evidence.')
    a.out.mkdir(parents=True,exist_ok=False);(a.out/'AUDIT.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if __name__=='__main__':main()
