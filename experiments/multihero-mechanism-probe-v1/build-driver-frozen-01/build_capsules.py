#!/usr/bin/env python3
"""Incremental capsule preparation. DEFAULT DOES NOT LOCK, BUILD, OR WRITE NATIVE INPUTS."""
import argparse,json,os,shutil,signal,subprocess,time,traceback
from pathlib import Path
from capsule_support import LAB,sha,write,source_manifest,idle_locks

HERE=Path(__file__).resolve().parent
NAMES=('vcmiclient','vcmiserver','libvcmi.so')
VARIANTS=('original-unhandled','close-only','transfer-close')

def build(build_tree,log):
    with log.open('w') as output:
        child=subprocess.Popen(['ninja','-C',str(build_tree),'-v','vcmiclient','vcmiserver'],stdout=output,stderr=subprocess.STDOUT,start_new_session=True)
        try:code=child.wait()
        except BaseException:
            try:os.killpg(child.pid,signal.SIGTERM)
            except ProcessLookupError:pass
            try:child.wait(timeout=10)
            except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
            raise
    assert code==0,'ninja failed; preserve build log'
    assert 'CDirectorAI.cpp' in log.read_text(errors='replace'),'Director compilation not observed in verbose ninja log'
    return code

def assert_no_native(bin_dir):
    active=[]
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():continue
        try:
            executable=(proc/'exe').resolve(strict=True)
            maps=(proc/'maps').read_text()
            if executable.parent==bin_dir.resolve() or str(bin_dir.resolve())+'/libvcmi' in maps:active.append(proc.name)
        except (FileNotFoundError,PermissionError,ProcessLookupError):pass
    assert not active,'Native inputs still loaded by PID(s): '+','.join(active)

def fresh_write(path,data,mode=None):
    # Do not restore an old source mtime: ninja must invalidate every diagnostic object.
    path.write_bytes(data);now=time.time_ns();os.utime(path,ns=(now,now))
    if mode is not None:os.chmod(path,mode)

def accepted_loader_resolution(bin_dir,out):
    """ldd resolution only, never a native game; actual capsule runs require /proc maps."""
    evidence=[]
    for name in ('vcmiclient','vcmiserver'):
        completed=subprocess.run(['ldd',str(bin_dir/name)],env=dict(os.environ,LD_LIBRARY_PATH=str(bin_dir)),
            stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=30)
        (out/(name+'-accepted-ldd.log')).write_text(completed.stdout)
        assert completed.returncode==0
        libraries=[line.split('=>',1)[1].split(' (',1)[0].strip() for line in completed.stdout.splitlines() if 'libvcmi.so' in line and '=>' in line]
        assert len(libraries)==1 and Path(libraries[0]).resolve()==(bin_dir/'libvcmi.so').resolve(),'Accepted loader resolves outside accepted bin'
        evidence.append({'executable':str((bin_dir/name).resolve()),'ldd_libvcmi':libraries[0],
            'library_sha256':sha(Path(libraries[0])),'scope':'dynamic loader resolution; no native game or /proc process proof claimed'})
    return evidence

def execute(args,plan):
    source=args.source_tree.resolve();build_tree=args.build_tree.resolve();bin_dir=build_tree/'bin'
    backup=args.out/'accepted-backup';result={'native_games_started':0,'optimizer_steps':0,'build_kind':'incremental_from_accepted_shared_tree',
        'variants':[],'accepted_sources_restored':False,'accepted_published_binaries_restored':False,'rebuild_required':True}
    with idle_locks():
        # Busy exits happen before backup/mutation. Also reject any native process that bypassed a lease.
        assert_no_native(bin_dir)
        backup.mkdir()
        base=source_manifest(source);write(backup/'base-source-manifest.json',base)
        assert not any(info.get('directory') for info in base.values()),'External symlink source directories require expanded attestation before build'
        director=source/'AI/DirectorAI';source_bytes={n:(director/n).read_bytes() for n in ('CDirectorAI.cpp','CDirectorAI.h')}
        source_modes={n:(director/n).stat().st_mode for n in source_bytes}
        bin_bytes={n:(bin_dir/n).read_bytes() for n in NAMES};bin_modes={n:(bin_dir/n).stat().st_mode for n in NAMES}
        accepted_hashes={n:sha(bin_dir/n) for n in NAMES}
        for name,data in source_bytes.items():(backup/name).write_bytes(data)
        for name,data in bin_bytes.items():(backup/name).write_bytes(data)
        write(backup/'published-artifacts.json',accepted_hashes)
        mutated=False
        def interrupted(signum,frame):raise InterruptedError('Signal during capsule build: '+str(signum))
        old_handlers={sig:signal.signal(sig,interrupted) for sig in (signal.SIGTERM,signal.SIGINT)}
        try:
            for variant in VARIANTS:
                capsule=args.out/variant;capsule.mkdir()
                candidate=args.candidates/variant
                candidate_bytes={name:(candidate/name).read_bytes() for name in source_bytes}
                import hashlib
                assert all(hashlib.sha256(data).hexdigest()==plan['candidate_sha256'][variant+'/'+name] for name,data in candidate_bytes.items()),'Reviewed candidate changed before compilation'
                # Snapshot exact inputs before compiler invocation, not a guessed final source.
                mutated=True
                for name,data in candidate_bytes.items():fresh_write(director/name,data,source_modes[name])
                build_manifest=source_manifest(source)
                allowed={'AI/DirectorAI/CDirectorAI.cpp','AI/DirectorAI/CDirectorAI.h'}
                assert set(base)==set(build_manifest)
                assert {p for p in base if base[p]!=build_manifest[p]}<=allowed,'Unrelated source changed during build window'
                write(capsule/'base-source-manifest.json',base);write(capsule/'build-source-manifest.json',build_manifest)
                snapshots=capsule/'source-snapshot/AI/DirectorAI';snapshots.mkdir(parents=True)
                for name in source_bytes:(snapshots/name).write_bytes((director/name).read_bytes())
                for relative in ('server/CGameHandler.h','server/CGameHandler.cpp','server/battles/BattleProcessor.cpp'):
                    target=capsule/'source-snapshot'/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((source/relative).read_bytes())
                started=time.time();code=build(build_tree,capsule/'build.log')
                assert source_manifest(source)==build_manifest,'Source changed while compiling'
                dest=capsule/'bin';dest.mkdir()
                for name in NAMES:shutil.copy2(bin_dir/name,dest/name)
                shutil.copytree(bin_dir/'config',dest/'config')
                artifacts={str(p.relative_to(capsule)):sha(p) for p in capsule.rglob('*') if p.is_file()}
                assert artifacts['bin/libvcmi.so']!=accepted_hashes['libvcmi.so'],'Implementation library unchanged; verify link/build graph'
                att={'schema':'native-incremental-capsule-attestation-v1','build_kind':'incremental_from_accepted_shared_tree',
                    'variant':variant,'source_tree_at_build':str(source),'build_tree':str(build_tree),'ninja_exit':code,
                    'director_compile_observed':True,'build_command':['ninja','-C',str(build_tree),'-v','vcmiclient','vcmiserver'],
                    'build_log_sha256':sha(capsule/'build.log'),'base_source_manifest_sha256':sha(capsule/'base-source-manifest.json'),
                    'build_source_manifest_sha256':sha(capsule/'build-source-manifest.json'),'accepted_artifacts':accepted_hashes,
                    'artifacts':artifacts,'started_unix':started,'finished_unix':time.time(),
                    'independent_full_build':False,'native_run_or_loaded_library_verified':False}
                write(capsule/'BUILD_ATTESTATION.json',att);result['variants'].append({'variant':variant,'capsule':str(capsule),'attestation_sha256':sha(capsule/'BUILD_ATTESTATION.json')})
        except BaseException as error:
            result['build_error']=repr(error);result['build_context']=traceback.format_exc()
        finally:
            # Restore under the SAME leases. Prevent a second SIGTERM from skipping cleanup.
            for sig in old_handlers:signal.signal(sig,signal.SIG_IGN)
            if mutated:
                try:
                    for name,data in source_bytes.items():fresh_write(director/name,data,source_modes[name])
                    result['accepted_sources_restored']=source_manifest(source)==base
                    assert result['accepted_sources_restored'],'Accepted source tree differs from full backup manifest'
                    build(build_tree,args.out/'restore-accepted-build.log')
                    result['accepted_rebuilt_binary_hashes']={name:sha(bin_dir/name) for name in NAMES}
                    assert result['accepted_rebuilt_binary_hashes']==accepted_hashes,'Accepted rebuild bytes differ from published binaries'
                    result['accepted_loader_resolution']=accepted_loader_resolution(bin_dir,args.out)
                    result['accepted_published_binaries_restored']=True;result['rebuild_required']=False
                except BaseException as error:
                    result['restore_build_error']=repr(error);result['restore_build_context']=traceback.format_exc()
                    # Preserve failure evidence and restore the published executable payloads.
                    fallback_errors=[]
                    for name,data in source_bytes.items():
                        try:fresh_write(director/name,data,source_modes[name])
                        except BaseException as failure:fallback_errors.append({'source':name,'error':repr(failure)})
                    for name,data in bin_bytes.items():
                        try:fresh_write(bin_dir/name,data,bin_modes[name])
                        except BaseException as failure:fallback_errors.append({'binary':name,'error':repr(failure)})
                    result['fallback_restoration_errors']=fallback_errors
                    result['accepted_sources_restored']=source_manifest(source)==base
                    result['accepted_published_binaries_restored']=all(sha(bin_dir/n)==accepted_hashes[n] for n in NAMES)
                    result['rebuild_required']=True
                    try:result['accepted_loader_resolution']=accepted_loader_resolution(bin_dir,args.out)
                    except BaseException as failure:result['accepted_loader_resolution_error']=repr(failure)
            else:
                result['accepted_sources_restored']=source_manifest(source)==base
                result['accepted_published_binaries_restored']=all(sha(bin_dir/n)==accepted_hashes[n] for n in NAMES)
                result['rebuild_required']=False
            result['accepted_artifact_resolved_paths']={n:str((bin_dir/n).resolve()) for n in NAMES}
            result['native_loading_not_tested_during_build']=True
            result['source_manifest_after_restore']=source_manifest(source)
            result['passed']=len(result['variants'])==len(VARIANTS) and not result.get('build_error') and result['accepted_sources_restored'] and result['accepted_published_binaries_restored'] and not result['rebuild_required']
            write(args.out/'EXECUTION.json',result)
            for sig,handler in old_handlers.items():signal.signal(sig,handler)
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-tree',type=Path,default=LAB/'src/vcmi-adv')
    p.add_argument('--build-tree',type=Path,default=LAB/'src/vcmi-adv-build')
    p.add_argument('--candidates',type=Path,default=HERE/'candidates-02')
    p.add_argument('--out',type=Path,required=True);p.add_argument('--execute',action='store_true')
    args=p.parse_args();args.out=args.out.resolve();args.out.mkdir(parents=True,exist_ok=False)
    plan={'prepared_only':not args.execute,'source_tree':str(args.source_tree),'build_tree':str(args.build_tree),
        'candidates':str(args.candidates),'lock_order':['GPU learner NB','pool NB'],'variants':VARIANTS,
        'native_games_started':0,'optimizer_steps':0,'explicit_execution_required':True,
        'restore_requires_new_mtime_then_ninja':True,'fallback_published_binaries_if_restore_rebuild_fails':True,
        'build_kind':'incremental_from_accepted_shared_tree','driver_sha256':sha(Path(__file__))}
    plan['candidate_sha256']={variant+'/'+name:sha(args.candidates/variant/name) for variant in VARIANTS for name in ('CDirectorAI.cpp','CDirectorAI.h')}
    plan['support_sha256']=sha(HERE/'capsule_support.py')
    plan['native_inputs_written']=False if not args.execute else 'Only during explicit locked execution; see EXECUTION.json'
    write(args.out/'PLAN.json',plan)
    if not args.execute:print(json.dumps(plan,indent=2));return 0
    try:result=execute(args,plan)
    except BaseException as error:
        result={'error':repr(error),'context':traceback.format_exc(),'native_games_started':0,'optimizer_steps':0}
        write(args.out/'BLOCKED_OR_FAILED.json',result)
    print(json.dumps({k:v for k,v in result.items() if k!='source_manifest_after_restore'},indent=2))
    return 0 if result.get('passed') else 1

if __name__=='__main__':raise SystemExit(main())
