"""CPU source/model/split preflight; never imports native environment or steps Adam."""
import ast,collections,json,sys
from pathlib import Path
import numpy as np
import torch
HERE=Path(__file__).resolve().parent;R=HERE.parent.parent/'research';sys.path[:0]=[str(R),str(HERE)]
import full_graph_policy as graph
import support
from run import B64,inputs,training,write
def main():
    torch.set_num_threads(1)
    for p in HERE.glob('*.py'):ast.parse(p.read_text(encoding='utf-8-sig'))
    model=graph.FullGraphPair(str(B64),'last').cpu().eval();trainable=[n for n,p in model.named_parameters() if p.requires_grad]
    assert any('gnn__convs__2__' in n for n in trainable) and any('policy_head__' in n for n in trainable)
    assert all('policy_head__' in n or 'value_head__' in n or 'gnn__convs__2__' in n or 'gnn__norms__2__' in n for n in trainable)
    assert support.sha(B64)==support.B64
    cases=[c for c in json.loads((R/'diverse-curriculum.json').read_text()) if c['split']=='train'];rng=np.random.default_rng(2026102008);schedule=[]
    order=rng.permutation(8)
    for slot in range(8):
        i=int(order[slot]);case=cases[int(rng.integers(len(cases)))];role='attacker' if i%2==0 else 'defender';opponent=['BattleAI','MMAI_MODEL'][(i//2)%2]
        schedule.append(dict(slot=slot,role=role,opponent=opponent,scenario_id=case['id'],map=case['map'],seed=2026102008+slot,split=case['split']))
    counts=collections.Counter((s['opponent'],s['role']) for s in schedule);assert set(counts.values())=={2} and len(counts)==4
    src=(HERE/'train_last_graph.py').read_text();assert 'fixed_opponent=None' in src and "counter['steps']>step_before" in src and 'partial_live_state_not_resumable=True' in src
    assert "__import__('random').seed(args.seed);np.random.seed(args.seed)" in src
    frozen=inputs()
    result=dict(passed=True,CPU_model_loaded_from_B64=True,total_parameters=sum(p.numel() for p in model.parameters()),trainable_parameters=sum(p.numel() for p in model.parameters() if p.requires_grad),
        trainable_tensors=len(trainable),schedule=schedule,balanced_cell_counts={str(k):v for k,v in counts.items()},native_games=0,GPU_operations=0,optimizer_steps=0,
        frozen_inputs=frozen,source_scope='Syntax, actual B64 CPU model and deterministic schedule only; no native/CUDA rollout or saved learner readback yet')
    write(HERE/'CPU_PREFLIGHT.json',result);print(json.dumps({k:v for k,v in result.items() if k!='frozen_inputs'},indent=2))
if __name__=='__main__':main()
