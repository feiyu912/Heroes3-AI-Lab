"""CPU read-only analysis of the actual archived TRAIN behavior policy."""
import collections,hashlib,json,math,statistics,sys
from pathlib import Path
import torch
HERE=Path(__file__).resolve().parent;TRAIN=HERE.parent/'strategic-typed-training-v1'
sys.path.insert(0,str(TRAIN))
from load_admitted import load
from model_io import load_model
from episode_balanced_ppo import collate
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    torch.set_num_threads(1)
    ledger_path=TRAIN/'balanced-ack-certified-01/RESULT.json';ledger=json.loads(ledger_path.read_text());assert ledger['passed']
    checkpoint=TRAIN/'cuda-update-engineering-01/update-1.pt';model,bundle,digest=load_model(checkpoint,'cpu')
    source=[Path(__file__),ledger_path,checkpoint,TRAIN/'model_io.py',TRAIN/'load_admitted.py',TRAIN/'episode_balanced_ppo.py',HERE.parent/'strategic-policy-v3/model.py',HERE.parent/'strategic-policy-v3/encoder.py']
    episodes=[];stop_values=[];logp_errors=[];counts=collections.Counter();multi_entropy=[];top=[];next_entropy=[]
    with torch.no_grad():
        for entry in ledger['episodes']:
            admission=Path(entry['admission']);assert sha(admission/'AUDIT.json')==entry['admission_sha256'];source.append(admission/'AUDIT.json')
            rows,manifest,_=load(admission);assert len(manifest)==1 and manifest[0]['checkpoint_sha256']==digest
            assert manifest[0]['job']['map'] in ('takeover-v2-train-01-mines','takeover-v2-train-02-development')
            local=collections.Counter();local_stop=[];local_entropy=[]
            for sample in rows:
                assert sample['policy_sha256']==digest
                request=sample['request'];logits,_=model(**collate([request],'cpu'));logits=logits[0].double();logp=logits.log_softmax(0);p=logp.exp()
                action=sample['action'];logp_errors.append(abs(float(logp[action])-sample['old_logprob']))
                moves=[i for i,c in enumerate(request['candidates']) if c['op']=='move'];stops=[i for i,c in enumerate(request['candidates']) if c['op']=='end_turn'];assert len(stops)==1
                q=float(p[stops[0]]);stop_values.append(q);local_stop.append(q);top.append(float(p.max()));local['rows']+=1
                local['one_move_plus_stop' if len(moves)==1 else 'multiple_moves_plus_stop']+=1
                local['sampled_stop']+=request['candidates'][action]['op']=='end_turn'
                local['sampled_non_argmax']+=action!=int(logits.argmax())
                steps={tuple(request['candidates'][i]['next']) for i in moves};local['one_distinct_move_next']+=len(steps)==1
                if len(moves)>1:
                    m=logits[moves].softmax(0);h=float(-(m*logits[moves].log_softmax(0)).sum());multi_entropy.append(h);local_entropy.append(h)
                    local['multiple_candidates_but_one_next']+=len(steps)==1
                    aggregated=collections.defaultdict(float)
                    for i,prob in zip(moves,m):aggregated[tuple(request['candidates'][i]['next'])]+=float(prob)
                    next_entropy.append(-sum(x*math.log(x) for x in aggregated.values()))
            counts.update(local);episodes.append(dict(cell=entry['cell'],reward=entry['reward'],counts=dict(local),mean_stop_probability=statistics.mean(local_stop),
                                                     median_move_conditional_entropy=statistics.median(local_entropy) if local_entropy else None))
    assert counts['rows']==2588 and max(logp_errors)<1e-4
    result=dict(passed=True,scope='Actual archived behavior checkpoint on its certified TRAIN samples; CPU probability replay, not CUDA generator replay or new on-policy collection.',
                behavior_checkpoint_sha256=digest,prior_scale=float(model.prior_scale),stop_bias=float(model.actor.stop_bias),counts=dict(counts),episodes=episodes,
                sampled_logprob_max_absolute_CPU_error=max(logp_errors),mean_stop_probability=statistics.mean(stop_values),median_stop_probability=statistics.median(stop_values),
                episode_balanced_mean_stop_probability=statistics.mean(e['mean_stop_probability'] for e in episodes),
                median_top_probability=statistics.median(top),median_multiple_move_conditional_entropy=statistics.median(multi_entropy),
                median_multi_candidate_next_coordinate_entropy=statistics.median(next_entropy),
                input_sha256={str(p):sha(p) for p in source},new_native_games=0,GPU_operations=0,optimizer_steps=0,training_samples_admitted=0,DEV_labels_used=0,
                limitation='CPU floating-point logprob check is tolerance-based, not exact original CUDA sampling replay. Distinct immediate next coordinates do not measure long-term destination diversity or action quality.')
    out=HERE/'independent-behavior-probability-01';out.mkdir(exist_ok=False);(out/'AUDIT.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k not in ['episodes','input_sha256']},indent=2))
if __name__=='__main__':main()
