"""CPU registration/schedule/serialization-metadata preflight; no native/GPU/Adam."""
import ast,collections,json,math,shutil,sys,tempfile
from pathlib import Path
import torch
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import curriculum,run,support
def rejects(f):
    try:f()
    except (AssertionError,ValueError):return True
    raise AssertionError('Invalid fixture accepted')
def main():
    torch.set_num_threads(1)
    for p in HERE.glob('*.py'):ast.parse(p.read_text(encoding='utf-8-sig'))
    reg=curriculum.registered(run.SCENARIOS);assert reg==curriculum.registered(run.SCENARIOS) and len(reg['phases'])==15
    selected=[c for f in reg['families'] for c in f['selected']];assert len(selected)==len({c['scenario_index'] for c in selected})==60
    assert all(c['scenario_index']<192 for c in selected) and all(len(f['selected'])==10 for f in reg['families'])
    cells=[];seeds=[];phase_stats=[]
    for phase in range(15):
        configs=curriculum.configs(run.SCENARIOS,curriculum.SEED,phase,'CPU_FIXTURE_NOT_NATIVE');assert len(configs)==16
        groups=collections.Counter((c['role'],c['opponent']) for c in configs);assert len(groups)==4 and set(groups.values())=={4}
        assert len({c['TRAIN_scenario_index'] for c in configs})==4
        for c in configs:
            cells.append((c['TRAIN_scenario_index'],c['role'],c['opponent']));seeds.append(c['seed']);assert Path(c['worker_root']).is_relative_to(run.LAB/'workers')
        e=curriculum.close_evidence(phase,[0,1,63,0]+[0]*12,configs,'CPU_FAKE_BOUNDARY_NOT_NATIVE');assert len(e['unfinished_fragments'])==2 and e['zero_step_post_reset_or_unacted_battles']==14
        assert e['terminated'] is e['truncated'] is e['reward_assigned'] is False
        phase_stats.append(dict(phase=phase,cases=sorted({c['TRAIN_scenario_index'] for c in configs}),groups={str(k):v for k,v in groups.items()}))
    assert len(cells)==len(set(cells))==240 and len(set(seeds))==240
    count=collections.Counter((c['family'],c['role'],c['opponent']) for p in reg['phases'] for c in p);assert len(count)==24 and set(count.values())=={10}
    # Metadata helper fixture: no actual model weights or optimization touched.
    fixture=torch.nn.Module();fixture.attacker=torch.nn.Module();fixture.defender=torch.nn.Module()
    for role in ('attacker','defender'):
        obj=getattr(fixture,role)
        for n in ('policy_head__w','value_head__w','gnn__convs__2__w'):obj.register_parameter(n,torch.nn.Parameter(torch.zeros(2)))
        obj.register_parameter('frozen_w',torch.nn.Parameter(torch.zeros(2),requires_grad=False))
    before=support.snapshot(fixture)
    with torch.no_grad():
        for p in fixture.parameters():
            if p.requires_grad:p.add_(.125)
    delta=support.delta(fixture,before);assert delta['changed_tensors']==6 and delta['unchanged_frozen_tensors']==2
    assert all(delta['parameter_groups'][g]['changed_tensors']==2 for g in ('actor_heads','critic_heads','last_graph'))
    negatives=dict(wrong_seed=rejects(lambda:curriculum.registered(run.SCENARIOS,0)),invalid_phase=rejects(lambda:curriculum.configs(run.SCENARIOS,curriculum.SEED,15,'fake')),wrong_close_shape=rejects(lambda:curriculum.close_evidence(0,[],[],'fake')))
    with tempfile.TemporaryDirectory(prefix='diverse60-cpu-fixture-') as temp:
        p=Path(temp)/'SCENARIOS.json';cases=json.loads(run.SCENARIOS.read_text())
        p.write_text(json.dumps([c for c in cases if c['split']!='train']));negatives['DEV_only_rejected']=rejects(lambda:curriculum.registered(p))
        cases[0]['armies'][1]=[];p.write_text(json.dumps(cases));negatives['nonmirror_TRAIN_rejected']=rejects(lambda:curriculum.registered(p))
    trainer=(HERE/'train_last_graph.py').read_text();assert 'rollout_evidence=support.save_rollout' in trainer and 'phase_resource_events.append' in trainer and 'args.workers' in trainer
    assert (run.training(Path('/CPU_PLAN_NOT_EXECUTED'))[run.training(Path('/CPU_PLAN_NOT_EXECUTED')).index('--updates')+1])=='30'
    result=dict(passed=True,native_games=0,GPU_operations=0,optimizer_steps=0,TRAIN_unique_maps=60,case_role_opponent_unique_slots=240,phases=15,workers=16,updates=30,owned_transition_budget=15360,
        registered_curriculum=reg,phase_stats=phase_stats,negative_cases=negatives,synthetic_delta_group_metadata_passed=True,disk_free_GiB=shutil.disk_usage('/root/heroes3-ai-lab').free/1024**3,
        source_sha256={str(p):run.sha(p) for p in HERE.glob('*.py')},scope='CPU registration/syntax/path/fake fragment and delta-metadata checks; no actual native or CUDA rollout')
    run.write(HERE/'CPU_PREFLIGHT.json',result);print(json.dumps({k:v for k,v in result.items() if k not in ('registered_curriculum','phase_stats','source_sha256')},indent=2))
if __name__=='__main__':main()
