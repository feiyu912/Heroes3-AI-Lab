"""New independent GNU11/sysroot prefix from dual-reader certified inputs."""
import hashlib,json,os,posixpath,stat
from pathlib import Path,PurePosixPath
HERE=Path(__file__).resolve().parent
SOURCE=HERE.parent/'ubuntu-native-takeover-20261025/toolchain-inputs'
PREFIX=Path('/home/kaicheng/Documents/Codex/2026-10-24/hello/outputs/Heroes3-Toolchain-GCC11-01')
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def safe_relative(name):
    p=PurePosixPath(name);assert p.is_absolute() and '..' not in p.parts
    return Path(*p.parts[1:])
def main():
    cert=json.loads((SOURCE/'AUDIT.json').read_text());assert cert['passed'] and cert['files']==4186 and cert['links']==85
    assert sha(SOURCE/'FILES.jsonl')==cert['file_journal_sha256'] and sha(SOURCE/'LINKS.jsonl')==cert['link_journal_sha256']
    files=[json.loads(x) for x in (SOURCE/'FILES.jsonl').read_text().splitlines()]
    links=[json.loads(x) for x in (SOURCE/'LINKS.jsonl').read_text().splitlines()]
    assert len(files)==4186 and len(links)==85 and sum(x['size'] for x in files)==177088756
    assert not PREFIX.exists() and not PREFIX.is_symlink()
    PREFIX.mkdir();sysroot=PREFIX/'sysroot';sysroot.mkdir()
    output=[]
    for row in files:
        source=Path(row['output']);assert row['passed'] and not source.is_symlink() and source.is_file()
        assert sha(source)==row['sha256']==row['independent_reader_sha256']==row['readback_sha256']
        target=sysroot/safe_relative(row['path']);target.parent.mkdir(parents=True,exist_ok=True)
        assert not target.exists();target.write_bytes(source.read_bytes())
        os.chmod(target,stat.S_IMODE(row['source_mode']))
        assert sha(target)==row['sha256'] and target.stat().st_ino!=source.stat().st_ino
        output.append(dict(path=str(target.relative_to(PREFIX)),original=row['path'],sha256=row['sha256'],size=row['size']))
    mapped=[]
    for row in links:
        assert row['passed'] and row['target']==row['independent_reader_target']
        target=sysroot/safe_relative(row['path']);target.parent.mkdir(parents=True,exist_ok=True)
        logical=posixpath.normpath(posixpath.join(posixpath.dirname(row['path']),row['target']))
        destination=sysroot/safe_relative(logical)
        relative=os.path.relpath(destination,target.parent)
        assert not target.exists() and not target.is_symlink();target.symlink_to(relative)
        mapped.append(dict(path=str(target.relative_to(PREFIX)),original_target=row['target'],new_target=relative))
    # Linker scripts require the standard interpreter alias; its target is a
    # certified byte-identical old loader, and this alias is new adapter metadata.
    alias=sysroot/'lib64/ld-linux-x86-64.so.2';alias.parent.mkdir(exist_ok=True)
    assert not alias.exists();alias.symlink_to('../usr/lib/x86_64-linux-gnu/ld-linux-x86-64.so.2')
    mapped.append(dict(path=str(alias.relative_to(PREFIX)),new_target=os.readlink(alias),origin='new-prefix-standard-loader-alias'))
    for row in mapped:
        target=PREFIX/row['path'];assert target.resolve(strict=True).is_relative_to(sysroot.resolve())
    runtime=PREFIX/'compiler-runtime';runtime.mkdir()
    families=('libmpc.so','libmpfr.so','libgmp.so','libisl.so','libz.so','libzstd.so','libbfd-','libctf','libopcodes-')
    for path in (sysroot/'usr/lib/x86_64-linux-gnu').iterdir():
        if any(path.name.startswith(n) for n in families) and path.is_file():
            (runtime/path.name).symlink_to(os.path.relpath(path.resolve(),runtime))
    for row in output:assert sha(PREFIX/row['path'])==row['sha256']
    (PREFIX/'FILES.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in output))
    write(PREFIX/'LINKS.json',mapped)
    write(PREFIX/'ASSEMBLY.json',dict(passed=True,files=len(output),bytes=sum(x['size'] for x in files),source_certificate_sha256=sha(SOURCE/'AUDIT.json'),files_sha256=sha(PREFIX/'FILES.jsonl'),links_sha256=sha(PREFIX/'LINKS.json'),independent_inodes=True,old_inputs_unchanged=all(sha(Path(x['output']))==x['sha256'] for x in files),compiler_qualified=False,actual_compilations=0,source_code_sha256=sha(__file__)))
    print(json.dumps(dict(prefix=str(PREFIX),passed=True,files=len(output),bytes=sum(x['size'] for x in files))))
if __name__=='__main__':main()
