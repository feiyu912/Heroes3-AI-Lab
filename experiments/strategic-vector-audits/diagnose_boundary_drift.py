#!/usr/bin/env python3
"""Read-only attribution of completed CPU vector-boundary divergence."""
import argparse
from collections import Counter,defaultdict
import hashlib
import json
from pathlib import Path
import sys

import torch

VECTOR=Path(__file__).resolve().parent.parent/'strategic-vector-v1'
sys.path.insert(0,str(VECTOR))
from collect_vector import env_seed,state_tensor_sha


def lines(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def batches(root,update):
    rows,details={},{}
    for wave in sorted(root.glob(f'update-{update:03d}-wave-*')):
        number=int(wave.name.rsplit('-',1)[1])
        for row in lines(wave/'accepted-rollout.jsonl'):
            rows[(number,row['episode_index'],row['request']['request_id'])]=row
        counters=Counter()
        for index,batch in enumerate(lines(wave/'inference-batches.jsonl')):
            for env in batch['env_indices']:
                counters[env]+=1
                details[(number,env,counters[env])]=dict(batch_index=index,batch_size=batch['batch_size'],
                    candidate_counts=batch['candidate_counts'],env_indices=batch['env_indices'])
    return rows,details


def compare_samples(left,right,update):
    a,ab=batches(left,update);b,bb=batches(right,update)
    assert a.keys()==b.keys()
    differences=Counter();examples=[];maximum=defaultdict(float)
    for key in sorted(a):
        changed=[]
        for field in ('request','action','old_logprob','old_value','generator_seed','episode_id','policy_version',
                      'policy_tensor_sha256','checkpoint_sha256','return'):
            if a[key][field]!=b[key][field]:
                differences[field]+=1;changed.append(field)
                if field in ('old_logprob','old_value'):
                    maximum[field]=max(maximum[field],abs(a[key][field]-b[key][field]))
        if changed and len(examples)<8:
            examples.append(dict(wave=key[0],env=key[1],request_id=key[2],changed_fields=changed,
                left={field:a[key][field] for field in changed if field not in ('request',)},
                right={field:b[key][field] for field in changed if field not in ('request',)},
                left_inference_batch=ab[key],right_inference_batch=bb[key]))
    return dict(samples=len(a),field_difference_counts=dict(differences),max_abs_difference=dict(maximum),
        inference_context_differences=sum(ab[key]!=bb[key] for key in a),first_difference_examples=examples)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',required=True,type=Path)
    parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    root=args.root
    comparison1=compare_samples(root/'trainer-cpu-continuous-02',root/'trainer-cpu-split-02',1)
    comparison2=compare_samples(root/'trainer-cpu-continuous-02',root/'trainer-cpu-resume-02',2)
    bundles={name:torch.load(root/name/'update-1.pt',map_location='cpu',weights_only=True)
             for name in ('trainer-cpu-continuous-02','trainer-cpu-split-02')}
    tensor_hashes={name:state_tensor_sha(bundle['state_dict']) for name,bundle in bundles.items()}
    job=json.loads((root/'trainer-cpu-continuous-02/update-002-wave-00/plan.json').read_text())['jobs'][0]
    seeds={name:env_seed(job,f'update-1:sha256:{value}'+':'+value) for name,value in tensor_hashes.items()}
    first_rows={name:lines(root/name/'update-002-wave-00/accepted-rollout.jsonl')[0]
                for name in ('trainer-cpu-continuous-02','trainer-cpu-resume-02')}
    assert seeds['trainer-cpu-continuous-02']==first_rows['trainer-cpu-continuous-02']['generator_seed']
    assert seeds['trainer-cpu-split-02']==first_rows['trainer-cpu-resume-02']['generator_seed']
    assert not torch.cuda.is_initialized()
    report=dict(readonly=True,game_started=False,optimizer_steps=0,CUDA_initialized=False,
        update1_continuous_vs_independent_split=comparison1,update2_continuous_vs_split_resumed=comparison2,
        update1_resulting_policy_tensor_hashes=tensor_hashes,update2_recomputed_first_job_generator_seeds=seeds,
        confirmed='First-update archival data differ slightly before the split checkpoint exists; different resulting tensor SHA changes all subsequent job RNG seeds. '
        'This confounds fresh repeated collection with serialization recovery. Exact same archived batches are needed to isolate save/restore.',
        inference_attribution='Different dynamic microbatch contexts are observed. Corresponding CPU batch-shape numerical differences explain value/logp drift; '
        'a tiny tensor change then causes a cryptographic RNG seed change, not merely a small numeric perturbation.',
        audit_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (args.out/'AUDIT.json').write_text(json.dumps(report,indent=2))
    (args.out/Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    print(json.dumps({key:report[key] for key in ('update1_continuous_vs_independent_split',
        'update2_continuous_vs_split_resumed','update1_resulting_policy_tensor_hashes',
        'update2_recomputed_first_job_generator_seeds')},indent=2))


if __name__=='__main__':
    main()
