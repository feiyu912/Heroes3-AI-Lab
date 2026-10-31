"""CPU-only exact coverage/config/path/fragment-accounting preflight."""
import ast,collections,copy,json,sys,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;R=HERE.parent.parent/'research';sys.path[:0]=[str(R),str(HERE)]
import curriculum
import run
def rejects(f):
    try:f()
    except (AssertionError,ValueError):return True
    raise AssertionError('Bad fixture accepted')
def main():
    for p in HERE.glob('*.py'):ast.parse(p.read_text(encoding='utf-8-sig'))
    reg=curriculum.registered(run.SCENARIOS);assert reg==curriculum.registered(run.SCENARIOS)
    assert len(reg['families'])==6 and all(x['scenario_index']<192 for x in reg['families'])
    cells=[];phases=[]
    for phase in range(2):
        configs=curriculum.configs(run.SCENARIOS,curriculum.SEED,phase,'cpu-fixture-no-native')
        assert len(configs)==12
        count=collections.Counter((c['opponent'],c['role']) for c in configs);assert len(count)==4 and set(count.values())=={3}
        assert all(Path(c['worker_root']).is_relative_to(run.LAB/'workers') for c in configs)
        cells +=[(c['family'],c['role'],c['opponent']) for c in configs]
        e=curriculum.close_evidence(phase,[0,1,2]+[0]*9,configs,'CPU_FAKE_BOUNDARY_NOT_NATIVE');assert len(e['unfinished_fragments'])==2 and e['zero_step_post_reset_or_unacted_battles']==10
        assert e['terminated'] is e['truncated'] is e['reward_assigned'] is False
        phases.append(dict(phase=phase,counts={str(k):v for k,v in count.items()},fake_fragment_accounting=e))
    expected={(f,r,o) for f in range(6) for r in ('attacker','defender') for o in ('BattleAI','MMAI_MODEL')};assert len(cells)==24 and set(cells)==expected
    negatives={'wrong_seed':rejects(lambda:curriculum.registered(run.SCENARIOS,0)),'wrong_fragment_shape':rejects(lambda:curriculum.close_evidence(0,[],[],'fake'))}
    with tempfile.TemporaryDirectory(prefix='family-cpu-fixture-') as t:
        cases=json.loads(run.SCENARIOS.read_text());fixture=Path(t)/'SCENARIOS.json'
        for case in cases:
            if case['split']=='train':case['armies'][1]=[];break
        fixture.write_text(json.dumps(cases));negatives['nonmirror_TRAIN_rejected']=rejects(lambda:curriculum.registered(fixture))
        fixture.write_text(json.dumps([c for c in cases if c['split']!='train']));negatives['DEV_only_rejected']=rejects(lambda:curriculum.registered(fixture))
    trainer=(HERE/'train_last_graph.py').read_text();assert 'live_steps[worker]+=1' in trainer and "if s['terminated'] or s['truncated']:live_steps[worker]=0" in trainer and "'phase_switch'" in trainer and "'final_budget_stop'" in trainer
    result=dict(passed=True,native_games=0,GPU_operations=0,optimizer_steps=0,registered_curriculum=reg,unique_cells=24,phases=phases,negative_cases=negatives,
        source_sha256={str(p):run.sha(p) for p in HERE.glob('*.py')},scope='CPU exact registration/syntax/path/fixture fragment checks; no actual phase close or native training yet')
    run.write(HERE/'CPU_PREFLIGHT.json',result);print(json.dumps({k:v for k,v in result.items() if k not in ('source_sha256','registered_curriculum','phases')},indent=2))
if __name__=='__main__':main()
