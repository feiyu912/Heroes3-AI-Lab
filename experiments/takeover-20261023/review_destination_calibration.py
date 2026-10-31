"""Independent native audit plus CPU probability-space reconstruction of all samples."""
import argparse,collections,hashlib,json,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;PACKAGE=HERE.parent/'strategic-destination-sampling-calibration-20261024'
sys.path.insert(0,str(PACKAGE))
from pipeline_common import BASE,DEFAULT_INITIAL,INITIAL_SHA,sha
from model_io import load_model,tensor_sha
import encoder,torch
def read(p):return json.loads(Path(p).read_text())
def main():
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    result=read(a.run/'RESULT.json');assert result['passed'] and result['all_four_valid'] and len(result['entries'])==4
    frozen=read(PACKAGE/'SOURCE_FREEZE.json')['files'];assert all(sha(p)==h for p,h in frozen.items())
    torch.set_num_threads(1);model,_,digest=load_model(DEFAULT_INITIAL,'cpu');assert digest==INITIAL_SHA;before=tensor_sha(model.state_dict())
    rows=[];total=0;max_error=0.;max_mass_error=0.;counts=collections.Counter();rawhashes={}
    for entry in result['entries']:
        index=entry['job']['index'];root=a.run/f'cell-{index:02d}';target=a.out/f'raw-{index:02d}'
        with (a.out/f'raw-{index:02d}.log').open('w') as log:
            c=subprocess.run(['/root/heroes3-ai-lab/venv/bin/python',str(PACKAGE/'audit_game_v6.py'),str(root/'native'),str(target)],stdout=log,stderr=subprocess.STDOUT)
        assert c.returncode==0
        audit=read(target/'AUDIT.json');assert audit==read(root/'raw-audit/AUDIT.json')
        replay=read(root/'sampler-replay/AUDIT.json');assert replay['passed'] and replay['replay_actions_logprobs_values_rng_exact'] and replay['samples_admitted']==0
        assert sha(root/'raw-audit/AUDIT.json')==entry['audit_sha256'] and sha(root/'sampler-replay/AUDIT.json')==entry['replay_sha256']
        proposals=[json.loads(x) for x in (root/'native/agent/typed-broker.jsonl').read_text().splitlines()]
        assert len(proposals)==audit['actual_decisions_checked']==replay['decisions_replayed']==entry['decisions']
        for i,old in enumerate(proposals,1):
            raw=(root/f'native/agent/request-{i:08d}.json').read_bytes();q=json.loads(raw);assert q==old['request'] and hashlib.sha256(raw).hexdigest()==old['request_sha256']
            with torch.no_grad():logits,value=model(**encoder.collate([q],'cpu'))
            legal=logits[0];logp=legal.log_softmax(-1);mask=torch.tensor([c['op']=='move' for c in q['candidates']]);m=int(mask.sum())
            # Independently construct conditional probabilities, rather than
            # invoking the producer's logit transformation helper.
            expected=logp.clone()
            if m>1:expected[mask]=(legal[mask]/.25).log_softmax(-1)+torch.logsumexp(logp[mask],0)
            archived_logits=torch.tensor(old['raw_logits']);archived_probs=torch.tensor(old['effective_probabilities'])
            assert torch.allclose(legal,archived_logits,atol=2e-5,rtol=1e-5)
            assert torch.allclose(expected.exp(),archived_probs,atol=2e-6,rtol=2e-5)
            selected=old['action'];error=abs(float(expected[selected])-old['old_logprob']);max_error=max(max_error,error)
            assert error<=2e-5+1e-5*abs(old['old_logprob']) and abs(float(value[0])-old['old_value'])<=2e-5+1e-5*abs(old['old_value'])
            assert old['manual_setting_is_learning'] is False and old['new_PPO_admissions']==0 and old['move_temperature']==.25
            assert all(old['raw_logits'][j]==old['effective_logits'][j] for j,c in enumerate(q['candidates']) if c['op']!='move')
            if m<=1:assert old['raw_logits']==old['effective_logits'] and old['raw_probabilities']==old['effective_probabilities']
            for op,prob in old['raw_operation_probabilities'].items():
                fresh=old['effective_operation_probabilities'][op];delta=abs(prob-fresh);max_mass_error=max(max_mass_error,delta);assert delta<=3e-7+3e-6*abs(prob)
            counts['zero_move' if m==0 else 'single_move' if m==1 else 'multiple_moves']+=1
        rows.append(dict(cell=index,win=entry['victory'],decisions=len(proposals),complete_GPU_sampler_replay=True,independent_CPU_distribution_reconstructed=True))
        total+=len(proposals);rawhashes.update({str(root/'native'/p):h for p,h in audit['raw_sha256'].items()})
    assert tensor_sha(model.state_dict())==before and all(sha(p)==h for p,h in frozen.items()) and all(sha(p)==h for p,h in rawhashes.items())
    wins=sum(r['win'] for r in rows);assert wins==result['wins']
    report=dict(passed=True,complete_raw_audits_rerun=4,complete_CPU_distributions_reconstructed=total,wins=wins,rows=rows,move_candidate_cases=dict(counts),max_CPU_archived_selected_logprob_error=max_error,max_archived_operation_mass_error=max_mass_error,qualifies_fixed_training_success_criterion=wins>=2,model_unchanged=True,new_native_games=0,GPU_operations=0,optimizer_steps=0,PPO_samples_admitted=0,expert_labels=0,model_promoted=False,final_test_touched=False,raw_sha256=rawhashes)
    (a.out/'AUDIT.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k not in ('rows','raw_sha256')},indent=2))
if __name__=='__main__':main()
