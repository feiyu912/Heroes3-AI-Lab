"""Build a new Ubuntu profile from completed dual-reader source certificates.

Default is validation/plan only. This never starts a native game or optimizer.
All source material stays unchanged; copied files are independent inodes.
"""
import argparse
import hashlib
import json
import os
import posixpath
import shlex
import shutil
import stat
import time
from pathlib import Path, PurePosixPath

HERE = Path(__file__).resolve().parent
TAKEOVER = HERE.parent
PROJECT = TAKEOVER.parent.parent
OUTPUTS = Path('/home/kaicheng/Documents/Codex/2026-10-24/hello/outputs')
MIGRATION = OUTPUTS / 'WSL迁出-20261025/files'
OLD_RUNTIME = OUTPUTS / 'Heroes3-Ubuntu'
RESOURCE_ROOT = MIGRATION / 'root/heroes3-ai-lab/evaluations'
OLD_ROOTS = ('/root/heroes3-ai-lab', '/root/heroes3-ai-lab-events-v2')


def sha(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def json_read(path):
    return json.loads(Path(path).read_text())


def load_certificate(folder, stage, count):
    cert_path = folder / 'AUDIT.json'
    cert = json_read(cert_path)
    journal = folder / 'FILES.jsonl'
    assert cert['passed'] is True and cert['stage'] == stage
    assert cert['files'] == count and cert['errors'] == []
    assert cert['source_read_only_and_metadata_unchanged'] is True
    assert sha(journal) == cert['journal_sha256'], 'Certificate journal changed'
    records = [json.loads(line) for line in journal.read_text().splitlines()]
    assert len(records) == count and len({r['path'] for r in records}) == count
    for row in records:
        assert row['passed'] is True
        assert row['sha256'] == row['independent_reader_sha256']
        if 'expected_sha256' in row:
            assert row['sha256'] == row['expected_sha256']
        assert type(row['size']) is int and row['size'] >= 0
    return cert, records, {str(cert_path): sha(cert_path), str(journal): sha(journal)}


def under(path, root):
    return path == root or path.startswith(root + '/')


def relative_original(path):
    p = PurePosixPath(path)
    assert p.is_absolute() and '..' not in p.parts
    assert any(under(path, root) and path != root for root in OLD_ROOTS), path
    return Path(*p.parts[2:])


def source_for(row, migration, repair):
    original = row['path']
    normal = migration / original.lstrip('/')
    candidates = [Path(row['repaired_copy'])] if row.get('repaired_copy') else []
    candidates += [normal, repair / original.lstrip('/')]
    checked = []
    for path in dict.fromkeys(candidates):
        if not path.exists() or path.is_symlink():
            continue
        if not stat.S_ISREG(path.stat().st_mode):
            continue
        checked.append(str(path))
        if path.stat().st_size == row['size'] and sha(path) == row['sha256']:
            return path
    raise AssertionError('No source copy matches independently read bytes: ' + original + ' ' + str(checked))


def ensure_parent(path, root):
    assert path.is_relative_to(root) and path != root
    root.mkdir(exist_ok=True)
    assert not root.is_symlink()
    current = root
    for part in path.relative_to(root).parts[:-1]:
        current = current / part
        assert not current.is_symlink(), 'Refuse symlink output ancestor'
        current.mkdir(exist_ok=True)
        assert current.is_dir()
    assert not path.exists() and not path.is_symlink(), 'Refuse any output overwrite'


def copy_verified(source, destination, digest, size, root):
    assert not source.is_symlink() and stat.S_ISREG(source.stat().st_mode)
    before = source.stat()
    ensure_parent(destination, root)
    value = hashlib.sha256()
    amount = 0
    descriptor = os.open(source, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(descriptor, 'rb') as src, destination.open('xb') as dst:
        for block in iter(lambda: src.read(1024 * 1024), b''):
            value.update(block)
            amount += len(block)
            dst.write(block)
    assert value.hexdigest() == digest and amount == size, 'Input changed during copy'
    os.chmod(destination, stat.S_IMODE(before.st_mode))
    assert sha(destination) == digest and destination.stat().st_size == size
    after = source.stat()
    assert (before.st_size, before.st_mtime_ns, before.st_ino) == (after.st_size, after.st_mtime_ns, after.st_ino)
    assert (destination.stat().st_dev, destination.stat().st_ino) != (after.st_dev, after.st_ino)


def map_target(original_link, target, profile, project):
    absolute = target if target.startswith('/') else posixpath.normpath(posixpath.join(posixpath.dirname(original_link), target))
    for old, new in ((OLD_ROOTS[0], profile / 'heroes3-ai-lab'), (OLD_ROOTS[1], profile / 'heroes3-ai-lab-events-v2'),
                     ('/mnt/g/Heroes3-AI-Lab', project)):
        if under(absolute, old):
            return str(new / absolute.removeprefix(old).lstrip('/')), True
    return target, False


def collect_symlinks(migration):
    result = []
    for original_root in OLD_ROOTS:
        root = migration / original_root.lstrip('/')
        assert root.is_dir() and not root.is_symlink()
        for folder, dirs, files in os.walk(root, followlinks=False):
            for name in dirs + files:
                path = Path(folder) / name
                if path.is_symlink():
                    original = '/' + str(path.relative_to(migration))
                    result.append(dict(path=original, source=str(path), target=os.readlink(path)))
    return result


WORKER_SOURCE = '''"""Prepare only isolated profile worker data/config/cache; never source trees."""
import json, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parent
worker = pathlib.Path(sys.argv[1]).resolve()
assert worker.is_relative_to(ROOT / 'workers') and worker != ROOT / 'workers'
data = worker / 'data/vcmi'
config = data / 'config'
config.mkdir(parents=True, exist_ok=True)
for name in ('Data', 'Maps', 'Mods'):
    target = ROOT / 'game-assets/vcmi' / name
    link = data / name
    if not link.exists() and not link.is_symlink():
        link.symlink_to(target, target_is_directory=True)
    assert link.is_symlink() and link.resolve(strict=True) == target.resolve(strict=True)
values = {'modSettings.json': {'activePreset': 'default', 'presets': {'default': {'mods': ['core', 'vcmi', 'ml'], 'settings': {}}}},
          'settings.json': {'mods': {'validation': 'off'}, 'general': {'music': 0, 'sound': 0}},
          'persistentStorage.json': {}, 'keyBindingsConfig.json': {}}
for name, value in values.items():
    path = config / name
    assert not path.is_symlink()
    if not path.exists():
        path.write_text(json.dumps(value))
(worker / 'config').mkdir(exist_ok=True)
(worker / 'cache').mkdir(exist_ok=True)
'''


def env_source(profile, venv, project, venv_certificate, venv_certificate_sha256):
    runtime = profile / 'runtime'
    lab = profile / 'heroes3-ai-lab'
    fixed = dict(HEROES3_LAB_ROOT=lab, HEROES3_EVENTS_ROOT=profile / 'heroes3-ai-lab-events-v2',
                 HEROES3_PROJECT_ROOT=project, HEROES3_RUNTIME_ROOT=runtime,
                 HEROES3_RESOURCE_ROOT=RESOURCE_ROOT, LAB_PYTHON=venv / 'bin/python',
                 HEROES3_QUAL_LAB_ROOT=lab, HEROES3_QUAL_RUNTIME_ROOT=runtime)
    text = '# Generated profile-local environment. No global path or Python changes.\n'
    text += 'if [[ $(sha256sum -- ' + shlex.quote(str(venv_certificate)) + ' | cut -d " " -f1) != ' + shlex.quote(venv_certificate_sha256) + ' ]]; then\n'
    text += "  printf '%s\\n' 'Qualified Python environment certificate changed; stop and re-audit' >&2; return 2\nfi\n"
    text += ''.join('export ' + key + '=' + shlex.quote(str(value)) + '\n' for key, value in fixed.items())
    text += '''case "${HEROES3_ENGINE:-battle}" in
  battle) export HEROES3_NATIVE_BIN="$HEROES3_RUNTIME_ROOT/engine-battle" ;;
  strategic) export HEROES3_NATIVE_BIN="$HEROES3_RUNTIME_ROOT/engine-strategic" ;;
  *) printf '%s\\n' 'HEROES3_ENGINE must be battle or strategic' >&2; return 2 ;;
esac
export LD_LIBRARY_PATH="$HEROES3_NATIVE_BIN:$HEROES3_RUNTIME_ROOT/runtime-libs:$HEROES3_LAB_ROOT/onnxruntime/lib"
export LD_PRELOAD="$HEROES3_RUNTIME_ROOT/native-paths.so"
export PYTHONPATH="$HEROES3_LAB_ROOT/src/gym:$HEROES3_PROJECT_ROOT/research"
export SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
'''
    return text


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--full-certificate', type=Path, default=TAKEOVER / 'evidence-review/reextract-full_migrated_lab_files')
    parser.add_argument('--critical-certificate', type=Path, default=TAKEOVER / 'evidence-review/reextract-critical21')
    parser.add_argument('--runtime-certificate', type=Path, default=TAKEOVER / 'evidence-review/reextract-runtime_libraries')
    parser.add_argument('--migration-files', type=Path, default=MIGRATION)
    parser.add_argument('--repair-files', type=Path, default=TAKEOVER / 'verified-repair')
    parser.add_argument('--venv', type=Path, required=True)
    parser.add_argument('--venv-certificate', type=Path, required=True)
    parser.add_argument('--source-restore-certificate', type=Path, default=TAKEOVER / 'migration-repair-source/RESTORE.json')
    parser.add_argument('--project', type=Path, default=PROJECT)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    out = args.out.absolute()
    assert args.out.is_absolute() and not out.exists() and not out.is_symlink()
    assert out == out.resolve(strict=False), 'Profile parent must have no symlink alias or dot traversal'
    for source_root in (args.migration_files, args.repair_files, OLD_RUNTIME, args.project):
        assert not out.is_relative_to(source_root) and not source_root.is_relative_to(out), 'Profile must be separate from every source root'
    assert args.venv.is_dir() and (args.venv / 'bin/python').is_file()
    assert args.venv.is_absolute() and args.venv == args.venv.resolve()
    assert args.venv != OLD_RUNTIME / 'gpu-venv', 'Known damaged migrated environment is not eligible'
    venv_cert = json_read(args.venv_certificate)
    assert venv_cert['passed'] is True and venv_cert['wheel_record_audit_passed'] is True
    assert venv_cert['environment_root'] == str(args.venv) and venv_cert['packages'] == 41
    restore_cert = json_read(args.source_restore_certificate)
    assert restore_cert['passed'] is True and restore_cert['backup_read_only_and_unchanged'] is True
    assert restore_cert['sha256'] == 'f90ad98ddbdc54aeb3d5856f6e5d6764fcfa76750e113624e40af1ede95886bc'
    assert restore_cert['bytes'] == 209994121216
    certs, full_rows, critical_rows, runtime_rows, inputs = [], [], [], [], {str(Path(__file__)): sha(__file__)}
    inputs[str(args.venv_certificate)] = sha(args.venv_certificate)
    inputs[str(args.source_restore_certificate)] = sha(args.source_restore_certificate)
    for folder, stage, count, target in ((args.full_certificate, 'full_migrated_lab_files', 27109, full_rows),
                                       (args.critical_certificate, 'critical21', 21, critical_rows),
                                       (args.runtime_certificate, 'runtime_libraries', 17, runtime_rows)):
        cert, records, bound = load_certificate(folder, stage, count)
        target.extend(records)
        inputs.update(bound)
        certs.append(cert)
    assert len({c['source_exact_backup_restore_certificate_sha256'] for c in certs}) == 1
    assert certs[0]['source_exact_backup_restore_certificate_sha256'] == sha(args.source_restore_certificate)
    unique = {}
    for row in full_rows + critical_rows:
        relative_original(row['path'])
        if row['path'] in unique:
            assert unique[row['path']]['sha256'] == row['sha256'] and unique[row['path']]['size'] == row['size']
            if row.get('repaired_copy'):
                unique[row['path']] = row
        else:
            unique[row['path']] = row
    selected = [(row, source_for(row, args.migration_files, args.repair_files)) for row in unique.values()]
    runtime_selected = []
    for row in runtime_rows:
        assert str(PurePosixPath(row['path']).parent) == '/usr/lib/x86_64-linux-gnu'
        runtime_selected.append((row, source_for(row, args.migration_files, args.repair_files)))
    observed_links = collect_symlinks(args.migration_files)
    shim_inputs = {str(OLD_RUNTIME / name): sha(OLD_RUNTIME / name) for name in ('native-paths.c', 'native-paths.so')}
    inputs.update(shim_inputs)
    required_bytes = sum(r['size'] for r in unique.values()) + sum(r['size'] for r in runtime_rows)
    parent = out.parent
    assert parent.is_dir()
    assert shutil.disk_usage(parent).free > required_bytes + 2 * 1024**3
    plan = dict(profile=str(out), source_files=len(unique), source_bytes=required_bytes,
                copied_sources='independent files, no hardlinks', runtime_libraries=17,
                observed_symlinks=len(observed_links), canonical_resource_root=str(RESOURCE_ROOT),
                input_sha256=inputs, execution_requested=args.execute, native_games=0, GPU_operations=0, optimizer_steps=0)
    print(json.dumps(plan, ensure_ascii=False, indent=2), flush=True)
    if not args.execute:
        return 0
    out.mkdir(exist_ok=False)
    runtime = out / 'runtime'
    lab = out / 'heroes3-ai-lab'
    events = out / 'heroes3-ai-lab-events-v2'
    entries = []
    links = []
    started = time.monotonic()
    result = dict(passed=False, plan=plan, native_games=0, GPU_operations=0, optimizer_steps=0)
    try:
        (out / 'PLAN.json').write_text(json.dumps(plan, ensure_ascii=False, indent=2) + '\n')
        for row, source in selected:
            destination = out / relative_original(row['path'])
            copy_verified(source, destination, row['sha256'], row['size'], out)
            entries.append(dict(path=str(destination.relative_to(out)), original=row['path'],
                sha256=row['sha256'], size=row['size'], source=str(source), origin='dual-reader-source'))
        for observed in observed_links:
            destination = out / relative_original(observed['path'])
            rewritten, mapped = map_target(observed['path'], observed['target'], out, args.project)
            ensure_parent(destination, out)
            destination.symlink_to(rewritten)
            links.append(dict(path=str(destination.relative_to(out)), old_target=observed['target'],
                new_target=rewritten, mapped=mapped, provenance='observed migration symlink; not independently re-read from VHDX'))
        for directory in (runtime / 'workers', runtime / 'runtime-libs', runtime / 'game-assets/vcmi', out / 'runs'):
            directory.mkdir(parents=True, exist_ok=True)
        for label, engine_source in (('battle', lab / 'src/gym/vcmi/rel/bin'), ('strategic', lab / 'src/vcmi-adv-build/bin')):
            engine = runtime / ('engine-' + label)
            engine.mkdir()
            for source in engine_source.iterdir():
                if source.is_file() and not source.is_symlink() and (source.suffix == '.so' or source.name in ('vcmiclient', 'vcmiserver')):
                    digest = sha(source)
                    destination = engine / source.name
                    copy_verified(source, destination, digest, source.stat().st_size, out)
                    entries.append(dict(path=str(destination.relative_to(out)), original=str(source.relative_to(out)), sha256=digest,
                        size=destination.stat().st_size, origin='verified-profile-engine-copy'))
            resource_source = lab / ('src/gym/vcmi' if label == 'battle' else 'src/vcmi-adv')
            for name in ('config', 'scripts', 'data', 'Mods'):
                target = resource_source / name
                if target.is_dir():
                    (engine / name).symlink_to(target, target_is_directory=True)
                    links.append(dict(path=str((engine / name).relative_to(out)), new_target=str(target), origin='new-profile-engine-resource'))
        for name in ('Data', 'Maps', 'Mods'):
            target = lab / 'data/vcmi' / name
            assert target.is_dir(), 'Missing required runtime data ' + name
            destination = runtime / 'game-assets/vcmi' / name
            destination.symlink_to(target, target_is_directory=True)
            links.append(dict(path=str(destination.relative_to(out)), new_target=str(target), origin='new-profile-game-assets'))
        for row, source in runtime_selected:
            destination = runtime / 'runtime-libs' / Path(row['path']).name
            copy_verified(source, destination, row['sha256'], row['size'], out)
            entries.append(dict(path=str(destination.relative_to(out)), original=row['path'], sha256=row['sha256'],
                size=row['size'], source=str(source), origin='dual-reader-runtime-library'))
        for name in ('native-paths.c', 'native-paths.so'):
            source = OLD_RUNTIME / name
            copy_verified(source, runtime / name, shim_inputs[str(source)], source.stat().st_size, out)
            entries.append(dict(path=str((runtime / name).relative_to(out)), source=str(source), sha256=sha(runtime / name),
                size=(runtime / name).stat().st_size, origin='existing-Ubuntu-process-local-path-shim'))
        # These are convenience links in the new profile only. No system Python is modified.
        for destination in (runtime / 'gpu-venv', lab / 'venv'):
            ensure_parent(destination, out)
            destination.symlink_to(args.venv, target_is_directory=True)
            links.append(dict(path=str(destination.relative_to(out)), new_target=str(args.venv), origin='reused-Ubuntu-reinstalled-venv'))
        generated = {'env.sh': env_source(out, args.venv, args.project, args.venv_certificate, sha(args.venv_certificate)), 'prepare-worker-native.py': WORKER_SOURCE}
        common = '#!/bin/bash\nset -euo pipefail\nulimit -c 0\n'
        generated['python-heroes3.sh'] = common + '''source "$(dirname "${BASH_SOURCE[0]}")/env.sh"
export LAB_WORKER_ROOT="${LAB_WORKER_ROOT:-$HEROES3_RUNTIME_ROOT/workers/manual-${HEROES3_ENGINE:-battle}}"
"$LAB_PYTHON" "$HEROES3_RUNTIME_ROOT/prepare-worker-native.py" "$LAB_WORKER_ROOT"
export XDG_DATA_HOME="$LAB_WORKER_ROOT/data" XDG_CONFIG_HOME="$LAB_WORKER_ROOT/config" XDG_CACHE_HOME="$LAB_WORKER_ROOT/cache"
exec "$LAB_PYTHON" "$@"
'''
        for engine in ('battle', 'strategic'):
            generated['vcmi-' + engine + '.sh'] = common + 'export HEROES3_ENGINE=' + engine + '\n' + '''source "$(dirname "${BASH_SOURCE[0]}")/env.sh"
export LAB_WORKER_ROOT="${LAB_WORKER_ROOT:-$HEROES3_RUNTIME_ROOT/workers/manual-$HEROES3_ENGINE}"
"$LAB_PYTHON" "$HEROES3_RUNTIME_ROOT/prepare-worker-native.py" "$LAB_WORKER_ROOT"
export XDG_DATA_HOME="$LAB_WORKER_ROOT/data" XDG_CONFIG_HOME="$LAB_WORKER_ROOT/config" XDG_CACHE_HOME="$LAB_WORKER_ROOT/cache"
exec "$HEROES3_NATIVE_BIN/vcmiclient" "$@"
'''
        for name, content in generated.items():
            destination = runtime / name
            ensure_parent(destination, out)
            destination.write_text(content)
            destination.chmod(0o755 if name.endswith('.sh') else 0o644)
            entries.append(dict(path=str(destination.relative_to(out)), sha256=sha(destination), size=destination.stat().st_size,
                origin='generated-profile-adapter', builder_sha256=sha(__file__)))
        for row in entries:
            path = out / row['path']
            assert not path.is_symlink() and sha(path) == row['sha256'] and path.stat().st_size == row['size']
        unresolved = []
        for row in links:
            path = out / row['path']
            try:
                row['resolved_exists'] = path.exists()
            except OSError as exc:
                row.update(resolved_exists=False, resolution_error=repr(exc))
            if not row['resolved_exists']:
                unresolved.append(row)
        assert all(sha(source) == row['sha256'] for row, source in selected + runtime_selected)
        assert all(sha(path) == digest for path, digest in inputs.items())
        for row in observed_links:
            assert os.readlink(row['source']) == row['target']
        manifest_path = out / 'BUILD_MANIFEST.jsonl'
        manifest_path.write_text(''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in entries))
        (out / 'SYMLINKS.json').write_text(json.dumps(links, ensure_ascii=False, indent=2) + '\n')
        result.update(passed=True, copied_source_files=len(unique), runtime_library_files=17, checked_output_files=len(entries),
            output_manifest_sha256=sha(manifest_path), symlink_report_sha256=sha(out / 'SYMLINKS.json'),
            unresolved_symlinks=unresolved, all_output_file_bytes_match_declared_origins=True, original_sources_unchanged=True,
            independent_file_inodes=True, historical_absolute_links_changed_only_in_new_profile=True,
            complete_native_runtime_qualified=False, full_game_or_strength_evaluation=False,
            symlink_metadata_scope='Observed migrated links, mapped lexically only for the two lab roots and project; symlink metadata was not covered by source regular-file reader certificates.',
            venv_scope='Explicit new environment gated by a 41-package wheel RECORD audit certificate, pinned at build and launcher entry. No claim its whole tree matches old VHDX, or that a dated audit proves future payload immutability.',
            venv_certificate_sha256=sha(args.venv_certificate),
            canonical_resource_root=str(RESOURCE_ROOT), seconds=time.monotonic() - started)
    except BaseException as exc:
        result.update(error=type(exc).__name__ + ': ' + str(exc), seconds=time.monotonic() - started)
        raise
    finally:
        (out / 'AUDIT.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
