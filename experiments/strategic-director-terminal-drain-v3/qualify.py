"""Fresh native regression for the terminal hang; no training or outcome rescue."""
import argparse,hashlib,json,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
REPLAN=HERE.parent/'strategic-threat-replan-v2'
LAB=Path('/root/heroes3-ai-lab')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    capsule=LAB/'evaluations/typed-director-terminal-drain-capsule-03'
    model=HERE.parent/'strategic-typed-training-v1/cuda-curriculum-ack-01/update-1.pt'
    assert json.loads((capsule/'EXECUTION.json').read_text())['passed']
    sources=[Path(__file__),HERE/'PLAN.md',HERE/'CANDIDATE_MANIFEST.json',HERE/'run_proxy_game_director_drain.py',HERE/'audit_game_v6.py',HERE/'director_registry_v1.py',HERE/'audit_replan_v3.py',REPLAN/'audit_proxy.py',REPLAN/'clearance_broker.py',REPLAN/'clearance_proxy.py',model,capsule/'EXECUTION.json',capsule/'build-source-manifest.json']
    frozen={str(p):sha(p) for p in sources}
    (a.out/'PLAN.json').write_text(json.dumps(dict(input_sha256=frozen,terminal_ack_scope='director',termination_registry_semantics='atomic-termination-closed-registry-v3',engineering_only=True,optimizer_steps=0,training_samples=0,expert_labels=0,old_failed_game_not_rescored=True),indent=2))
    jobs=[('hang-repro',2026111003,1,'Nullkiller2','clearance'),('empty-red-control',2026111000,0,'EmptyAI','model'),('empty-blue-control',2026111001,1,'EmptyAI','model')]
    results=[]
    try:
        for name,seed,player,opponent,policy in jobs:
            root=a.out/name;root.mkdir()
            commands=[['/usr/bin/python3',HERE/'run_proxy_game_director_drain.py','--capsule',capsule,'--checkpoint',model,'--map','takeover-v2-train-01-mines','--seed',seed,'--player',player,'--opponent',opponent,'--decision-policy',policy,'--threat-replan','once','--out',root/'native'],
                [LAB/'venv/bin/python',HERE/'audit_game_v6.py',root/'native',root/'raw-audit'],
                [LAB/'venv/bin/python',HERE/'audit_replan_v3.py',root/'native',root/'raw-audit/AUDIT.json',root/'replan-audit'],
                [LAB/'venv/bin/python',REPLAN/'audit_proxy.py',root/'native',root/'replan-audit/AUDIT.json',root/'proxy-audit']]
            for i,cmd in enumerate(commands):
                assert all(sha(Path(p))==h for p,h in frozen.items())
                r=subprocess.run(list(map(str,cmd)),capture_output=True,text=True)
                (root/f'command-{i}.log').write_text(r.stdout+'\nSTDERR:\n'+r.stderr)
                assert r.returncode==0,f'{name} command {i} invalid; no scoring/admission'
            proof=json.loads((root/'raw-audit/AUDIT.json').read_text())
            assert proof['whole_game_valid'] and proof['native_game_completed'] and proof['transport_drained']
            results.append(dict(name=name,counts=proof['counts'],winner=proof['winner'],registry=proof['director_registry_proof']))
        result=dict(passed=True,games=results,engineering_only=True,ability_improvement_claim=False,optimizer_steps=0,training_samples=0,expert_labels=0)
    except BaseException as error:result=dict(passed=False,error=repr(error),completed=results,optimizer_steps=0,training_samples=0)
    (a.out/'RESULT.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
    return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
