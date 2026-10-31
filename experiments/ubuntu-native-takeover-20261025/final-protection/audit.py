"""Final active-profile snapshot. Run only after root authorizes quiescence.

Default is plan-only: no locks, GPU queries, imports of torch, or file mutation.
"""
import argparse,csv,errno,fcntl,hashlib,json,os,subprocess,sys,time
from datetime import datetime,timezone
from pathlib import Path

HERE=Path(__file__).resolve().parent
TAKEOVER=HERE.parent
PROJECT=TAKEOVER.parent.parent

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def proc_records():
    rows=[]
    for directory in Path('/proc').glob('[0-9]*'):
        try:
            status=(directory/'stat').read_text().rsplit(')',1)[1].split()
            if status[0] in ('Z','X'):continue
            pid=int(directory.name)
            rows.append(dict(pid=pid,ppid=int(status[1]),name=(directory/'comm').read_text().strip(),arguments=(directory/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace').strip()))
        except (FileNotFoundError,ProcessLookupError,PermissionError,ValueError,IndexError):continue
    return rows

def processes(profile):
    all_processes=proc_records();by_pid={x['pid']:x for x in all_processes}
    native=[dict(pid=x['pid'],name=x['name']) for x in all_processes if 'vcmi' in x['name'].lower()]
    task_markers=('worker_entry.py','qualify_battle.py','learner-recovery/qualify.py','learner-recovery-v2/qualify.py','qualify_strategy.py')
    owned=[]
    for x in all_processes:
        if x['pid']==os.getpid():continue
        if not x['name'].lower().startswith(('python','vcmi')):continue
        if any(m in x['arguments'] for m in task_markers) and (str(TAKEOVER) in x['arguments'] or profile in x['arguments']):
            owned.append(dict(pid=x['pid'],name=x['name']))
    result=subprocess.run(['nvidia-smi','--query-compute-apps=pid,process_name,used_gpu_memory','--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=15)
    assert result.returncode==0,'GPU compute query failed: '+result.stderr[:500]
    compute=[]
    for values in csv.reader(result.stdout.splitlines()):
        if not values or not values[0].strip():continue
        assert len(values)>=3,values
        pid=int(values[0].strip());item=by_pid.get(pid,{});arguments=item.get('arguments','')
        related=str(TAKEOVER) in arguments or profile in arguments or 'heroes3' in arguments.lower()
        compute.append(dict(pid=pid,name=values[1].strip(),used_gpu_memory_MiB=values[2].strip(),current_task_related=related))
    graphics=[dict(pid=x['pid'],name=x['name']) for x in all_processes if x['name'] in ('Xorg','Xwayland','gnome-shell','ChatGPT','chrome','firefox')]
    return dict(native_processes=native,current_task_native_or_restore_drivers=owned,compute_processes=compute,current_task_compute_processes=[x for x in compute if x['current_task_related']],graphics_desktop_processes_observed=graphics,scope='nvidia-smi compute-apps is distinct from desktop/browser graphics processes. No GPU tensors or native games were started; process enumeration is a bounded current snapshot.')

def check_hash(path,expected):
    path=Path(path);before=path.stat();actual=sha(path);after=path.stat()
    assert (before.st_size,before.st_mtime_ns,before.st_ino)==(after.st_size,after.st_mtime_ns,after.st_ino),str(path)
    return dict(path=str(path),expected_sha256=expected,actual_sha256=actual,size=after.st_size,passed=actual==expected)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--execute',action='store_true');parser.add_argument('--out',type=Path);a=parser.parse_args()
    plan_path=HERE/'PLAN.json';plan=json.loads(plan_path.read_text())
    if not a.execute:
        print(json.dumps(dict(execute=False,plan_sha256=sha(plan_path),active_protected_files=len(plan['active_protected_sha256']),active_engine_files=len(plan['active_engine_sha256']),frozen_payloads=len(plan['frozen_payload_sha256']),locks_not_acquired=True,GPU_not_queried=True,awaiting_root_quiescence_authorization=True)));return
    assert a.out is not None,'Explicit new snapshot --out required'
    out=a.out.resolve();assert out.is_relative_to(HERE) and out!=HERE;out.mkdir(exist_ok=False)
    started=time.monotonic();handles=[];lock_info=[];rows=[];report=dict(passed=False,checked_at_utc=datetime.now(timezone.utc).isoformat(),plan_sha256=sha(plan_path),script_sha256=sha(__file__),executing_python=sys.executable)
    try:
        for path in map(Path,plan['resource_lock_paths']):
            assert path.is_file(),'Expected canonical resource lock missing: '+str(path)
            prior=path.stat();handle=path.open('a');handles.append(handle)
            fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
            actual=os.fstat(handle.fileno());current=path.stat()
            assert (prior.st_dev,prior.st_ino)==(actual.st_dev,actual.st_ino)==(current.st_dev,current.st_ino)
            with path.open('a') as other:
                try:fcntl.flock(other,fcntl.LOCK_EX|fcntl.LOCK_NB)
                except OSError as exc:assert exc.errno in (errno.EACCES,errno.EAGAIN)
                else:
                    fcntl.flock(other,fcntl.LOCK_UN);raise AssertionError('Separate descriptor unexpectedly acquired held lease')
            lock_info.append(dict(path=str(path),fd=handle.fileno(),device=actual.st_dev,inode=actual.st_ino,nonblocking_exclusive_flock_verified=True))
        report['lock_acquisition_order_GPU_then_pool']=lock_info
        before_processes=processes(plan['active_profile']);report['process_snapshot_before']=before_processes
        assert not before_processes['native_processes'] and not before_processes['current_task_native_or_restore_drivers'] and not before_processes['current_task_compute_processes'],'Native/current-task compute still live'
        categories=(('active_protected',plan['active_protected_sha256']),('active_engines',plan['active_engine_sha256']),('certificate_pins',plan['certificate_sha256']),('frozen_payloads',plan['frozen_payload_sha256']),('retained_history_artifacts',plan['history_artifact_sha256']))
        for category,items in categories:
            for path,expected in items.items():
                item=check_hash(path,expected);item['category']=category;rows.append(item)
        assert all(r['passed'] for r in rows),'Actual protected/certificate/frozen SHA mismatch'
        build=json.loads(Path(plan['profile_build_certificate']).read_text());assert build['passed'] and build['all_output_file_bytes_match_declared_origins'] and build['original_sources_unchanged'] and build['independent_file_inodes']
        assert build['canonical_resource_root']==str(Path(plan['resource_lock_paths'][0]).parent)
        assert sha(Path(plan['active_profile'])/'BUILD_MANIFEST.jsonl')==build['output_manifest_sha256']
        assert sha(Path(plan['active_profile'])/'SYMLINKS.json')==build['symlink_report_sha256']
        venv=json.loads(Path(plan['venv_certificate']).read_text());assert venv['passed'] and venv['wheel_record_audit_passed'] and venv['packages']==41
        assert sha(venv['audit_path'])==venv['audit_sha256'] and sha(venv['details_path'])==venv['details_sha256'] and sha(venv['requirements_path'])==venv['requirements_sha256']
        assert build['venv_certificate_sha256']==sha(plan['venv_certificate'])
        cleanup=json.loads(Path(plan['cleanup_certificate']).read_text());assert cleanup['passed'] and cleanup['removed_only_this_turn_generated_temporary_source']==plan['temporary_source']
        assert not Path(plan['temporary_source']).exists() and Path(plan['backup_file']).is_file()
        assert Path(plan['backup_file']).stat().st_size==plan['backup_bytes']==cleanup['compressed_backup_bytes']
        backup=json.loads(Path(plan['backup_manifest']).read_text(encoding='utf-8-sig'))
        assert backup['verified'] and backup['compressed_sha256']==plan['backup_compressed_sha256'] and backup['source_sha256']==plan['original_disk_sha256']
        for path,expected in cleanup['retained_certificates'].items():assert sha(path)==expected,path
        end_processes=processes(plan['active_profile']);report['process_snapshot_after']=end_processes
        assert not end_processes['native_processes'] and not end_processes['current_task_native_or_restore_drivers'] and not end_processes['current_task_compute_processes']
        report.update(passed=True,active_profile=plan['active_profile'],active_protected_files_read=len(plan['active_protected_sha256']),active_engine_files_read=len(plan['active_engine_sha256']),all_active_17_original_frozen_SHA_exact=True,all_active_8_engine_SHA_exact=True,new_source_freezes_and_payloads_exact=True,source_cleanup_certificate_passed=True,temporary_source_absent=True,original_compressed_backup_present_size_exact=True,original_compressed_backup_rehashed_now=False,full_27109_profile_rehashed_now=False,fresh_venv_payload_rehashed_now=False,original_bad_migration_copies_repaired_in_place=False,original_migration_integrity_report=plan['old_migration_audit'],native_games_started=0,GPU_operations=0,optimizer_steps=0,scope='Actual25 protected active file hashes plus certificate/freeze/history-artifact hashes under real canonical GPU→pool leases. Builder full-tree and fresh41-package RECORD audits are certificate-pinned, not repeated. Original83.7GB compressed backup is present/size checked and anchored to this-turn exact restoration proof, not rehashed here. Original bad migration copies remain separate and were not fixed in place. This snapshot does not establish model strength or promote any model.')
    except Exception as exc:report['error']=type(exc).__name__+': '+str(exc)
    finally:
        for handle in reversed(handles):
            try:fcntl.flock(handle,fcntl.LOCK_UN)
            finally:handle.close()
        retained=[]
        for entry in lock_info:
            p=Path(entry['path']);s=p.stat();retained.append(dict(path=str(p),inode_same=(s.st_dev,s.st_ino)==(entry['device'],entry['inode'])))
        report['leases_released_and_lock_files_not_deleted']=all(r['inode_same'] for r in retained) and len(lock_info)==2
        report['retained_lock_paths']=retained
        report['hash_checks']=rows;report['seconds']=time.monotonic()-started
        (out/'AUDIT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in report.items() if k not in ('hash_checks','process_snapshot_before','process_snapshot_after')},ensure_ascii=False,indent=2))
    if not report['passed']:raise SystemExit(1)

if __name__=='__main__':main()
