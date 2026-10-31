"""No-overwrite recovery of bounded compiler inputs from the exact old VHDX.

Only reads the original image. It does not install, configure or run tools.
Symlink targets are preserved as certified metadata, never global symlinks.
"""
import argparse
import hashlib
import json
import os
import stat
import sys
import time
from pathlib import Path, PurePosixPath

HERE = Path(__file__).resolve().parent
TAKEOVER = HERE.parent
REVIEW = TAKEOVER / 'evidence-review'
sys.path.insert(0, str(REVIEW))
from bounded_vhdx import BoundedVHDX
from direct_vhdx import DirectReadVHDX
from dissect.extfs.extfs import ExtFS
from reextract_from_source import PathResolver


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def stream_hash(stream):
    h = hashlib.sha256()
    count = 0
    for block in iter(lambda: stream.read(1024 * 1024), b''):
        h.update(block)
        count += len(block)
    return h.hexdigest(), count


def destination(root, original):
    p = PurePosixPath(original)
    assert p.is_absolute() and '..' not in p.parts
    assert p.parts[1] in ('usr', 'lib', 'lib64', 'etc')
    out = root
    for part in p.parts[1:-1]:
        out = out / part
        assert not out.is_symlink()
        out.mkdir(exist_ok=True)
        assert out.is_dir()
    out = out / p.name
    assert not out.exists() and not out.is_symlink()
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    plan_path = HERE / 'TOOLCHAIN_SOURCE_PLAN.json'
    plan = json.loads(plan_path.read_text())
    chosen = plan['source_extraction_candidates']
    assert plan['passed'] and not chosen['missing']
    assert chosen['ordinary_files'] == 4186 and chosen['ordinary_file_bytes'] == 177088756 and chosen['symlinks'] == 85
    assert chosen['ordinary_file_bytes'] < 2 * 1024**3
    image = TAKEOVER / 'migration-repair-source/source.vhdx'
    certificate = image.parent / 'RESTORE.json'
    restored = json.loads(certificate.read_text())
    assert restored['passed'] and restored['backup_read_only_and_unchanged']
    assert restored['sha256'] == 'f90ad98ddbdc54aeb3d5856f6e5d6764fcfa76750e113624e40af1ede95886bc'
    assert image.stat().st_size == restored['bytes'] == 209994121216
    args.out.mkdir(parents=False, exist_ok=False)
    assert not args.out.is_symlink()
    payload = args.out / 'files'
    payload.mkdir()
    before = image.stat()
    code_inputs = {str(p): sha(p) for p in (Path(__file__), REVIEW / 'bounded_vhdx.py', REVIEW / 'direct_vhdx.py',
                                           REVIEW / 'reextract_from_source.py', plan_path, certificate)}
    errors = []
    rows = []
    links = []
    started = time.monotonic()
    result = dict(passed=False, actual_compilations=0, native_games=0, GPU_operations=0, optimizer_steps=0)
    try:
        with image.open('rb') as a, image.open('rb') as b, (args.out / 'FILES.jsonl').open('x') as journal:
            one = ExtFS(BoundedVHDX(a))
            two = ExtFS(DirectReadVHDX(b))
            first_resolver = PathResolver(one)
            second_resolver = PathResolver(two)
            for index, (original, wanted) in enumerate(chosen['files'].items(), 1):
                row = dict(path=original, source_inode=wanted['source_inode'])
                try:
                    assert first_resolver.inode_for(original) == second_resolver.inode_for(original) == wanted['source_inode']
                    node = one.get_inode(wanted['source_inode'])
                    other = two.get_inode(wanted['source_inode'])
                    assert node.filetype == other.filetype == stat.S_IFREG
                    assert node.size == other.size == wanted['source_size']
                    assert node.inode.i_mode == other.inode.i_mode == wanted['source_mode']
                    target = destination(payload, original)
                    with node.open() as source, target.open('xb') as dst:
                        h = hashlib.sha256()
                        size = 0
                        for block in iter(lambda: source.read(1024 * 1024), b''):
                            h.update(block)
                            size += len(block)
                            dst.write(block)
                        dst.flush()
                        os.fsync(dst.fileno())
                    with other.open() as source:
                        independent, second_size = stream_hash(source)
                    assert size == second_size == wanted['source_size'] and h.hexdigest() == independent
                    os.chmod(target, stat.S_IMODE(wanted['source_mode']) & 0o555)
                    readback = sha(target)
                    assert readback == h.hexdigest()
                    row.update(passed=True, sha256=h.hexdigest(), independent_reader_sha256=independent,
                               readback_sha256=readback, size=size, output=str(target), source_mode=wanted['source_mode'],
                               original_path_inode_verified=True)
                except Exception as exc:
                    row.update(passed=False, error=type(exc).__name__ + ': ' + str(exc))
                    errors.append(row)
                rows.append(row)
                journal.write(json.dumps(row, ensure_ascii=False) + '\n')
                journal.flush()
                if index % 250 == 0 or index == len(chosen['files']):
                    progress = dict(files=index, total=len(chosen['files']), errors=len(errors), seconds=time.monotonic() - started)
                    (args.out / 'PROGRESS.json').write_text(json.dumps(progress))
                    print(json.dumps(progress), flush=True)
            with (args.out / 'LINKS.jsonl').open('x') as link_journal:
                for original, wanted in chosen['links'].items():
                    row = dict(path=original, source_inode=wanted['source_inode'])
                    try:
                        assert first_resolver.inode_for(original) == second_resolver.inode_for(original) == wanted['source_inode']
                        node = one.get_inode(wanted['source_inode'])
                        other = two.get_inode(wanted['source_inode'])
                        assert node.filetype == other.filetype == stat.S_IFLNK
                        assert node.link == other.link == wanted['target']
                        row.update(passed=True, target=node.link, independent_reader_target=other.link, original_path_inode_verified=True,
                                   output_symlink_created=False)
                    except Exception as exc:
                        row.update(passed=False, error=type(exc).__name__ + ': ' + str(exc))
                        errors.append(row)
                    links.append(row)
                    link_journal.write(json.dumps(row, ensure_ascii=False) + '\n')
        after = image.stat()
        assert (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns)
        assert all(sha(path) == digest for path, digest in code_inputs.items())
        assert sum(r.get('size', 0) for r in rows if r['passed']) == 177088756
        result.update(passed=not errors and len(rows) == 4186 and len(links) == 85, errors=errors,
            files=len(rows), bytes=sum(r.get('size', 0) for r in rows if r['passed']), links=len(links),
            source_read_only_and_metadata_unchanged=True, source_vhdx_sha256=restored['sha256'],
            inputs_sha256=code_inputs, file_journal_sha256=sha(args.out / 'FILES.jsonl'), link_journal_sha256=sha(args.out / 'LINKS.jsonl'),
            source_payload_two_readers_and_readback_equal=True, symlink_targets_captured_only=True,
            elapsed_seconds=time.monotonic() - started, compiler_or_sysroot_qualified=False,
            scope='Bounded original compiler/header/link-input recovery only. Both independently implemented VHDX payload readers share the same extfs metadata parser. Correct logical paths and inode metadata checked. Link targets saved as metadata, no global or payload symlinks installed. No compiler/native/GPU/optimizer executed; full ELF transitive closure and actual toolchain operation still require qualification.')
    except BaseException as exc:
        result.update(error=type(exc).__name__ + ': ' + str(exc), errors=errors, elapsed_seconds=time.monotonic() - started)
        raise
    finally:
        (args.out / 'AUDIT.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
