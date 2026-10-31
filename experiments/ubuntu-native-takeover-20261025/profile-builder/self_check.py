"""Bounded synthetic copy/isolation/certificate checks, no profile build or engine."""
import hashlib
import importlib.util
import json
import pathlib
import subprocess
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('profile_builder_under_review', HERE / 'build_profile.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def rejects(fn):
    try:
        fn()
    except (AssertionError, FileNotFoundError):
        return True
    raise AssertionError('Invalid input was accepted')


def main():
    checks = {}
    with tempfile.TemporaryDirectory(prefix='heroes-profile-self-check-') as temporary:
        root = pathlib.Path(temporary)
        original = root / 'original.bin'
        original.write_bytes(b'unchanged frozen source fixture\x00\xff')
        digest = builder.sha(original)
        profile = root / 'new-profile'
        profile.mkdir()
        copy = profile / 'engine/copied.bin'
        builder.copy_verified(original, copy, digest, original.stat().st_size, profile)
        assert builder.sha(copy) == digest and copy.stat().st_ino != original.stat().st_ino
        copy.write_bytes(b'future isolated rebuild')
        assert builder.sha(original) == digest
        checks['independent_copy_future_write_preserves_source'] = True
        checks['refuse_overwrite'] = rejects(lambda: builder.copy_verified(original, copy, digest, original.stat().st_size, profile))
        (profile / 'redirect').symlink_to(root)
        checks['refuse_output_symlink_ancestor'] = rejects(lambda: builder.ensure_parent(profile / 'redirect/escape.bin', profile))
        source_link = root / 'source-link'
        source_link.symlink_to(original)
        checks['refuse_symlink_source'] = rejects(lambda: builder.copy_verified(source_link, profile / 'other.bin', digest, original.stat().st_size, profile))
        candidate = root / 'migration/root/heroes3-ai-lab/model.bin'
        candidate.parent.mkdir(parents=True)
        candidate.write_bytes(b'wrong old migration bytes')
        repaired = root / 'repair/root/heroes3-ai-lab/model.bin'
        repaired.parent.mkdir(parents=True)
        repaired.write_bytes(original.read_bytes())
        row = dict(path='/root/heroes3-ai-lab/model.bin', sha256=digest, size=original.stat().st_size)
        assert builder.source_for(row, root / 'migration', root / 'repair') == repaired
        checks['reject_bad_migration_select_corrected_expected_SHA'] = True
        repaired.write_bytes(b'now damaged too')
        checks['reject_all_wrong_source_copies'] = rejects(lambda: builder.source_for(row, root / 'migration', root / 'repair'))
        new_target, mapped = builder.map_target('/root/heroes3-ai-lab/bin/config', '../../heroes3-ai-lab-events-v2/config', profile, root / 'project')
        assert mapped and new_target == str(profile / 'heroes3-ai-lab-events-v2/config')
        checks['relative_cross_lab_target_mapped'] = True
        assert builder.map_target('/root/heroes3-ai-lab/src/link', '/mnt/g/Heroes3-AI-Lab/research', profile, root / 'project') == (str(root / 'project/research'), True)
        checks['project_absolute_target_mapped'] = True
        assert builder.map_target('/root/heroes3-ai-lab/src/link', '/root/heroes3-ai-lab-evil/private', profile, root / 'project') == ('/root/heroes3-ai-lab-evil/private', False)
        checks['prefix_collision_is_external_unchanged'] = True
        cert = root / 'certificate'
        cert.mkdir()
        record = dict(path=row['path'], passed=True, sha256=digest, independent_reader_sha256=digest, size=row['size'])
        journal = cert / 'FILES.jsonl'
        journal.write_text(json.dumps(record) + '\n')
        (cert / 'AUDIT.json').write_text(json.dumps(dict(passed=True, stage='synthetic', files=1, errors=[], source_read_only_and_metadata_unchanged=True, journal_sha256=builder.sha(journal))))
        builder.load_certificate(cert, 'synthetic', 1)
        checks['certificate_requires_stage_count_and_journal_binding'] = rejects(lambda: builder.load_certificate(cert, 'other-stage', 1)) and rejects(lambda: builder.load_certificate(cert, 'synthetic', 2))
        journal.write_text(json.dumps(dict(record, sha256='0' * 64)) + '\n')
        checks['certificate_rejects_tampered_journal'] = rejects(lambda: builder.load_certificate(cert, 'synthetic', 1))
        script = builder.env_source(profile, root / 'qualified venv', root / 'project path', root / 'venv certificate.json', 'a' * 64)
        subprocess.run(['/bin/bash', '-n'], input=script.encode(), check=True)
        compile(builder.WORKER_SOURCE, '<generated-worker-source>', 'exec')
        assert str(builder.RESOURCE_ROOT) in script and 'HEROES3_RESOURCE_ROOT=' in script
        checks['generated_env_syntax_canonical_lock_and_worker_syntax'] = True
    assert all(checks.values())
    result = dict(passed=True, checks=checks, builder_sha256=builder.sha(HERE / 'build_profile.py'),
                  self_check_sha256=builder.sha(__file__), real_profile_built=False, native_games=0, GPU_operations=0,
                  optimizer_steps=0, scope='Synthetic file fixtures and shell syntax only; does not qualify the real VHDX source, new Python environment, native engines or full games.')
    output = HERE / 'SELF_CHECK.json'
    with output.open('x') as stream:
        stream.write(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
