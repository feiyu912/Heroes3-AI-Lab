"""Independent aggregate/income/native-calendar label check; no live continuation reads."""
import collections,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;RUN=HERE.parent;POLICY=RUN.parent/'strategic-learned-build-exploration-policy-v1'
LAB=Path('/root/heroes3-ai-lab/evaluations');TRAIN=LAB/'strategic-learned-build-exploration-train-01';DEV=LAB/'strategic-learned-build-exploration-dev-01'
INITIAL='40eccc511fbc61b84b86e75b5aec102781835f2574db809f9a698f9a81db6d97';TRAINED='d27d282bbcdaf1f1bf47f13b4b44c40ee1cd82639bedd47db90da5fd6c0da1d2'
def read(path):return json.loads(Path(path).read_text())
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def main():
    report=read(HERE/'REPORT.json');transactions=read(HERE/'BUILD_TRANSACTIONS.json');original=read(DEV/'RESULT.json')
    cells=set();totals=collections.defaultdict(collections.Counter);pairs=[];income=[];per_case={}
    for case in report['cases']:
        path=Path(case['case']);plan=read(path/'native/PLAN.json');audit=read(HERE/'raw-reaudit'/f"{case['phase']}-{case['identity']}"/'AUDIT.json')
        win=audit['winner']==('red' if plan['owned_player']==0 else 'blue');arm='train' if case['phase']=='train' else case['identity'][-1]
        c=totals[arm];c['games']+=1;c['wins']+=win;c['losses']+=not win;c['builds']+=case['counts']['policy_builds'];c['policy_end_turns']+=case['counts']['policy_end_turns']
        per_case[case['case']]=dict(case=case,win=win,arm=arm,income=0)
        if arm=='train':
            cells.add((plan['map'],plan['owned_player'],plan['opponent']));assert plan['seed']==2026102800+int(case['identity']) and case['model_sha256']==INITIAL
            assert read(path/'admitted/episode.json')['reward']==(1. if win else -1.)
        else:
            index=int(case['identity'][:2]);pair=original['pairs'][index]
            assert plan['seed']==2026102900+index and win is pair['arms'][arm]['win']
            assert all(plan[k]==pair['job'][v] for k,v in [('map','map'),('owned_player','player'),('opponent','opponent'),('seed','seed')])
            assert case['counts']==pair['arms'][arm]['counts'] and case['raw_audit_sha256']==pair['arms'][arm]['audit_sha256']
    for row in transactions:
        path=Path(row['case']);info=per_case[row['case']];request=read(path/f"native/agent/request-{row['decision_id']:08d}.json")
        candidate=next(c for c in request['candidates'] if c['op']=='build' and c['town_id']==row['town_id'] and c['building_id']==row['building_id'])
        assert candidate['cost']==row['cost']
        if candidate['category']=='income':
            assert row['building_id'] in (11,12,13)
            info['income']+=1;totals[info['arm']]['income']+=1
            income.append(dict(**row,phase=info['case']['phase'],arm=info['arm'],request_day=request['day'],own_turn=request['own_turn']))
    for index,pair in enumerate(original['pairs']):
        arms={}
        for arm in ('a','b'):
            info=per_case[str(DEV/f'pair-{index:02d}'/arm)];case=info['case']
            arms[arm]=dict(win=info['win'],builds=case['counts']['policy_builds'],income=info['income'],calendar=case['calendar'],policy_moves=case['counts']['policy_moves'])
        pairs.append(dict(pair=index,job=pair['job'],arms=arms,win_delta=int(arms['b']['win'])-int(arms['a']['win'])))
    expected={(m,p,o) for m in ('takeover-v2-train-01-mines','takeover-v2-train-02-development') for p in (0,1) for o in ('EmptyAI','Nullkiller2')}
    assert cells==expected and totals['train']['builds']==28 and totals['train']['income']==1
    assert totals['a']['wins']==totals['b']['wins']==4 and sum(totals[a]['builds'] for a in ('a','b'))==134
    restoration=POLICY/'recovery-audit-01/native-cuda-01/AUDIT.json';cert=read(restoration)
    assert cert['passed_exact'] and cert['checkpoint_sha256']==TRAINED and cert['optimizer_steps_restored']==120
    assert cert['build_bias_and_Adam_moment_exact'] and len(cert['negative_cases'])==6 and cert['build_bias']==report['actual_cpu_build_bias'][TRAINED]
    calibration=RUN.parent/'strategic-learned-build-exploration-v1/calibration-01/AUDIT.json';cal=read(calibration)
    assert cal['passed'] and cal['gradient_updates']==0 and cal['chosen_checkpoint_sha256']==INITIAL and cal['chosen_bias']==1.5
    for mapping in ('source_sha256','input_sha256'):
        assert all(sha(Path(path) if Path(path).is_absolute() else calibration.parent.parent/path)==h for path,h in cal[mapping].items())
    frozen=read(HERE/'INPUTS.json');assert all(sha(path)==h for path,h in frozen.items())
    result=dict(passed=True,totals={key:dict(value) for key,value in totals.items()},pairs=pairs,income_transactions=income,
        all_result_labels_match_reaudited_native_winners=True,all_frozen_input_hashes_unchanged=True,
        calibration_certificate_only=dict(path=str(calibration),sha256=sha(calibration),gradient_updates=0,initial_build_bias=1.5),
        gpu_restore_certificate_only=dict(path=str(restoration),sha256=sha(restoration),steps=120,invalid_cases=6),
        source_protocol_scope='First-update frozen protocol only; no claim that separately frozen continuation controller is contained in it. No live logical-update1..3 directory read.',
        report_sha256=sha(HERE/'REPORT.json'),build_transactions_sha256=sha(HERE/'BUILD_TRANSACTIONS.json'),new_native_runs=0,new_gpu_runs=0,new_optimizer_steps=0)
    (HERE/'AGGREGATE_AUDIT.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(passed=True,totals=result['totals'],income=[dict(phase=x['phase'],arm=x['arm'],building_id=x['building_id'],day=x['request_day'],cost=x['cost']) for x in income],pairs=pairs),indent=2))
if __name__=='__main__':main()
