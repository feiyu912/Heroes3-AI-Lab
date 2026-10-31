"""Cross-check aggregate labels against re-audited native winners, not reported totals."""
import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;LAB=Path('/root/heroes3-ai-lab/evaluations')
def read(path):return json.loads(Path(path).read_text())
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def main():
    report=read(HERE/'REPORT.json');original=read(LAB/'strategic-learned-build-dev-01/RESULT.json')
    cells=set();train_wins=0;dev_wins={'a':0,'b':0};dev_builds=0
    for case in report['cases']:
        path=Path(case['case']);plan=read(path/'native/PLAN.json')
        audited=read(HERE/'raw-reaudit'/f"{case['phase']}-{case['identity']}"/'AUDIT.json')
        win=audited['winner']==('red' if plan['owned_player']==0 else 'blue')
        if case['phase']=='train':
            cells.add((plan['map'],plan['owned_player'],plan['opponent']))
            assert plan['seed']==2026102600+int(case['identity'])
            assert case['model_sha256']=='0dbbc4735e217e39a55dcd2f398b945bcb9ea6490525c86645843a5f1ac313f6'
            episode=read(path/'admitted/episode.json');assert episode['reward']==(1. if win else -1.)
            train_wins+=win
        else:
            index,arm=case['identity'].split('-');pair=original['pairs'][int(index)]
            assert pair['pair']==int(index) and plan['seed']==2026102700+int(index)
            assert all(plan[k]==pair['job'][target] for k,target in [('map','map'),('owned_player','player'),('opponent','opponent'),('seed','seed')])
            assert win is pair['arms'][arm]['win']
            assert case['counts']==pair['arms'][arm]['counts'] and case['raw_audit_sha256']==pair['arms'][arm]['audit_sha256']
            dev_wins[arm]+=win;dev_builds+=case['counts']['policy_builds']
    expected={(m,p,o) for m in ('takeover-v2-train-01-mines','takeover-v2-train-02-development') for p in (0,1) for o in ('EmptyAI','Nullkiller2')}
    assert cells==expected and train_wins==4 and dev_wins==report['dev_wins']=={'a':4,'b':4} and dev_builds==0
    inputs=read(HERE/'INPUTS.json');assert all(sha(path)==value for path,value in inputs.items())
    result=dict(passed=True,train_coverage_exact=True,train_actual_native_wins=train_wins,train_actual_native_losses=8-train_wins,
        dev_actual_native_wins=dev_wins,all_root_result_labels_match_native_reaudits=True,all_24_inputs_remain_unchanged=True,
        report_sha256=sha(HERE/'REPORT.json'),build_transactions_sha256=sha(HERE/'BUILD_TRANSACTIONS.json'),native_runs=0,gpu_runs=0)
    (HERE/'AGGREGATE_AUDIT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
