"""CPU-only parser requalification of four completed, immutable capsule03 games."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent
LAB=Path('/root/heroes3-ai-lab')
REPLAN=HERE.parent/'strategic-threat-replan-v2'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    q=LAB/'evaluations/typed-director-terminal-drain-qualification-01'
    old=LAB/'evaluations/typed-clearance-proxy-paired-03'
    previous=json.loads((q/'RESULT.json').read_text());assert previous['passed'] and len(previous['games'])==3
    failed=json.loads((old/'RESULT.json').read_text());assert not failed['passed']
    cases=[(g['name'],q/g['name']/'native') for g in previous['games']]+[('previously-parser-rejected-pair02-a',old/'pair-02/a/native')]
    frozen={str(path):sha(path) for path in [q/'RESULT.json',q/'PLAN.json',old/'RESULT.json',old/'PLAN.json']}
    a.out.mkdir(parents=True,exist_ok=False);games=[]
    for name,root in cases:
        out=a.out/name;out.mkdir()
        before={str(path):sha(path) for path in root.rglob('*') if path.is_file()}
        commands=[['/usr/bin/python3',HERE/'audit_game_v6.py',root,out/'raw-audit'],
                  ['/usr/bin/python3',HERE/'audit_replan_v3.py',root,out/'raw-audit/AUDIT.json',out/'replan-audit'],
                  [LAB/'venv/bin/python',REPLAN/'audit_proxy.py',root,out/'replan-audit/AUDIT.json',out/'proxy-audit']]
        for i,command in enumerate(commands):
            r=subprocess.run(list(map(str,command)),capture_output=True,text=True,timeout=120)
            (out/f'command-{i}.log').write_text(r.stdout+'\nSTDERR:\n'+r.stderr)
            assert r.returncode==0,(name,i,r.stderr)
        proof=json.loads((out/'raw-audit/AUDIT.json').read_text());assert proof['whole_game_valid']
        assert proof['audit_epoch']=='director-neutral-makeaction-ack-v4' and proof['read_only_legacy_reaudit'] is True
        assert all(sha(Path(path))==h for path,h in before.items())
        games.append(dict(name=name,root=str(root),passed=True,winner=proof['winner'],counts=proof['counts'],
                          registered_count=proof['director_registry_proof']['registered_count'],
                          neutral_makeaction_acks=proof['director_registry_proof']['verified_neutral_makeaction_acks'],
                          actual_atomic_cleared_ids=proof['director_registry_proof']['actual_atomic_cleared_ids'],
                          all_raw_files_unchanged=True,input_sha256=before,
                          output_sha256={str(out/n/'AUDIT.json'):sha(out/n/'AUDIT.json') for n in ['raw-audit','replan-audit','proxy-audit']}))
    assert all(sha(Path(path))==h for path,h in frozen.items())
    sources=[p for p in HERE.glob('*.py')]+[HERE/'PLAN.md',HERE/'CANDIDATE_MANIFEST.json']+list((HERE/'candidate').rglob('*'))
    result=dict(passed=True,schema='director-neutral-ack-readonly-four-raw-qualification-v4',audit_epoch='director-neutral-makeaction-ack-v4',
                native_epoch='atomic-termination-closed-registry-v3',capsule=str(LAB/'evaluations/typed-director-terminal-drain-capsule-03'),
                new_native_games=0,GPU_operations=0,optimizer_steps=0,training_samples=0,engineering_only=True,
                old_paired03_remains_failed_unscored=True,ability_improvement_claim=False,games=games,
                original_batch_input_sha256=frozen,source_sha256={str(p):sha(p) for p in sources if p.is_file()},
                limitation='Independent read-only audit epoch; does not rewrite old PLAN/RESULT, create new native games, or rescore the failed paired batch.')
    (a.out/'AUDIT.json').write_text(json.dumps(result,indent=2));(a.out/'RESULT.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(dict(passed=True,new_native_games=0,games=[dict(name=g['name'],registered_count=g['registered_count'],neutral_ack_count=len(g['neutral_makeaction_acks'])) for g in games]),indent=2))

if __name__=='__main__':main()
