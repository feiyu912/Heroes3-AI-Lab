#!/usr/bin/env python3
"""Temporary fake-tree tests. No compiler, loader, native process, GPU or shared lock."""
import argparse,contextlib,fcntl,json,os,tempfile,time
from pathlib import Path
from unittest.mock import patch
import build_capsules as driver
import capsule_support as support

HERE=Path(__file__).resolve().parent
checks={}
@contextlib.contextmanager
def fake_leases():yield

def fixture(root):
    source=root/'src';build=root/'build';out=root/'out';candidate=root/'candidates'
    for relative,data in {'AI/DirectorAI/CDirectorAI.cpp':b'accepted-cpp','AI/DirectorAI/CDirectorAI.h':b'accepted-h',
        'server/CGameHandler.h':b'server-h','server/CGameHandler.cpp':b'server-cpp','server/battles/BattleProcessor.cpp':b'battle'}.items():
        p=source/relative;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
    (build/'bin/config').mkdir(parents=True);(build/'bin/config/settings.json').write_text('{}')
    for name in driver.NAMES:(build/'bin'/name).write_bytes(('accepted-'+name).encode())
    for variant in driver.VARIANTS:
        folder=candidate/variant;folder.mkdir(parents=True)
        for name in ('CDirectorAI.cpp','CDirectorAI.h'):(folder/name).write_text(variant+' '+name)
    for relative,target in support.RUNTIME_ASSET_LINKS.items():
        path=source/relative;path.parent.mkdir(parents=True,exist_ok=True);path.symlink_to(target,target_is_directory=True)
    out.mkdir()
    return argparse.Namespace(source_tree=source,build_tree=build,out=out,candidates=candidate)

def test_build(root,fail_variant=False,fail_restore=False):
    args=fixture(root);original=support.source_manifest(args.source_tree)
    binaries={n:(args.build_tree/'bin'/n).read_bytes() for n in driver.NAMES}
    before=(args.source_tree/'AI/DirectorAI/CDirectorAI.cpp').stat().st_mtime_ns
    calls=[]
    def fake_build(tree,log):
        cpp=(args.source_tree/'AI/DirectorAI/CDirectorAI.cpp').read_bytes();restoring=cpp==b'accepted-cpp';calls.append(restoring)
        log.write_text('SYNTHETIC ONLY mock compile CDirectorAI.cpp\n')
        for name in driver.NAMES:(tree/'bin'/name).write_bytes(binaries[name] if restoring else (binaries[name] if name=='vcmiclient' else b'probe-'+cpp+name.encode()))
        if (fail_variant and not restoring) or (fail_restore and restoring):raise RuntimeError('SYNTHETIC compiler failure')
        return 0
    with patch.object(driver,'idle_locks',fake_leases),patch.object(driver,'assert_no_native',lambda _:None),\
         patch.object(driver,'build',fake_build),patch.object(driver,'accepted_loader_resolution',lambda *_:[{'SYNTHETIC_ONLY':True}]):
        plan={'candidate_sha256':{variant+'/'+name:support.sha(args.candidates/variant/name) for variant in driver.VARIANTS for name in ('CDirectorAI.cpp','CDirectorAI.h')}}
        result=driver.execute(args,plan)
    assert support.source_manifest(args.source_tree)==original
    assert all((args.build_tree/'bin'/n).read_bytes()==binaries[n] for n in driver.NAMES)
    assert (args.source_tree/'AI/DirectorAI/CDirectorAI.cpp').stat().st_mtime_ns>before
    assert calls[-1] is True,'Restoration must rebuild accepted source after probe objects'
    assert result['rebuild_required']==fail_restore and result['accepted_sources_restored'] and result['accepted_published_binaries_restored']
    assert result['passed']==(not fail_variant and not fail_restore)
    if result['passed']:
        for variant in driver.VARIANTS:
            att=support.verify_attestation(args.out/variant,variant)
            assert att['artifacts']['bin/vcmiclient']==att['accepted_artifacts']['vcmiclient'],'Unchanged linked client must be permitted'
    return args,result

with tempfile.TemporaryDirectory() as temporary:
    temp=Path(temporary)
    args,result=test_build(temp/'success');checks['success_restores_sources_new_mtime_rebuilds_accepted']=True
    manifest=support.source_manifest(args.source_tree)
    links=support.validate_source_links(manifest)
    assert set(links)==set(support.RUNTIME_ASSET_LINKS)
    assert not any(p.startswith(asset+'/') for p in manifest for asset in links)
    assert all('target_sha256' not in info for info in links.values())
    checks['three_fixed_runtime_asset_links_accepted_without_dereferencing']=True
    unknown=temp/'unknown-source';unknown.mkdir();bad=args.source_tree/'lib/external';bad.parent.mkdir();bad.symlink_to(unknown,target_is_directory=True)
    try:support.validate_source_links(support.source_manifest(args.source_tree));raise AssertionError('Unknown source link accepted')
    except AssertionError as error:assert 'Unknown source link accepted' not in str(error)
    checks['unknown_external_source_directory_rejected']=True;bad.unlink()
    wrong=args.source_tree/'data/Data';wrong.unlink();wrong.symlink_to(unknown,target_is_directory=True)
    try:support.validate_source_links(support.source_manifest(args.source_tree));raise AssertionError('Wrong asset target accepted')
    except AssertionError as error:assert 'Wrong asset target accepted' not in str(error)
    checks['wrong_fixed_asset_target_rejected']=True;wrong.unlink();wrong.symlink_to(support.RUNTIME_ASSET_LINKS['data/Data'],target_is_directory=True)
    model=args.source_tree/'defender-ipnkyfqb-best3.onnx';model.symlink_to(support.RUNTIME_DANGLING_FILE_LINKS[model.name])
    reviewed=support.source_manifest(args.source_tree);support.validate_source_links(reviewed)
    info=reviewed[model.name]
    assert info['lexists'] and info['target_exists'] is False and 'target_sha256' not in info and info['symlink']=='../export/defender-ipnkyfqb-best3.onnx'
    checks['exact_reviewed_dangling_runtime_onnx_no_fake_sha_accepted']=True
    unknown_model=args.source_tree/'unknown.onnx';unknown_model.symlink_to('../export/unknown.onnx')
    try:support.validate_source_links(support.source_manifest(args.source_tree));raise AssertionError('Unknown dangling ONNX accepted')
    except AssertionError as error:assert 'Unknown dangling ONNX accepted' not in str(error)
    checks['unknown_dangling_onnx_rejected']=True;unknown_model.unlink()
    model.unlink();model.symlink_to('../elsewhere/defender-ipnkyfqb-best3.onnx')
    try:support.validate_source_links(support.source_manifest(args.source_tree));raise AssertionError('Wrong known model target accepted')
    except AssertionError as error:assert 'Wrong known model target accepted' not in str(error)
    checks['reviewed_model_wrong_raw_target_rejected']=True;model.unlink()
    checks['unchanged_client_changed_lib_attestation_accepted']=True
    test_build(temp/'variant-failure',True,False);checks['variant_failure_still_rebuilds_accepted']=True
    test_build(temp/'restore-failure',True,True);checks['restore_build_failure_restores_published_bin_flags_rebuild']=True
    capsule=args.out/'close-only';bin_dir=capsule/'bin';fakeproc=temp/'proc/123';fakeproc.mkdir(parents=True)
    (fakeproc/'exe').symlink_to(bin_dir/'vcmiclient');lib=bin_dir/'libvcmi.so';stat=lib.stat()
    maps=f'000-fff r-xp 00000000 {os.major(stat.st_dev):02x}:{os.minor(stat.st_dev):02x} {stat.st_ino} {lib}\n'
    (fakeproc/'maps').write_text(maps)
    with patch.object(support,'PROC',temp/'proc'):
        (fakeproc/'task/123').mkdir(parents=True);(fakeproc/'task/123/comm').write_text('vcmiClient\n')
        (fakeproc/'task/456').mkdir(parents=True);(fakeproc/'task/456/comm').write_text('runServer\n')
        observation=support.loaded_evidence(123,bin_dir)
        assert observation['valid'];checks['maps_real_path_inode_device_sha_gate']=True
        log='CVCMIServer created! UUID: SYNTHETIC\nServer gives turn to red\n'
        assert support.thread_server_gate([observation],log,False)['passed']
        checks['thread_mode_client_library_and_runServer_and_native_log_positive']=True
        (fakeproc/'task/456/comm').write_text('otherThread\n')
        missing=support.loaded_evidence(123,bin_dir)
        try:support.thread_server_gate([missing],log,False);raise AssertionError('Missing server thread accepted')
        except AssertionError as error:assert 'Missing server thread accepted' not in str(error)
        checks['missing_runServer_thread_rejected']=True
        try:support.thread_server_gate([observation],'',False);raise AssertionError('Missing server log accepted')
        except AssertionError as error:assert 'Missing server log accepted' not in str(error)
        checks['missing_native_server_log_rejected']=True
        try:support.thread_server_gate([observation],log,True);raise AssertionError('Process mode accepted')
        except AssertionError as error:assert 'Process mode accepted' not in str(error)
        checks['process_setting_true_rejected']=True
        (fakeproc/'maps').write_text(maps.replace(str(stat.st_ino),str(stat.st_ino+1)))
        assert not support.loaded_evidence(123,bin_dir)['valid'];checks['wrong_mapped_inode_rejected']=True
        (fakeproc/'maps').write_text(maps.replace(str(lib),str(lib)+' (deleted)'))
        assert not support.loaded_evidence(123,bin_dir)['valid'];checks['deleted_mapped_library_rejected']=True
    locklab=temp/'fake-lab';(locklab/'evaluations').mkdir(parents=True)
    with patch.object(support,'LAB',locklab):
        # Locks are temporary test files, not the actual shared GPU/pool leases.
        with support.idle_locks():
            for name in ('.gpu-learner-lock','.pool-lock'):
                with (locklab/'evaluations'/name).open('a+') as other:
                    try:fcntl.flock(other,fcntl.LOCK_EX|fcntl.LOCK_NB);raise AssertionError('Held lock not exclusive')
                    except BlockingIOError:pass
        with (locklab/'evaluations/.pool-lock').open('a+') as held:
            fcntl.flock(held,fcntl.LOCK_EX|fcntl.LOCK_NB)
            try:
                with support.idle_locks():raise AssertionError('Busy pool accepted')
            except RuntimeError:pass
            with (locklab/'evaluations/.gpu-learner-lock').open('a+') as released:fcntl.flock(released,fcntl.LOCK_EX|fcntl.LOCK_NB)
        checks['nonblocking_busy_pool_releases_first_gpu_lock']=True
    # Alter a source attestation after creation: original manifest/hash must reject it.
    (capsule/'source-snapshot/AI/DirectorAI/CDirectorAI.cpp').write_text('tampered')
    try:support.verify_attestation(capsule,'close-only');raise AssertionError('Changed source accepted')
    except AssertionError as error:assert 'Changed source accepted' not in str(error)
    checks['tampered_source_snapshot_rejected']=True
assert all(checks.values())
report={'passed':True,'temporary_fake_trees_only':True,'compiler_started':False,'ldd_started':False,
    'native_games_started':0,'actual_shared_locks_acquired':False,'native_inputs_written':False,'checks':checks}
(HERE/'CAPSULE_CPU_AUDIT.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
