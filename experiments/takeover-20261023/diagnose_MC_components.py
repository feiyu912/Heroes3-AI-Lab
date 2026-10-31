"""Inference-only head/body crossings on equal first-difference public graphs."""
import argparse,hashlib,importlib.util,json,sys
from pathlib import Path
import torch
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent.parent;sys.path[:0]=[str(ROOT/'research'),'/root/heroes3-ai-lab/src/gym']
from observation_digest import update
RUN=Path('/root/heroes3-ai-lab/evaluations/battle-observed-MC-DEV-01')
PARENT=Path('/root/heroes3-ai-lab/evaluations/battle-terminal-credit-01/candidate-micro/update-61.pt')
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def gh(o):h=hashlib.sha256();update(h,o);return h.hexdigest()
def weights(p):return torch.load(p,map_location='cpu',weights_only=True)['models']
def state(head,body):
    return {'models.'+role+'.weights.'+key.replace('.','__'):(head if 'policy_head' in key else body)[role]['weights'][key] for role in ('attacker','defender') for key in head[role]['weights']}
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);torch.set_num_threads(1)
    result=read(RUN/'RESULT.json');assert result['passed'] and result['full_CPU_replay']
    raw=read(RUN/'DEV-RAW-AUDIT.json');plan=read(RUN/'PLAN.json')
    paths=dict(parent61=PARENT,reference62=Path(plan['models']['control']['path']),MC62=Path(plan['models']['candidate']['path']))
    bank={name:weights(path) for name,path in paths.items()}
    spec=importlib.util.spec_from_file_location('_inference_component_model',ROOT/'research/recovered-graph.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    model=module.RecoveredPair(paths['MC62']).eval()
    variants=dict(reference_full=('reference62','reference62'),MC_full=('MC62','MC62'),MC_head_reference_body=('MC62','reference62'),MC_head_parent61_body=('MC62','parent61'),reference_head_MC_body=('reference62','MC62'))
    reports={(r['model'],r['opponent']):read(r['report']) for r in result['DEV']};cases=[]
    for pair in raw['DEV']['control_vs_candidate_pairs']:
        if not pair['win_delta']:continue
        first=pair['first_public_graph_or_action_difference'];assert first and first['control']['public_graph_sha256']==first['candidate']['public_graph_sha256']
        decisions={}
        for name in ('control','candidate'):
            game=next(g for g in reports[(name,pair['opponent'])]['battles'] if g['role']==pair['role'] and int(g['scenario'].split('-')[-1])==pair['scenario'])
            item=game['step_evidence']['files'][2*(first['step']-1)];assert sha(item['path'])==item['sha256'];decisions[name]=torch.load(item['path'],map_location='cpu',weights_only=False)
        obs=decisions['control']['obs'];identity=gh(obs);assert identity==gh(decisions['candidate']['obs'])==first['control']['public_graph_sha256']
        ids=obs['active_action_ids'];out={}
        for name,(head,body) in variants.items():
            model.load_state_dict(state(bank[head],bank[body]),strict=True)
            with torch.inference_mode():logits,value=model.models[pair['role']](obs)
            logits=logits.reshape(-1);probs=logits.softmax(-1);rank=logits.argsort(descending=True)
            action=int(ids[int(rank[0])]);top=[dict(action=int(ids[int(i)]),logit=float(logits[int(i)]),probability=float(probs[int(i)])) for i in rank[:3]]
            out[name]=dict(action=action,top3=top,top2_margin=float(logits[int(rank[0])]-logits[int(rank[1])]) if len(rank)>1 else None)
            if name in ('reference_full','MC_full'):
                original=decisions['control' if name=='reference_full' else 'candidate']
                assert torch.allclose(logits,original['logits'],atol=1e-6,rtol=0) and action==original['action']
            assert gh(obs)==identity
        cases.append(dict(opponent=pair['opponent'],scenario=pair['scenario'],role=pair['role'],seed=pair['seed'],win_delta=pair['win_delta'],step=first['step'],public_graph_sha256=identity,variants=out))
    assert not torch.cuda.is_initialized()
    report=dict(passed=True,checkpoint_sha256={name:sha(path) for name,path in paths.items()},cases=cases,inference_only=True,new_checkpoint_files=0,new_native_games=0,optimizer_steps=0,GPU_operations=0,PPO_teacher_rows=0,scope='Component effects on action rankings for a fixed public graph only. These hybrids are not resumable models or demonstrated battle outcomes; DEV graphs are never PPO data.')
    (a.out/'AUDIT.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if __name__=='__main__':main()
