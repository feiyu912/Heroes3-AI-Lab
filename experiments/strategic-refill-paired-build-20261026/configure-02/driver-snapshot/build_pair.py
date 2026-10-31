"""Isolated paired source epoch; each invocation is a separately archived stage."""
import argparse, contextlib, fcntl, hashlib, importlib.util, json, os
from pathlib import Path
import resource, shutil, signal, subprocess, sys, time, traceback

HERE = Path(__file__).resolve().parent
CONTRACT_PATH = HERE / 'build-contract-v1.json'
EXPECTED_CONTRACT = '94fababf70089e1d944b17280c0d6e003ba39dc34c6a34fcb853316dc4308cf2'
NAMES = ('vcmiclient', 'vcmiserver', 'libvcmi.so')

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()

def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')

def manifest(root):
    result = {}
    for folder, dirs, names in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d != '.git')
        for name in sorted(dirs + names):
            path = Path(folder) / name
            rel = str(path.relative_to(root))
            if path.is_symlink():
                entry = dict(symlink=os.readlink(path), directory=path.is_dir(),
                             lexists=os.path.lexists(path), target_exists=path.exists(), file=path.is_file())
                if path.is_file():
                    entry.update(target_sha256=sha(path), bytes=path.stat().st_size)
                result[rel] = entry
            elif path.is_file():
                result[rel] = dict(sha256=sha(path), bytes=path.stat().st_size)
    return result

def inputs():
    assert sha(CONTRACT_PATH) == EXPECTED_CONTRACT, 'Registered contract changed'
    c = json.loads(CONTRACT_PATH.read_text())
    for key in ('parent_manifest', 'candidate_manifest'):
        assert sha(c[key]['path']) == c[key]['sha256'], key
    for arm, key in [('baseline', 'parent_manifest'), ('candidate', 'candidate_manifest')]:
        for rel, entry in c['payloads'].items():
            assert sha(Path(c[key]['path']).parent / 'candidate' / rel) == entry[arm + '_sha256']
    assert [p for p, e in c['payloads'].items() if e['baseline_sha256'] != e['candidate_sha256']] == [c['only_arm_source_difference']]
    return c

def protection(c):
    profile = Path(c['profile_root'])
    result = {'source': manifest(profile / 'heroes3-ai-lab/src/vcmi-adv')}
    paths = [CONTRACT_PATH, Path(__file__), HERE / 'stage_entry.py']
    for key in ('parent_manifest', 'candidate_manifest'):
        paths.append(Path(c[key]['path']))
        paths += [Path(c[key]['path']).parent / 'candidate' / rel for rel in c['payloads']]
    for base in (profile / 'heroes3-ai-lab/src/vcmi-adv-build/bin',
                 profile / 'runtime/engine-strategic', profile / 'runtime/engine-battle'):
        paths += [base / n for n in NAMES if (base / n).is_file()]
    result['files'] = {str(p): sha(p) for p in paths}
    return result

def copy_source(source, target):
    shutil.copytree(source, target, symlinks=True, ignore=shutil.ignore_patterns('.git'))
    assert manifest(source) == manifest(target), 'Independent source copy differs'
    for rel, info in manifest(source).items():
        if 'sha256' in info:
            a, b = (source / rel).stat(), (target / rel).stat()
            assert (a.st_dev, a.st_ino) != (b.st_dev, b.st_ino), 'Hard-linked protected input'

def set_payload(c, arm):
    root = Path(c['scratch_root']) / 'source'
    src = Path(c['parent_manifest' if arm == 'baseline' else 'candidate_manifest']['path']).parent / 'candidate'
    for rel, entry in c['payloads'].items():
        target = root / rel
        assert not target.is_symlink()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((src / rel).read_bytes())
        assert sha(target) == entry[arm + '_sha256']

def prepare(c, out):
    scratch = Path(c['scratch_root'])
    assert not scratch.exists(), 'Fresh prepare only; never overwrite prior scratch'
    scratch.mkdir()
    source = Path(c['profile_root']) / 'heroes3-ai-lab/src/vcmi-adv'
    links = {p: e for p, e in manifest(source).items() if 'symlink' in e}
    expected = {
        'data/Maps': 'heroes3-ai-lab/data/vcmi/Maps',
        'data/Data': 'heroes3-ai-lab/data/vcmi/Data',
        'data/Mods': 'heroes3-ai-lab/data/vcmi/Mods',
        'defender-ipnkyfqb-best3.onnx': 'heroes3-ai-lab/src/export/defender-ipnkyfqb-best3.onnx',
    }
    assert set(links) == set(expected), 'Unreviewed source link'
    for rel, target in expected.items():
        assert links[rel]['symlink'] == str(Path(c['profile_root']) / target)
        assert links[rel]['target_exists'] == (rel != 'defender-ipnkyfqb-best3.onnx')
    copy_source(source, scratch / 'source')
    assert not list((scratch / 'source').rglob('*.o')) and not list((scratch / 'source').rglob('*.gch'))
    (scratch / 'build').mkdir()
    (scratch / 'install').mkdir()
    set_payload(c, 'baseline')
    write(scratch / 'BASELINE_SOURCE.json', manifest(scratch / 'source'))
    write(out / 'REVIEWED_SOURCE_LINKS.json', links)
    write(scratch / 'PREPARED.json', {'contract_sha256': EXPECTED_CONTRACT, 'old_objects_or_PCH': 0,
          'source_manifest_sha256': sha(scratch / 'BASELINE_SOURCE.json')})

def environment(c):
    prefix = Path(c['toolchain_root'])
    cert_path = prefix / 'QUALIFIED_TOOLCHAIN.json'
    cert = json.loads(cert_path.read_text())
    assert cert['passed'] and cert['toolchain_root'] == str(prefix)
    assert cert['actual_executable_compilations'] >= 2 and cert['actual_inherited_flocks']
    evidence = Path(cert['qualification_evidence']) / 'RESULT.json'
    assert sha(evidence) == cert['result_sha256'], 'Toolchain evidence changed'
    env = cert['environment'].copy()
    assert 'GCC_EXEC_PREFIX' not in env
    env['HEROES3_TOOLCHAIN_ROOT'] = str(prefix)
    env['HEROES3_LAB_ROOT'] = str(Path(c['profile_root']) / 'heroes3-ai-lab')
    return env, cert_path

def verify_capsule(c, arm):
    capsule = Path(c['capsule_root']) / arm
    attestation = json.loads((capsule / 'BUILD_ATTESTATION.json').read_text())
    assert attestation['contract_sha256'] == EXPECTED_CONTRACT and attestation['arm'] == arm
    assert sha(capsule / 'build-source-manifest.json') == attestation['source_manifest_sha256']
    assert manifest(capsule / 'source-snapshot') == json.loads((capsule / 'build-source-manifest.json').read_text())
    expected_bins = json.loads((capsule / 'binary-sha256.json').read_text())
    assert set(expected_bins) == set(NAMES)
    assert {name: sha(capsule / 'bin' / name) for name in NAMES} == expected_bins == attestation['binary_sha256']
    assert json.loads((capsule / 'EXECUTION.json').read_text())['passed']
    return capsule

def dependency_closure(c):
    path = Path(c['toolchain_root']) / 'TARGET_DEPENDENCY_CLOSURE.json'
    closure = json.loads(path.read_text())
    assert closure['passed'] is True and closure['files'], 'Final target closure is not qualified'
    for filename, expected in closure['files'].items():
        target = Path(filename)
        if not target.is_absolute():
            target = Path(c['toolchain_root']) / target
        assert sha(target) == expected, 'Target closure input changed: ' + filename
    for filename, expected in closure.get('links', {}).items():
        target = Path(filename)
        if not target.is_absolute():
            target = Path(c['toolchain_root']) / target
        assert target.is_symlink() and os.readlink(target) == expected, 'Target closure link changed: ' + filename
    return dict(path=str(path), sha256=sha(path), verified_files=len(closure['files']), verified_links=len(closure.get('links', {})))

def build_admission(c, configured):
    scratch = Path(c['scratch_root'])
    admission = json.loads((scratch / 'BUILD_ADMISSION.json').read_text())
    assert admission['passed'] is True and admission['contract_sha256'] == EXPECTED_CONTRACT
    assert admission['configured_sha256'] == sha(scratch / 'CONFIGURED.json')
    assert admission['build_ninja_sha256'] == sha(scratch / 'build/build.ninja')
    assert admission['compile_commands_sha256'] == sha(scratch / 'build/compile_commands.json')
    assert admission['dependency_closure_sha256'] == configured['dependency_closure']['sha256']
    return admission

def configure_command(c, out):
    scratch, prefix = Path(c['scratch_root']), Path(c['toolchain_root'])
    sysroot = prefix / 'sysroot'
    lab = Path(c['profile_root']) / 'heroes3-ai-lab'
    old = json.loads((HERE.parent / 'ubuntu-native-takeover-20261025/toolchain-plan/TOOLCHAIN_SOURCE_PLAN.json').read_text())['old_cmake_cache']
    template = HERE.parent / 'ubuntu-native-takeover-20261025/toolchain-plan/ubuntu22-gcc11.cmake.in'
    toolfile = scratch / 'toolchain.cmake'
    if toolfile.exists():
        assert toolfile.read_bytes() == template.read_bytes()
    else:
        shutil.copyfile(template, toolfile)
    command = [str(lab / 'python-packages/cmake/data/bin/cmake'), '-S', str(scratch / 'source'), '-B', str(scratch / 'build'), '-G', 'Ninja',
               '-DCMAKE_TOOLCHAIN_FILE=' + str(toolfile), '-DCMAKE_BUILD_TYPE=Release',
               '-DCMAKE_INSTALL_PREFIX=' + str(scratch / 'install'), '-DCMAKE_EXPORT_COMPILE_COMMANDS=ON']
    for key, entry in old.items():
        if key.startswith('ENABLE_') or key in ('COPY_CONFIG_ON_BUILD', 'VCMI_FLATPAK', 'VCMI_PORTMASTER', 'BIN_DIR', 'LIB_DIR', 'DATA_DIR'):
            command.append('-D' + key + ':' + entry['kind'] + '=' + entry['value'])
        elif key in ('LIBSQUISH_INCLUDE_DIR', 'LIBSQUISH_LIBRARY', 'SDL2MAIN_LIBRARY', 'SDL2_IMAGE_INCLUDE_DIR', 'SDL2_IMAGE_LIBRARY', 'SDL2_INCLUDE_DIR', 'SDL2_LIBRARY', 'SDL2_MIXER_INCLUDE_DIR', 'SDL2_MIXER_LIBRARY', 'SDL2_TTF_INCLUDE_DIR', 'SDL2_TTF_LIBRARY', 'ZLIB_INCLUDE_DIR', 'ZLIB_LIBRARY_RELEASE', 'luajit_INCLUDE_DIR', 'luajit_LIBRARY', 'minizip_INCLUDE_DIR', 'minizip_LIBRARY'):
            assert entry['value'].startswith('/usr/')
            command.append('-D' + key + ':' + entry['kind'] + '=' + str(sysroot / entry['value'].lstrip('/')))
    # Compiler relocation is explicit and identical in both arms. This changes
    # search paths from the old epoch, never the optimization flags or factor.
    flags = '-B' + str(sysroot / 'usr/bin') + '/ -B' + str(sysroot / 'usr/lib/gcc/x86_64-linux-gnu/11') + '/'
    command += ['-DCMAKE_C_FLAGS=' + flags, '-DCMAKE_CXX_FLAGS=' + flags]
    write(out / 'CONFIGURE_COMMAND.json', command)
    return command

def group_members(pgid):
    result = []
    for path in Path('/proc').glob('[0-9]*/stat'):
        try:
            fields = path.read_text().rsplit(')', 1)[1].split()
            if int(fields[2]) == pgid and fields[0] not in ('Z', 'X'):
                result.append(int(path.parent.name))
        except (FileNotFoundError, ProcessLookupError, ValueError, IndexError):
            continue
    return result

@contextlib.contextmanager
def leases(c, out):
    root = Path(c['resource_locks']['root'])
    handles, entries = [], []
    try:
        for name in c['resource_locks']['order']:
            path = root / name
            assert path.is_file(), 'Never create replacement lock namespace'
            handle = path.open('r+')
            handles.append(handle)
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            st = os.fstat(handle.fileno())
            assert (st.st_dev, st.st_ino) == (path.stat().st_dev, path.stat().st_ino)
            entries.append(dict(path=str(path), fd=handle.fileno(), device=st.st_dev, inode=st.st_ino))
        env = dict(os.environ, HEROES3_LAB_ROOT=str(Path(c['profile_root']) / 'heroes3-ai-lab'), HEROES3_RESOURCE_ROOT=str(root))
        previous = dict(os.environ)
        os.environ.update(env)
        try:
            spec = importlib.util.spec_from_file_location('pair_leases', HERE.parent / 'ubuntu-native-takeover-20261025/leases.py')
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            proof = module.verify(entries, [Path(e['path']) for e in entries])
        finally:
            os.environ.clear()
            os.environ.update(previous)
        write(out / 'LEASES.json', proof)
        yield entries
    finally:
        for handle in reversed(handles):
            fcntl.flock(handle, fcntl.LOCK_UN)
            handle.close()

def run_command(command, env, entries, out):
    env = dict(env, HEROES3_BUILD_LEASES=json.dumps(entries), HEROES3_BUILD_STAGE=str(out))
    wrapped = [sys.executable, str(HERE / 'stage_entry.py'), *command]
    samples, peak_rss = [], 0
    with (out / 'command.log').open('w') as log:
        proc = subprocess.Popen(wrapped, env=env, stdout=log, stderr=subprocess.STDOUT,
                                pass_fds=tuple(e['fd'] for e in entries), start_new_session=True)
        try:
            while proc.poll() is None:
                members = group_members(proc.pid)
                rss = 0
                for pid in members:
                    try:
                        status = (Path('/proc') / str(pid) / 'status').read_text()
                        rss += next((int(line.split()[1]) for line in status.splitlines() if line.startswith('VmRSS:')), 0)
                    except (FileNotFoundError, ProcessLookupError):
                        continue
                peak_rss = max(peak_rss, rss)
                samples.append(dict(monotonic=time.monotonic(), pids=members, process_group_rss_kib=rss,
                                    meminfo=Path('/proc/meminfo').read_text()))
                time.sleep(.5)
            code = proc.wait()
            assert not group_members(proc.pid), 'Owned live descendants remain after command exit'
        finally:
            if group_members(proc.pid):
                os.killpg(proc.pid, signal.SIGTERM)
                deadline = time.monotonic() + 5
                while group_members(proc.pid) and time.monotonic() < deadline:
                    time.sleep(.1)
                if group_members(proc.pid):
                    os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()
                while group_members(proc.pid):
                    time.sleep(.1)
            write(out / 'RESOURCES.json', dict(sampled_peak_process_group_rss_kib=peak_rss,
                  sample_interval_seconds=.5, sample_count=len(samples),
                  child_rusage_maxrss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
                  sampling_limit='Short-lived peaks between samples may be missed; child rusage is not aggregate simultaneous RSS.', samples=samples))
    result = dict(command=command, exit_code=code, inherited_lease_proof_sha256=sha(out / 'CHILD_LEASES.json'))
    write(out / 'COMMAND.json', result)
    assert code == 0, 'Command failed; original attempt log retained'
    return result

def capsule(c, arm, out, command, cert_path):
    scratch = Path(c['scratch_root'])
    dest = Path(c['capsule_root']) / arm
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.mkdir()
    source = manifest(scratch / 'source')
    copy_source(scratch / 'source', dest / 'source-snapshot')
    write(dest / 'build-source-manifest.json', source)
    (dest / 'bin').mkdir()
    for name in NAMES:
        shutil.copy2(scratch / 'build/bin' / name, dest / 'bin' / name)
    shutil.copytree(scratch / 'build/bin/config', dest / 'bin/config', symlinks=False)
    bins = {name: sha(dest / 'bin' / name) for name in NAMES}
    write(dest / 'binary-sha256.json', bins)
    execution = dict(passed=True, arm=arm, native_games=0, optimizer_steps=0,
                     private_scratch_only=True, actual_command=command, stage=str(out))
    write(dest / 'EXECUTION.json', execution)
    configured = json.loads((scratch / 'CONFIGURED.json').read_text())
    configure_stage = Path(configured['stage'])
    configure_command_result = json.loads((configure_stage / 'COMMAND.json').read_text())
    assert configure_command_result['exit_code'] == 0
    attestation = dict(contract_sha256=EXPECTED_CONTRACT, arm=arm,
                       source_manifest_sha256=sha(dest / 'build-source-manifest.json'), binary_sha256=bins,
                       source_link_review={p: e for p, e in source.items() if 'symlink' in e},
                       toolchain_certificate_sha256=sha(cert_path), actual_commands_and_exit_codes=[configure_command_result, command],
                       configured_sha256=sha(scratch / 'CONFIGURED.json'),
                       build_admission_sha256=sha(scratch / 'BUILD_ADMISSION.json'),
                       dependency_closure=configured['dependency_closure'],
                       configure_evidence_sha256={name: sha(configure_stage / name) for name in ('COMMAND.json', 'CHILD_LEASES.json', 'LEASES.json', 'RESOURCES.json', 'ENVIRONMENT.json')},
                       lease_inode_and_inherited_fd_evidence=json.loads((out / 'CHILD_LEASES.json').read_text()),
                       resource_peaks={k: v for k, v in json.loads((out / 'RESOURCES.json').read_text()).items() if k != 'samples'},
                       protected_inputs_before_and_after_equal=True)
    write(dest / 'BUILD_ATTESTATION.json', attestation)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['prepare', 'configure', 'baseline', 'candidate'])
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    def terminate(signum, frame):
        raise InterruptedError('Stage interrupted by signal ' + str(signum))
    signal.signal(signal.SIGTERM, terminate)
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    c = inputs()
    (out / 'driver-snapshot').mkdir()
    for path in (Path(__file__), HERE / 'stage_entry.py', CONTRACT_PATH):
        shutil.copyfile(path, out / 'driver-snapshot' / path.name)
    write(out / 'DRIVER_SHA256.json', {p.name: sha(p) for p in (out / 'driver-snapshot').iterdir()})
    before = protection(c)
    write(out / 'PROTECTED_BEFORE.json', before)
    result = dict(passed=False, action=args.action, native_games=0, optimizer_steps=0)
    try:
        if args.action == 'prepare':
            prepare(c, out)
        else:
            scratch = Path(c['scratch_root'])
            assert json.loads((scratch / 'PREPARED.json').read_text())['contract_sha256'] == EXPECTED_CONTRACT
            env, cert_path = environment(c)
            closure_path = Path(c['toolchain_root']) / 'TARGET_DEPENDENCY_CLOSURE.json'
            # Configuration may discover missing package metadata before target
            # closure is finished. Such an exploratory graph cannot admit builds.
            closure = dependency_closure(c) if closure_path.exists() else None
            if args.action != 'configure':
                assert closure is not None, 'Complete target closure required for compilation'
            shutil.copyfile(cert_path, out / 'TOOLCHAIN_CERTIFICATE.json')
            write(out / 'ENVIRONMENT.json', env)
            with leases(c, out) as entries:
                if args.action == 'configure':
                    assert manifest(scratch / 'source') == json.loads((scratch / 'BASELINE_SOURCE.json').read_text())
                    command = configure_command(c, out)
                else:
                    assert (scratch / 'build/build.ninja').is_file()
                    configured = json.loads((scratch / 'CONFIGURED.json').read_text())
                    assert configured['environment_sha256'] == sha(out / 'ENVIRONMENT.json'), 'Compile environment changed since configuration'
                    assert configured['toolchain_certificate_sha256'] == sha(cert_path), 'Reconfigure after toolchain certificate changes'
                    assert configured['dependency_closure'] == closure, 'Target closure changed after configuration'
                    build_admission(c, configured)
                    if args.action == 'baseline':
                        assert manifest(scratch / 'source') == json.loads((scratch / 'BASELINE_SOURCE.json').read_text())
                    else:
                        baseline = verify_capsule(c, 'baseline')
                        assert manifest(scratch / 'source') == json.loads((baseline / 'build-source-manifest.json').read_text())
                        set_payload(c, 'candidate')
                        candidate_source = manifest(scratch / 'source')
                        baseline_source = json.loads((baseline / 'build-source-manifest.json').read_text())
                        changed = {p for p in set(candidate_source) | set(baseline_source) if candidate_source.get(p) != baseline_source.get(p)}
                        assert changed == {c['only_arm_source_difference']}
                    command = [str(Path(c['toolchain_root']) / 'sysroot/usr/bin/ninja'), '-C', str(scratch / 'build'), '-j2', '-v', 'vcmiclient', 'vcmiserver']
                actual = run_command(command, env, entries, out)
                assert sha(cert_path) == sha(out / 'TOOLCHAIN_CERTIFICATE.json'), 'Toolchain certificate changed during command'
                if closure is not None:
                    assert dependency_closure(c) == closure, 'Target dependency input changed during command'
                if args.action == 'configure':
                    write(scratch / 'CONFIGURED.json', dict(stage=str(out), command=actual,
                          environment_sha256=sha(out / 'ENVIRONMENT.json'), toolchain_certificate_sha256=sha(cert_path), dependency_closure=closure))
                after = protection(c)
                assert before == after, 'Protected input changed during stage'
                if args.action in ('baseline', 'candidate'):
                    assert 'CDirectorAI.cpp' in (out / 'command.log').read_text(errors='replace'), 'Director compilation not observed'
                    capsule(c, args.action, out, actual, cert_path)
        result['passed'] = True
    except BaseException as error:
        result.update(error=repr(error), traceback=traceback.format_exc())
    finally:
        after = protection(c)
        write(out / 'PROTECTED_AFTER.json', after)
        result['protected_inputs_before_and_after_equal'] = before == after
        result['passed'] = result['passed'] and before == after
        write(out / 'RESULT.json', result)
    print(json.dumps(result, indent=2))
    return 0 if result['passed'] else 1

if __name__ == '__main__':
    raise SystemExit(main())
