"""Same archived common-prefix states, actual CPU/CUDA numerical check; no updates."""
import argparse,json,os,sys
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG',':4096:8')
from pathlib import Path
from pipeline_common import BASE,DEFAULT_INITIAL,INITIAL_SHA,sha
sys.path.insert(0,str(BASE))
import torch
from model_io import load_model
import encoder
from collect_cpu import owned_resources
def main():
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();assert not a.out.exists()
    entries=json.loads((a.run/'PROGRESS.json').read_text())['entries'];rows=[]
    with owned_resources():
        torch.set_num_threads(1);torch.use_deterministic_algorithms(True);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
        cpu,_,csha=load_model(DEFAULT_INITIAL,'cpu');gpu,_,gsha=load_model(DEFAULT_INITIAL,'cuda');assert csha==gsha==INITIAL_SHA
        for e in entries:
            root=Path(e['job']['stochastic_native']);old=[json.loads(x) for x in (root/'agent/typed-broker.jsonl').read_text().splitlines()]
            stop=min(len(old),e['equal_public_request_action_prefix']+1)
            for i,s in enumerate(old[:stop],1):
                with torch.no_grad():
                    lc,vc=cpu(**encoder.collate([s['request']],'cpu'));lg,vg=gpu(**encoder.collate([s['request']],'cuda'))
                    lg=lg.cpu();vg=vg.cpu();pc=lc[0].log_softmax(-1);pg=lg[0].log_softmax(-1)
                # These requests have only legal offered candidates; no padded -inf.
                assert torch.allclose(lc,lg,atol=2e-5,rtol=1e-5) and torch.allclose(vc,vg,atol=2e-5,rtol=1e-5)
                assert float(pg[s['action']])==s['old_logprob'] and float(vg[0])==s['old_value']
                same=int(lc[0].argmax())==int(lg[0].argmax())
                rows.append(dict(cell=e['job']['index'],step=i,legal_candidates=len(s['request']['candidates']),max_logit_abs_difference=float((lc-lg).abs().max()),value_abs_difference=float((vc-vg).abs().max()),CPU_CUDA_argmax_equal=same,stochastic_selected_action=s['action'],argmax_action=int(lc[0].argmax()),selected_logprob_CPU=float(pc[s['action']]),selected_logprob_CUDA=float(pg[s['action']]),CPU_argmax_probability=float(pc.exp().max()),request_sha256=s['request_sha256']))
        assert sha(DEFAULT_INITIAL)==INITIAL_SHA
    report=dict(passed=True,states_checked=len(rows),rows=rows,atol=2e-5,rtol=1e-5,CUDA_archived_selected_logprob_and_value_exact=True,all_CPU_CUDA_argmax_equal=all(r['CPU_CUDA_argmax_equal'] for r in rows),optimizer_steps=0,native_games=0,scope='Actual shared observations through first policy-sequence difference, not hidden-state equivalence or all future states')
    a.out.write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='rows'}))
if __name__=='__main__':main()
