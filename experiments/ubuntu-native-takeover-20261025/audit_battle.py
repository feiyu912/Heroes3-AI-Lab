"""Independent full raw-chain and CPU NN replay of Ubuntu migration games."""
import argparse,hashlib,importlib.util,json,sys,time
from pathlib import Path
import torch
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parent.parent;R=PROJECT/'research'
sys.path[:0]=[str(R)]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(name,p):
    s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def main():
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=False);torch.set_num_threads(1);assert not torch.cuda.is_initialized()
    result=json.loads((a.run/'RESULT.json').read_text());assert result['passed'] and len(result['games'])==4
    frozen=json.loads((a.run/'FREEZE.json').read_text())['files'];assert all(sha(q)==h for q,h in frozen.items())
    helper=load('_raw_audit',PROJECT/'experiments/battle-observed-MC-DEV-20261024/dev_utils.py')
    graph=load('_NN_independent',R/'recovered-graph.py');records=[];count=0;ml=mv=mp=0.;start=time.monotonic()
    with torch.inference_mode():
        for item in result['games']:
            report=Path(item['report']);assert sha(report)==item['sha256'];g=json.loads(report.read_text())
            e,last,types,digest=helper.inspect_steps(Path(g['step_evidence']['path']),g['step_evidence']['identity'])
            assert e==g['step_evidence'] and digest==g['trajectory_sha256'] and types==g['action_types']
            assert json.loads(json.dumps(last['next_obs']['terminal_outcome']))==g['terminal_outcome']
            assert all(item['historical_comparison'].values())
            model=graph.RecoveredPair(g['checkpoint']).eval().models[g['role']]
            for saved in e['files'][::2]:
                assert sha(saved['path'])==saved['sha256'];d=torch.load(saved['path'],map_location='cpu',weights_only=False)
                logits,value=model(d['obs']);logits=logits.reshape(-1);prob=torch.softmax(logits,-1)
                ml=max(ml,float((logits-d['logits']).abs().max()));mv=max(mv,float((value-d['value']).abs().max()));mp=max(mp,float((prob-d['probabilities']).abs().max()))
                for actual,expected in ((logits,d['logits']),(value,d['value']),(prob,d['probabilities'])):assert torch.allclose(actual,expected,atol=1e-6,rtol=0)
                assert int(d['active_action_ids'][int(logits.argmax())])==d['action'];count+=1
            records.append(dict(name=item['name'],normal_terminal=True,raw_decisions=e['decisions'],trajectory_sha256=digest,checkpoint_sha256=sha(g['checkpoint'])))
    assert all(sha(q)==h for q,h in frozen.items()) and not torch.cuda.is_initialized()
    out=dict(passed=True,scope='Technical regression on four repeated historical games; no independent strength estimate.',games=4,decisions=count,raw_chain_complete=True,full_CPU_NN_replay=True,maximum_logit_error=ml,maximum_value_error=mv,maximum_probability_error=mp,absolute_tolerance=1e-6,records=records,new_native_games=0,GPU_operations=0,optimizer_steps=0,final_test_touched=False,seconds=time.monotonic()-start,script_sha256=sha(__file__))
    (a.out/'AUDIT.json').write_text(json.dumps(out,indent=2));print(json.dumps(out),flush=True)
if __name__=='__main__':main()
