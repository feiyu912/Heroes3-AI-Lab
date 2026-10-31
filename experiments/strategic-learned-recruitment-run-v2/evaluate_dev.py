"""Eight fresh same-schema6 four-arm DEV cells, CPU argmax; no optimization."""
import argparse,importlib.util,json,subprocess,sys
from pathlib import Path
from pipeline_common import BASE,HERE,LAB,DEFAULT_CAPSULE,INITIAL_SHA,CONTROL_POLICY,CONTROL_INITIAL,CONTROL_UPDATED,CONTROL_SHA,source_inputs,capsule_inputs,sha
def write(p,value):p.write_text(json.dumps(value,indent=2)+'\n')
def main():
    p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path,required=True);p.add_argument('--candidate',type=Path,required=True)
    p.add_argument('--minus-four-initial',type=Path,default=CONTROL_INITIAL);p.add_argument('--minus-four-updated',type=Path,default=CONTROL_UPDATED)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--capsule',type=Path,default=DEFAULT_CAPSULE);p.add_argument('--execute',action='store_true');a=p.parse_args()
    # Both models must encode the same actual vocabulary and runtime action space.
    sys.path.insert(0,str(BASE))
    from model_io import load_model,INITIAL_FORMAT
    _,baseline,bsha=load_model(a.baseline);_,candidate,csha=load_model(a.candidate)
    assert bsha==INITIAL_SHA,'Only registered zero-prior baseline may enter this pilot'
    assert baseline['format']==INITIAL_FORMAT and candidate.get('training_updates')==1 and candidate['complete_update_boundary']
    assert all(sha(path)==h for path,h in candidate['protocol']['sources'].items()),'Training source epoch changed before independent evaluation'
    assert candidate['parent_checkpoint_sha256']==bsha and baseline['catalog_sha256']==candidate['catalog_sha256']
    assert baseline['lineage']['parent_checkpoint_sha256']=='83319be8bde5d94eea839b1a889821449a7c1492c65da7ca6cde2deb63aab25a'
    assert sha(a.minus_four_initial)==CONTROL_SHA['minus4_initial'] and sha(a.minus_four_updated)==CONTROL_SHA['minus4_updated']
    spec=importlib.util.spec_from_file_location('_frozen_minus_four_evaluation_codec',CONTROL_POLICY/'model_io.py')
    oldio=importlib.util.module_from_spec(spec);spec.loader.exec_module(oldio)
    _,old_initial,_=oldio.load_model(a.minus_four_initial);_,old_updated,_=oldio.load_model(a.minus_four_updated)
    assert old_updated['parent_checkpoint_sha256']==CONTROL_SHA['minus4_initial'] and old_updated['training_updates']==1
    assert all(sha(path)==h for path,h in old_updated['protocol']['sources'].items()),'Old learned control source changed'
    assert old_initial['catalog_sha256']==old_updated['catalog_sha256']==baseline['catalog_sha256']
    expected_native={k:candidate['protocol'][k] for k in ('capsule_manifest_sha256','native_artifacts')}
    assert all(old_updated['protocol'][k]==v for k,v in expected_native.items()),'Four arms need exactly the same native runtime'
    jobs=[dict(map=m,opponent=o,player=p,seed=2026104200+i) for i,(m,o,p) in enumerate((m,o,p) for m in ('takeover-v2-dev-01-river','takeover-v2-dev-02-reserves') for o in ('EmptyAI','Nullkiller2') for p in (0,1))]
    models={'minus4_initial':a.minus_four_initial.resolve(),'minus4_updated':a.minus_four_updated.resolve(),'zero_initial':a.baseline.resolve(),'zero_updated':a.candidate.resolve()}
    paths=source_inputs()+capsule_inputs(a.capsule)+list(models.values())+[LAB/('data/vcmi/Maps/adv/'+j['map']+'.vmap') for j in jobs]
    frozen={str(p):sha(p) for p in paths};a.out.mkdir(parents=True,exist_ok=False)
    write(a.out/'PLAN.json',dict(epoch='recruitment-prior-zero-four-arm-paired-DEV-v1',jobs=jobs,model_sha256={arm:sha(path) for arm,path in models.items()},input_sha256=frozen,
        sampling='CPU argmax',training_samples=0,optimizer_steps=0,finaltest_touched=False,execute=a.execute,
        limitation='Eight historically seen DEV map/role/opponent cells; initial public request equality is not hidden-world determinism. No DEV teacher labels.'))
    if not a.execute:print(json.dumps(dict(plan_only=True,paired_cells=8,games=32,optimizer_steps=0)));return 0
    pairs=[]
    try:
        for i,job in enumerate(jobs):
            pair=dict(index=i,job=job,arms={})
            for arm,checkpoint in models.items():
                assert all(sha(path)==h for path,h in frozen.items())
                root=a.out/f'pair-{i:02d}'/arm;root.mkdir(parents=True)
                commands=[[str(LAB/'gpu-venv/bin/python'),str(HERE/'collect_cpu.py'),'--capsule',str(a.capsule),'--checkpoint',str(checkpoint),'--out',str(root/'native'),
                    '--map',job['map'],'--player',str(job['player']),'--opponent',job['opponent'],'--seed',str(job['seed']),
                    '--policy-epoch','minus-four-control' if arm.startswith('minus4_') else 'prior-zero'],
                    [str(LAB/'venv/bin/python'),str(HERE/'audit_game_v6.py'),str(root/'native'),str(root/'raw-audit')]]
                for stage,command in enumerate(commands):
                    result=subprocess.run(command,capture_output=True,text=True);(root/f'command-{stage}.log').write_text(result.stdout+'\nSTDERR:\n'+result.stderr)
                    assert result.returncode==0,'Invalid DEV arm; unscored '+str(root)
                audit=json.loads((root/'raw-audit/AUDIT.json').read_text())
                assert audit['whole_game_valid'] and audit['native_game_completed'] and audit['transport_drained']
                proposals=[json.loads(x) for x in (root/'native/agent/typed-broker.jsonl').read_text().splitlines()]
                pair['arms'][arm]=dict(win=audit['winner']==('red' if job['player']==0 else 'blue'),audit_sha256=sha(root/'raw-audit/AUDIT.json'),
                    initial_request_sha256=sha(root/'native/agent/request-00000001.json'),counts=audit['counts'],
                    recruitment_days=[p['request']['day'] for p in proposals if p['response']['op']=='recruit'],
                    recruited_amount=sum(p['request']['candidates'][p['response']['selected_index']]['amount'] for p in proposals if p['response']['op']=='recruit'))
            pair['initial_request_equal_all_four']=len({data['initial_request_sha256'] for data in pair['arms'].values()})==1
            pairs.append(pair);write(a.out/'PROGRESS.json',dict(pairs=pairs))
        wins={arm:sum(x['arms'][arm]['win'] for x in pairs) for arm in models}
        result=dict(passed=True,pairs=pairs,arm_wins=wins,zero_prior_update_net_wins=wins['zero_updated']-wins['zero_initial'],minus4_update_net_wins=wins['minus4_updated']-wins['minus4_initial'],
            initial_prior_net_wins=wins['zero_initial']-wins['minus4_initial'],updated_prior_net_wins=wins['zero_updated']-wins['minus4_updated'],
            training_samples=0,optimizer_steps=0,finaltest_touched=False,ability_improvement_claim=False)
    except BaseException as error:result=dict(passed=False,error=repr(error),completed_pairs=pairs,training_samples=0,optimizer_steps=0)
    write(a.out/'RESULT.json',result);print(json.dumps({k:v for k,v in result.items() if k not in ('pairs','completed_pairs')},indent=2))
    return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
