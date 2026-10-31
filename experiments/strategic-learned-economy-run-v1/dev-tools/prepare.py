"""Minimal isolated CPU-argmax DEV adapters; never rewrite frozen root inputs."""
import difflib,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;RUN=HERE.parent
EXPERIMENTS=RUN.parent;PARENT_EVAL=EXPERIMENTS/'strategic-learning-mainline-20261020/evaluate_dev.py'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def change(text,old,new):
    assert text.count(old)==1,(old,text.count(old));return text.replace(old,new,1)
def emit(name,original,text):
    (HERE/name).write_text(text)
    (HERE/(name+'.diff')).write_text(''.join(difflib.unified_diff(original.splitlines(True),text.splitlines(True),fromfile='frozen-parent/'+name,tofile='build-dev/'+name)))
def main():
    original=(RUN/'collect_episode_v5.py').read_text();text=original
    text=change(text,'LOCAL=Path(__file__).resolve().parent','DEV_TOOLS=Path(__file__).resolve().parent\nLOCAL=DEV_TOOLS.parent\nsys.path.insert(0,str(LOCAL))')
    text=change(text,'One on-policy CUDA sampled native episode. No optimizer; admission is separate.','One CPU-argmax native DEV episode. No sampling/admission/training or optimizer.')
    text=change(text,"BROKER=HERE/'onpolicy_broker_v2.py'","BROKER=HERE/'broker.py'")
    text=change(text,'clean_environment();assert args.load_save is None,"New training cells start from the Training map"',
        'clean_environment();assert args.load_save is None,"DEV starts from the fixed native map"\n    assert args.map in ("takeover-v2-dev-01-river","takeover-v2-dev-02-reserves"),"Only the two registered DEV maps"')
    text=change(text,'inputs.extend(source_inputs()+capsule_inputs(capsule))',
        "inputs.extend(source_inputs()+capsule_inputs(capsule))\n    inputs.extend(sorted(DEV_TOOLS.glob('*.py'))+[DEV_TOOLS/'PLAN.md',LOCAL/'collect_episode_v5.py'])")
    text=change(text,"sampling='onpolicy CUDA multinomial'","sampling='CPU argmax'")
    text=change(text,"[str(LAB/'gpu-venv/bin/python'),str(BROKER),'--agent-dir',str(work/'agent'),'--checkpoint',str(checkpoint),\n                '--sampling-seed',str(sampling_seed),'--gpu-lock-fd',str(lease_fds[0]),'--pool-lock-fd',str(lease_fds[1]),",
        "[str(LAB/'venv/bin/python'),str(BROKER),'--mode','new-policy','--agent-dir',str(work/'agent'),'--checkpoint',str(checkpoint),")
    text=change(text,"ready['mode']=='onpolicy_cuda' and ready['device']=='cuda'","ready['mode']=='new-policy' and ready['device']=='cpu'")
    text=change(text,"choices=['takeover-v2-train-01-mines','takeover-v2-train-02-development'],default='takeover-v2-train-01-mines'",
        "choices=['takeover-v2-dev-01-river','takeover-v2-dev-02-reserves'],default='takeover-v2-dev-01-river'")
    emit('collect_cpu.py',original,text)
    original=PARENT_EVAL.read_text();text=original
    text=change(text,'HERE=Path(__file__).resolve().parent;EXPERIMENTS=HERE.parent;LAB=Path(\'/root/heroes3-ai-lab\')',
        "HERE=Path(__file__).resolve().parent;RUN=HERE.parent;EXPERIMENTS=RUN.parent;LAB=Path('/root/heroes3-ai-lab')\nsys.path.insert(0,str(RUN))\nfrom pipeline_common import source_inputs,capsule_inputs,validate_capsule\nINITIAL_SHA='0dbbc4735e217e39a55dcd2f398b945bcb9ea6490525c86645843a5f1ac313f6'\nTRAINED_SHA='34a6a86ea74d727338388db74e0ab3b9e16ec85e45ef46313757b1ac814538bc'")
    text=change(text,"DRAIN=EXPERIMENTS/'strategic-director-terminal-drain-v4'","DRAIN=RUN")
    text=change(text,'sys.path.insert(0,str(DRAIN))\n    from run_proxy_game_director_drain import run','sys.path.insert(0,str(HERE))\n    from collect_cpu import run')
    text=change(text,"p.add_argument('--out',type=Path,required=True)\n    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)",
        "p.add_argument('--out',type=Path,required=True);p.add_argument('--execute',action='store_true')\n    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)")
    text=change(text,"capsule=LAB/'evaluations/typed-director-terminal-drain-capsule-03'","capsule=LAB/'evaluations/strategic-learned-economy-build-capsule-01'\n    validate_capsule(capsule)\n    assert sha(a.baseline)==INITIAL_SHA and sha(a.candidate)==TRAINED_SHA,'Exact registered same-window models required'")
    text=change(text,'seed=2026102100+len(jobs)','seed=2026102700+len(jobs)')
    start=text.index('    sources=[Path(__file__),HERE/\'PLAN.md\'')
    end=text.index('    frozen={str(x):sha(x) for x in sources}',start)
    text=text[:start]+"    sources=source_inputs()+capsule_inputs(capsule)+sorted(HERE.glob('*.py'))+[HERE/'PLAN.md']+list(models.values())\n    sources +=[LAB/('data/vcmi/Maps/adv/'+j['map']+'.vmap') for j in jobs]\n"+text[end:]
    text=change(text,"native_runtime=str(capsule),threat_replan='off'","native_runtime=str(capsule),execute=a.execute,evaluation_epoch='learned-build-same-window-cpu-dev-v1',threat_replan='off'")
    text=change(text,'    pairs=[]\n    try:',"    if not a.execute:\n        print(json.dumps(dict(plan_only=True,games=16,pairs=8,native_runs=0,optimizer_steps=0)));return 0\n    pairs=[]\n    try:")
    text=change(text,"'policy_end_turns':sum(x['response']['op']=='end_turn' for x in proposals)","'policy_end_turns':sum(x['response']['op']=='end_turn' for x in proposals),\n                    'policy_builds':sum(x['response']['op']=='build' for x in proposals)")
    emit('evaluate_dev.py',original,text)
    (HERE/'PARENT_SOURCES.json').write_text(json.dumps({str(p):sha(p) for p in [RUN/'collect_episode_v5.py',PARENT_EVAL]},indent=2)+'\n')
if __name__=='__main__':main()
