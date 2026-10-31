"""CPU-only integration guards; synthetic metadata is never native/admission evidence."""
import ast,copy,importlib,inspect,json,py_compile,sys
from pathlib import Path
from pipeline_common import *
def main():
    checks=[]
    def reject(name,fn):
        try:fn()
        except (AssertionError,ValueError,KeyError):checks.append({'case':name,'rejected':True});return
        raise AssertionError('negative accepted: '+name)
    for p in HERE.glob('*.py'):py_compile.compile(str(p),doraise=True)
    from run_pipeline import jobs
    planned=jobs(2026102000)
    cells=[{'episode_id':'synthetic-'+str(i),'checkpoint_sha256':INITIAL_SHA,'job':dict(map=j['map'],owned_player=j['player'],opponent=j['opponent'],logical_update=0)} for i,j in enumerate(planned)]
    validate_cells(cells);assert [j['seed'] for j in planned]==list(range(2026102000,2026102008))
    checks.append({'case':'eight_full_training_cells_seed_order','passed':True})
    reject('seven_cells',lambda:validate_cells(cells[:-1]));reject('nine_cells',lambda:validate_cells(cells+[cells[0]]))
    mutated=copy.deepcopy(cells);mutated[1]['job']=copy.deepcopy(mutated[0]['job']);reject('duplicate_coverage_cell',lambda:validate_cells(mutated))
    mutated=copy.deepcopy(cells);mutated[-1]['checkpoint_sha256']='other-policy';reject('mixed_parent_policy',lambda:validate_cells(mutated))
    mutated=copy.deepcopy(cells);mutated[-1]['job']['logical_update']=1;reject('mixed_logical_update',lambda:validate_cells(mutated))
    mutated=copy.deepcopy(cells);mutated[-1]['job']['map']='takeover-v2-test-01';reject('nontraining_map',lambda:validate_cells(mutated))
    native=dict(audit_metadata(),input_audit_epoch=AUDIT_EPOCH,read_only_legacy_reaudit=False,compiled_native_epoch_proven=True,event_contract_valid=True,
                whole_game_valid=True,native_game_completed=True,transport_drained=True,candidate_manifest_sha256=sha(AUDITOR/'CANDIDATE_MANIFEST.json'),
                auditor_sha256={name:sha(path) for name,path in AUDITOR_SOURCES.items()})
    plan=audit_metadata();execution=audit_metadata();validate_native_epoch(native,plan,execution)
    for field,value in [('transport_drained',False),('compiled_native_epoch_proven',False),('event_contract_valid',False),
                        ('whole_game_valid',False),('native_game_completed',False),('input_audit_epoch',None),
                        ('read_only_legacy_reaudit',True),('audit_epoch','old-epoch'),('candidate_manifest_sha256','changed')]:
        altered=copy.deepcopy(native);altered[field]=value;reject('native_metadata_'+field,lambda n=altered:validate_native_epoch(n,plan,execution))
    altered=copy.deepcopy(native);altered['auditor_sha256']['audit_game_v5.py']=altered['auditor_sha256'].pop('audit_game_v6.py')
    reject('old_auditor_source_key',lambda:validate_native_epoch(altered,plan,execution))
    altered=copy.deepcopy(native);altered['auditor_sha256']['director_registry_v1.py']='changed'
    reject('changed_actual_auditor_helper',lambda:validate_native_epoch(altered,plan,execution))
    for target in ('plan','execution'):
        altered=audit_metadata();altered['termination_registry_semantics']='non-atomic'
        reject('wrong_'+target+'_native_epoch',lambda a=altered,t=target:validate_native_epoch(native,a if t=='plan' else plan,a if t=='execution' else execution))
    base=(BASE/'admit_episode_v5.py').read_text();new=(HERE/'admit_episode_v5.py').read_text()
    start='    with owned_resources():\n';end="    assert all(sha(Path(path))==h for path,h in plan['hashes'].items())\n    manifest="
    # Whole exact CUDA replay block, including action/logprob/value and both RNG endpoints.
    original_replay=base.split(start,1)[1].split(end,1)[0];current_replay=new.split(start,1)[1].split(end,1)[0]
    assert original_replay==current_replay;checks.append({'case':'entire_original_cuda_replay_block_byte_identical','passed':True})
    assert "reward=1. if native['winner']==own_colour else -1." in new
    train=(HERE/'train_update_v3.py').read_text();assert "ppo_update(model,optimizer,samples,'cuda',progress,episodes=episodes)" in train
    assert "from episode_balanced_ppo import PROTOCOL,ppo_update,optimizer_steps" in train
    checks.append({'case':'original_terminal_reward_and_ppo_call_unchanged','passed':True})
    sys.path.insert(0,str(BASE))
    broker=importlib.import_module('onpolicy_broker_v2');assert Path(broker.__file__).resolve()==(BASE/'onpolicy_broker_v2.py').resolve()
    checks.append({'case':'sampler_reuses_frozen_original_onpolicy_broker_v2','passed':True})
    att=validate_capsule(DEFAULT_CAPSULE);assert sha(DEFAULT_INITIAL)==INITIAL_SHA
    paths=set(source_inputs());assert set(AUDITOR_SOURCES.values())<=paths
    assert AUDITOR/'CANDIDATE_MANIFEST.json' in paths
    caps=set(capsule_inputs(DEFAULT_CAPSULE));assert all(DEFAULT_CAPSULE/r in caps for r in att['candidate_artifacts'])
    checks.append({'case':'actual_capsule03_all_artifacts_nine_payload_and_initial_sha_read_only_verified','passed':True})
    report={'passed':True,'checks':checks,'source_sha256':{str(p):sha(p) for p in [HERE/'collect_episode_v5.py',HERE/'admit_episode_v5.py',HERE/'train_update_v3.py',HERE/'run_pipeline.py',HERE/'pipeline_common.py']},
            'native_runs':0,'cuda_inference':False,'optimizer_steps':0,'scope':'CPU syntax, unchanged replay/PPO source checks and synthetic rejection guards; not native/CUDA training certification'}
    (HERE/'CPU_REPORT.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'passed':True,'checks':len(checks),'native_runs':0,'optimizer_steps':0}))
if __name__=='__main__':main()
