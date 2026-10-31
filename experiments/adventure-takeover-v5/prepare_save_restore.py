"""Prepare an isolated --testsave run and inspect native save magic. Never launches VCMI."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import tempfile


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inspect_save(path):
    with path.open('rb') as f:
        head = f.read(32)
    if len(head) < 15 or head[:4] != b'VCMI' or head[8:15] != b'VCMISVG':
        raise ValueError('Not a current native VCMI save: expected VCMI/version/VCMISVG header')
    if path.suffix.lower() != '.vsgm1':
        raise ValueError('This isolated engine only registers .VSGM1 as SAVEGAME')
    return {'path': str(path), 'bytes': path.stat().st_size, 'sha256': sha(path),
            'magic': 'VCMI/version/VCMISVG', 'version_little_endian': int.from_bytes(head[4:8], 'little'),
            'header_only_verified': True, 'full_deserialization_verified': False}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--save-file', required=True, type=Path)
    p.add_argument('--source-run', required=True, type=Path)
    p.add_argument('--red', default='DirectorAI')
    p.add_argument('--blue', default='Nullkiller2')
    p.add_argument('--seconds', type=int, default=180)
    p.add_argument('--inspect-only', action='store_true')
    args = p.parse_args()
    save = args.save_file.resolve()
    inspection = inspect_save(save)
    if args.inspect_only:
        print(json.dumps(inspection, indent=2))
        return
    source = args.source_run.resolve()
    if not (source / 'config/settings.json').is_file():
        raise ValueError('source-run must have its original config/settings.json')
    lab = Path('/root/heroes3-ai-lab')
    binary = lab / 'src/vcmi-adv-build/bin'
    run = Path(tempfile.mkdtemp(prefix='restore-v5-', dir=lab / 'workers/adv-runs'))
    for name in ('config', 'data/vcmi/Maps', 'data/vcmi/config'):
        original = source / name
        if original.exists():
            shutil.copytree(original, run / name, dirs_exist_ok=True)
        else:
            (run / name).mkdir(parents=True, exist_ok=True)
    for name in ('Data', 'Mods'):
        (run / 'data/vcmi' / name).symlink_to(lab / 'data/vcmi' / name)
    saves = run / 'data/vcmi/Saves'
    saves.mkdir(parents=True)
    target = saves / 'takeover-resume-snapshot.vsgm1'
    shutil.copy2(save, target)
    assert sha(target) == inspection['sha256']
    command = [str(binary / 'vcmiclient'), '--headless', '--testsave',
               'Saves/takeover-resume-snapshot', '--nointro', '--disable-video']
    environment = {'LD_LIBRARY_PATH': str(binary), 'SDL_VIDEODRIVER': 'dummy',
                   'SDL_AUDIODRIVER': 'dummy', 'XDG_DATA_HOME': str(run / 'data'),
                   'XDG_CONFIG_HOME': str(run), 'XDG_CACHE_HOME': str(run / 'cache'),
                   'LAB_ADV_AI_0': args.red, 'LAB_ADV_AI_1': args.blue}
    plan = {'prepared_only': True, 'launched': False, 'source_run': str(source),
            'save': inspection, 'run_dir': str(run), 'command': command, 'environment': environment,
            'binary_sha256': {name: sha(binary / name)
                for name in ('vcmiclient', 'vcmiserver', 'libvcmi.so')},
            'limitations': ['Native game state restores; AI C++ private state is reconstructed.',
                'Unpatched NetPacksClient auto-exit only tests testmap, not testsave.',
                'Header check is not full native deserialization.']}
    (run / 'restore-plan.json').write_text(json.dumps(plan, indent=2))
    lines = ['#!/usr/bin/env bash', 'set -euo pipefail',
             '# Prepared only; invocation explicitly starts one native restore under the shared lock.',
             'cd ' + shlex.quote(str(run))]
    lines += ['export ' + key + '=' + shlex.quote(value) for key, value in environment.items()]
    lines += ['exec 9>' + shlex.quote(str(lab / 'evaluations/.pool-lock')), 'flock -x 9',
              'timeout --kill-after=5s ' + str(args.seconds) + 's ' + shlex.join(command)
              + ' > client.log 2>&1']
    launcher = run / 'launch-restore.sh'
    launcher.write_text('\n'.join(lines) + '\n')
    os.chmod(launcher, 0o700)
    print(json.dumps({'prepared_only': True, 'run_dir': str(run), 'launcher': str(launcher),
                      'source_save': inspection, 'native_load_executed': False}, indent=2))


if __name__ == '__main__':
    main()
