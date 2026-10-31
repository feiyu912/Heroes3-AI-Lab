"""New final snapshot epoch; retain first plan and include completed qualifiers."""
import hashlib,json
from pathlib import Path

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def main():
    new_plan=HERE/'PLAN.v2.json';new_script=HERE/'audit_v2.py';assert not new_plan.exists() and not new_script.exists()
    original=HERE/'audit.py';source=original.read_text()
    source=source.replace("plan_path=HERE/'PLAN.json'","plan_path=HERE/'PLAN.v2.json'")
    old="related=str(TAKEOVER) in arguments or profile in arguments or 'heroes3' in arguments.lower()"
    new="""related=str(TAKEOVER) in arguments or profile in arguments or 'heroes3' in arguments.lower()
        desktop_file_manager=item.get('name')=='nautilus' and Path('/proc') .joinpath(str(pid),'exe').resolve()==Path('/usr/bin/nautilus')
        if desktop_file_manager:related=False"""
    assert old in source;source=source.replace(old,new)
    old="compute.append(dict(pid=pid,name=values[1].strip(),used_gpu_memory_MiB=values[2].strip(),current_task_related=related))"
    new="compute.append(dict(pid=pid,name=values[1].strip(),used_gpu_memory_MiB=values[2].strip(),current_task_related=related,verified_desktop_file_manager=desktop_file_manager))"
    assert old in source;source=source.replace(old,new)
    old="return dict(native_processes=native,"
    new="return dict(raw_nvidia_compute_query_stdout=result.stdout,raw_nvidia_compute_query_stderr=result.stderr,native_processes=native,"
    assert old in source;source=source.replace(old,new)
    old="('retained_history_artifacts',plan['history_artifact_sha256']))"
    new="('retained_history_artifacts',plan['history_artifact_sha256']),('completed_qualifications',plan['completed_qualification_sha256']))"
    assert old in source;source=source.replace(old,new)
    old="        end_processes=processes(plan['active_profile']);report['process_snapshot_after']=end_processes"
    new="""        qualifiers={name:json.loads(Path(path).read_text()) for name,path in plan['qualification_certificates'].items()}
        assert all(r['passed'] for r in qualifiers.values())
        battle=qualifiers['battle_runtime'];independent=qualifiers['battle_independent'];learner=qualifiers['learner'];controller=qualifiers['controller']
        assert battle['normal_completed_games']==4 and battle['historical_trajectories_equal']
        assert independent['games']==4 and independent['decisions']==102 and independent['raw_chain_complete'] and independent['full_CPU_NN_replay']
        assert learner['optimizer_step_calls']==controller['optimizer_step_calls']==0 and learner['actual_Adam_steps']==7936
        assert learner['full_payload_exact'] and learner['four_RNG_actual_draw_recovery']['passed'] and learner['four_RNG_actual_draw_recovery']['repeated_draws_exact']
        assert learner['CUDA_restoration']['CUDA_restore_executed'] and learner['CPU_CUDA_NN_comparison']['passed']
        assert controller['worker_exit']==0 and controller['owned_group_drained'] and controller['result_sha256']==sha(plan['qualification_certificates']['learner'])
        report['completed_qualification_certificates_passed']=True
        report['desktop_compute_entries_are_retained_and_not_killed']=True
        end_processes=processes(plan['active_profile']);report['process_snapshot_after']=end_processes"""
    assert old in source;source=source.replace(old,new)
    new_script.write_text(source)
    plan=json.loads((HERE/'PLAN.json').read_text())
    named={'battle_runtime':BASE/'battle-runtime-02/RESULT.json','battle_independent':BASE/'battle-independent-01/AUDIT.json','learner':BASE/'learner-recovery-actual-01/RESULT.json','controller':BASE/'LEARNER_RECOVERY_CONTROLLER.json'}
    assert all(json.loads(p.read_text())['passed'] for p in named.values())
    learner=json.loads(named['learner'].read_text());extra={str(p):sha(p) for p in named.values()}
    extra[str(Path(learner['roundtrip_checkpoint']))]=learner['roundtrip_sha256']
    for p in (BASE/'battle-runtime-02/FREEZE.json',BASE/'battle-runtime-02/PLAN.json',BASE/'learner-recovery-actual-01/NN_COMPARISON.pt'):extra[str(p)]=sha(p)
    plan.update(epoch=2,prior_plan_sha256=sha(HERE/'PLAN.json'),root_authorized_after_native_and_GPU_exit=True,qualification_certificates={n:str(p) for n,p in named.items()},completed_qualification_sha256=extra)
    plan['certificate_sha256'].update({str(new_script):sha(new_script),str(Path(__file__)):sha(__file__)})
    new_plan.write_text(json.dumps(plan,ensure_ascii=False,indent=2))
    (HERE/'DERIVATION.v2.json').write_text(json.dumps(dict(prior_plan_sha256=sha(HERE/'PLAN.json'),prior_script_sha256=sha(original),new_plan_sha256=sha(new_plan),new_script_sha256=sha(new_script),change='Add four completed qualifier certificates, zero-update checkpoint and freeze evidence; retain raw GPU compute query and verify nautilus GUI identity; no global process kill or empty-compute-list claim.'),indent=2))
    print(json.dumps(dict(prepared=True,epoch=2,extra_pins=len(extra),new_plan_sha256=sha(new_plan),old_plan_preserved=True),indent=2))

if __name__=='__main__':main()
