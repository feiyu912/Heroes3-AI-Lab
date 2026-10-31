"""Independent post-resource-stop completed-boundary review; never relabel run pass."""
from pathlib import Path
import json,sys,torch,numpy as np
torch.set_num_threads(1)
HERE=Path(__file__).resolve().parent
PACKAGE=HERE.parent/'battle-terminal-credit-native-20261023';sys.path.insert(0,str(PACKAGE))
import audit,restore_learner as restore,targets
root=Path('/root/heroes3-ai-lab/evaluations/battle-terminal-credit-01')
stage=root/'control-phase-1';folder=stage/'phase-1'
out=HERE/'terminal-credit-recovery-review-01';out.mkdir(exist_ok=False)
failed=json.loads((root/'RESULT.json').read_text());assert failed['passed'] is False
result=json.loads((stage/'RESULT.json').read_text());assert result['passed'] is False and result['actual_Adam_steps']==8192
assert 'post_update_resource' in (root/'control-phase-1.log').read_text()
workers=json.loads((folder/'WORKERS.json').read_text())
registered=json.loads((PACKAGE/'REGISTERED_CURRICULUM.json').read_text())['phases'][1]
assert len(set(workers['worker_PIDs']))==16 and workers['torch_imported']==[False]*16
for cfg,row in zip(workers['configs'],registered):
    assert all(cfg[k]==row[k] for k in ('map','role','opponent','seed','family')) and cfg['TRAIN_scenario_index']==row['scenario_index'] and cfg['initial_reset_once'] and cfg['step_cost']==0
p0,n0,c0,f0=audit.raw_check(folder/'admitted-0.pt',32,True)
p1,n1,c1,f1=audit.raw_check(folder/'admitted-1.pt',32,True,n0)
s,ns,cs,fs=audit.raw_check(folder/'suffix.pt',64,False,n1)
assert p1['behavior_checkpoint_sha256']==s['behavior_checkpoint_sha256']
saved=audit.payload(folder/'TARGETS.pt');recomputed=targets.build(p1['arrays'],s['arrays'],'control')
for key in ('advantage','returns','base_advantage','base_returns','candidate_advantage','candidate_returns','eligible'):assert np.array_equal(recomputed[key],saved['targets'][key])
assert recomputed['reason']==saved['targets']['reason']
assert saved['learning_RNG_before_suffix']==saved['learning_RNG_after_suffix'] and saved['global_RNG_unchanged']
assert saved['behavior_model_digest']==saved['behavior_model_after_suffix'] and saved['Adam_digest']==saved['Adam_after_suffix']
boundaries={}
for update in (63,64):
    path=stage/f'update-{update}.pt';digest=restore.sha(path)
    model,opt,b,spec=restore.prepare(path,digest);counter=restore.install_counter(opt)
    proof=restore.restore_CPU(b,spec,model,opt,counter);proof.pop('CUDA_rng_payload')
    assert b['completed_updates']==update and b['actual_Adam_steps']==7680+(update-60)*128
    assert b['environment_steps']==30720+(update-60)*512
    meta=b['terminal_credit_experiment']
    assert meta['arm']=='control' and meta['phase']==1 and meta['half']==update-63
    assert meta['phase_complete']==(update==64)
    assert all(restore.sha(p)==h for p,h in b['frozen_inputs']['input_sha256'].items())
    assert restore.sha(b['rollout_evidence']['path'])==b['rollout_evidence']['sha256']
    boundaries[str(update)]={'path':str(path),'sha256':digest,'actual_Adam_steps':b['actual_Adam_steps'],'proof':proof}
report={'recovery_boundary_verified':True,'original_run_passed':False,'original_resource_gate_passed':False,
        'original_error':'post_update_resource reserve or swap gate failed; exact offending live metric was not saved',
        'last_saved_resource_update63':json.loads((stage/'PROGRESS.json').read_text())['records'][-1]['resources'],
        'boundaries':boundaries,'phase1_native_rows':2048,'admitted_rows':1024,'suffix_rows':1024,
        'all256_native_journals_verified':len(f0+f1+fs)==256,'all_raw_targets_recomputed':True,
        'normal_phase_native_resume_allowed':False,'learner_only_resume_at_next_fresh_registered_phase':True,
        'control_next_update':65,'candidate_completed_update':62,'candidate_next_update':63,
        'rerun_phase1_control_allowed':False,'parent_reset_allowed':False,'DEV_started':False,
        'new_native_games':0,'GPU_operations':0,'optimizer_steps':0}
(out/'AUDIT.json').write_text(json.dumps(report,indent=2))
print(json.dumps({k:v for k,v in report.items() if k!='boundaries'},indent=2))
