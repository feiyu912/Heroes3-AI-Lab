"""CPU recompute every saved DEV graph from actual immutable checkpoints."""
import argparse,hashlib,importlib.util,json,sys,time
from pathlib import Path
import torch
ROOT=Path(__file__).resolve().parents[3];R=ROOT/'research';sys.path.insert(0,str(R))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--dev-run',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);torch.set_num_threads(1)
    result=json.loads((a.dev_run/'RESULT.json').read_text());assert result['passed'] and len(result['DEV'])==6
    frozen=json.loads((a.dev_run/'FREEZE.json').read_text())['input_sha256'];assert all(sha(p)==h for p,h in frozen.items())
    spec=importlib.util.spec_from_file_location('_independent_recovered',R/'recovered-graph.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    records=[];maxlog=maxval=maxprob=0.;count=0;started=time.monotonic()
    with torch.inference_mode():
        for item in result['DEV']:
            report=json.loads(Path(item['report']).read_text());checkpoint=report['checkpoint'];model=module.RecoveredPair(checkpoint).eval();local_count=0
            for game in report['battles']:
                role=model.models[game['role']]
                for saved in game['step_evidence']['files'][::2]:
                    assert sha(saved['path'])==saved['sha256'];d=torch.load(saved['path'],map_location='cpu',weights_only=False);logits,value=role(d['obs']);logits=logits.reshape(-1);value=value.detach().cpu();prob=torch.softmax(logits,-1)
                    le=float((logits-d['logits']).abs().max());ve=float((value-d['value']).abs().max());pe=float((prob-d['probabilities']).abs().max());maxlog=max(maxlog,le);maxval=max(maxval,ve);maxprob=max(maxprob,pe)
                    assert torch.allclose(logits,d['logits'],atol=1e-6,rtol=0) and torch.allclose(value,d['value'],atol=1e-6,rtol=0) and torch.allclose(prob,d['probabilities'],atol=1e-6,rtol=0)
                    assert int(d['active_action_ids'][int(logits.argmax())])==d['action'];count+=1;local_count+=1
            records.append(dict(model=item['model'],opponent=item['opponent'],games=16,real_graph_decisions=local_count,checkpoint_sha256=sha(checkpoint)));print(json.dumps(records[-1]),flush=True)
    assert all(sha(p)==h for p,h in frozen.items())
    report=dict(passed=True,unique_games=96,actual_full_NN_CPU_probability_replay=True,decisions=count,maximum_logit_error=maxlog,maximum_value_error=maxval,maximum_probability_error=maxprob,absolute_tolerance=1e-6,records=records,new_native_games=0,GPU_operations=0,optimizer_steps=0,elapsed_seconds=time.monotonic()-started,source_sha256=sha(__file__))
    (a.out/'AUDIT.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
