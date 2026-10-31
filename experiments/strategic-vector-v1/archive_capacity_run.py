"""Copy completed Linux collection evidence without rewriting recorded absolute paths."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--complete-existing-collection', action='store_true')
    args = parser.parse_args()
    source = args.source.resolve()
    archive = args.archive.resolve()
    if (archive.exists() and not args.complete_existing_collection) or source == archive or source in archive.parents:
        raise ValueError('Archive must be a new independent directory')
    batch = json.loads((source / 'batch.json').read_text())
    if batch['status'] != 'complete_on_policy_batch':
        raise ValueError('Only completed collections can use this archiver')
    if not archive.exists():
        shutil.copytree(source, archive)
    entries = []

    def verify_tree(original, copied, category):
        for path in sorted(original.rglob('*')):
            if path.is_symlink():
                entries.append(dict(category=category, original_absolute_path=str(path),
                                    symbolic_link_target=str(path.readlink()),
                                    archived_as='manifest metadata only; external game assets not dereferenced'))
                continue
            if path.is_file():
                target = copied / path.relative_to(original)
                before = digest(path)
                if digest(target) != before:
                    raise ValueError(f'Archive bytes differ: {path}')
                entries.append(dict(category=category, original_absolute_path=str(path),
                                    archive_relative_path=str(target.relative_to(archive)),
                                    bytes=path.stat().st_size, sha256=before))

    verify_tree(source, archive, 'collection')
    for episode in batch['episodes']:
        native = Path(episode['native']['run_dir']).resolve()
        target = archive / 'native-evidence' / f"env-{episode['episode_index']:03d}"
        shutil.copytree(native, target, ignore=lambda directory,names:
                        [name for name in names if (Path(directory) / name).is_symlink()])
        verify_tree(native, target, 'native')
    report = dict(original_linux_run=str(source), archive=str(archive), verified=True,
                  original_paths_preserved=True, source_retained=True,
                  note='Recorded absolute paths remain Linux originals; regular native evidence files are byte-identical copies. External asset symbolic links are recorded as link metadata without dereferencing.',
                  files=entries)
    (archive / 'ARCHIVE_MANIFEST.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(verified=True, files=len(entries), archive=str(archive))))


if __name__ == '__main__':
    main()
