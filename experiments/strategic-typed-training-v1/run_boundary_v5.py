"""Prespecified complete native two-update engineering recovery comparison."""
import hashlib,json,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent;LAB=Path('/root/heroes3-ai-lab')
OUT=LAB/'evaluations/typed-native-cuda-boundary-v5-01'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
OUT.mkdir(exist_ok=False)
names=['run_boundary_v5.py','native_boundary_v5.py','train_update_v3.py','collect_episode_v5.py','admit_episode_v5.py','live_jsonl.py',
       'model_io.py','onpolicy_broker_v2.py','load_admitted.py','episode_balanced_ppo.py']
frozen={str(HERE/n):sha(HERE/n) for n in names}
(OUT/'PLAN.json').write_text(json.dumps(dict(purpose='Engineering continuous2 versus split1/resume2, fresh real native episodes in every arm',
    parent_sha256=sha(HERE/'cuda-curriculum-ack-01/update-1.pt'),source_sha256=frozen,
    native_games_planned=4,opponent='EmptyAI',initial_optimizer_reset=True,
    one_gpu_learner=True,child_inference_serialized_under_leases=True,
    endpoints=['exact model','exact Adam','exact CPU/CUDA/Python RNG','exact per-episode sampling states','exact requests/responses and gameplay traces'],
    finaltest_touched=False,ability_improvement_claim=False),indent=2))
for name,args in [('continuous',['--initialize',HERE/'cuda-curriculum-ack-01/update-1.pt','--through-update','2']),
                  ('split-one',['--initialize',HERE/'cuda-curriculum-ack-01/update-1.pt','--through-update','1']),
                  ('resumed',['--resume',OUT/'split-one/update-1.pt','--through-update','2'])]:
    assert all(sha(Path(p))==h for p,h in frozen.items())
    cmd=[str(LAB/'gpu-venv/bin/python'),str(HERE/'native_boundary_v5.py')]+list(map(str,args))+['--out',str(OUT/name)]
    with (OUT/(name+'.log')).open('w') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
    assert r.returncode==0,'Arm failed; preserve evidence and do not retry silently: '+name
    print(json.dumps({'completed_arm':name}),flush=True)
import torch
def differences(a,b,path=''):
    if isinstance(a,torch.Tensor):return [] if isinstance(b,torch.Tensor) and a.dtype==b.dtype and a.shape==b.shape and torch.equal(a,b) else [path]
    if type(a)!=type(b):return [path+':type']
    if isinstance(a,dict):
        if a.keys()!=b.keys():return [path+':keys']
        return [x for k in a for x in differences(a[k],b[k],path+'/'+str(k))]
    if isinstance(a,(list,tuple)):
        if len(a)!=len(b):return [path+':length']
        return [x for i,(x,y) in enumerate(zip(a,b)) for x in differences(x,y,path+'/'+str(i))]
    return [] if a==b else [path]
checkpoints=[];traces=[]
for update,other in [(1,'split-one'),(2,'resumed')]:
    paths=[OUT/'continuous'/f'update-{update}.pt',OUT/other/f'update-{update}.pt']
    a,b=[torch.load(p,map_location='cpu',weights_only=True) for p in paths]
    diff=differences(a,b)
    checkpoints.append(dict(update=update,full_bundle_exact=not diff,differences=diff[:30],sha256=[sha(p) for p in paths],
        optimizer_steps_total=[x['optimizer_steps_total'] for x in (a,b)]))
    roots=[OUT/'continuous'/f'update-{update:02d}/native',OUT/other/f'update-{update:02d}/native']
    names=['strategy-decisions.jsonl','strategy-trace.jsonl','strategy-trace.jsonl.targets.jsonl','agent/typed-broker.jsonl']
    names+=sorted(str(p.relative_to(roots[0])) for pattern in ('request-*.json','response-*.json') for p in (roots[0]/'agent').glob(pattern))
    checks={name:sha(roots[0]/name)==sha(roots[1]/name) for name in names}
    traces.append(dict(update=update,files_compared=len(checks),all_exact=all(checks.values()),different_files=[n for n,v in checks.items() if not v]))
report=dict(passed=all(x['full_bundle_exact'] for x in checkpoints) and all(x['all_exact'] for x in traces),checkpoints=checkpoints,traces=traces,
    native_games=4,independent_ability_samples=0,ability_improvement_claim=False,
    limitation='Engineering two-update recovery on deterministic EmptyAI training cells. Does not prove NK/native full-world determinism, midturn/battle recovery, multihero control or strategic improvement.')
(OUT/'COMPARISON.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
raise SystemExit(0 if report['passed'] else 1)
