"""Read-only C++ relocation inventory. Never extracts, installs or compiles."""
import collections
import fnmatch
import hashlib
import json
import os
import pathlib
import posixpath
import re
import shutil
import stat
import struct

HERE = pathlib.Path(__file__).resolve().parent
TAKEOVER = HERE.parent
OUTPUTS = pathlib.Path('/home/kaicheng/Documents/Codex/2026-10-24/hello/outputs')
MIGRATION = OUTPUTS / 'WSL迁出-20261025/files'
INVENTORY = OUTPUTS.parent / 'work/wsl-migration/inventory.jsonl'
OLD_BUILD = '/root/heroes3-ai-lab/src/vcmi-adv-build/'


def sha(path):
    h = hashlib.sha256()
    with pathlib.Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def main():
    manifest_path = TAKEOVER / 'evidence-review/reextract-full_migrated_lab_files/FILES.jsonl'
    manifest = {r['path']: r for r in map(json.loads, manifest_path.read_text().splitlines())}
    inputs = {str(manifest_path): sha(manifest_path), str(__file__): sha(__file__)}

    def source(original):
        row = manifest[original]
        file = pathlib.Path(row.get('repaired_copy', str(MIGRATION / original.lstrip('/'))))
        assert sha(file) == row['sha256']
        inputs[str(file)] = row['sha256']
        return file

    cache_path = source(OLD_BUILD + 'CMakeCache.txt')
    cache = {}
    for line in cache_path.read_text().splitlines():
        if line and not line.startswith(('#', '//')) and ':' in line and '=' in line:
            key_type, value = line.split('=', 1)
            key, kind = key_type.split(':', 1)
            cache[key] = dict(kind=kind, value=value)
    compiler_path = source(OLD_BUILD + 'CMakeFiles/3.31.10/CMakeCXXCompiler.cmake')
    compiler_text = compiler_path.read_text()
    assert 'set(CMAKE_CXX_COMPILER_ID "GNU")' in compiler_text
    assert 'set(CMAKE_CXX_COMPILER_VERSION "11.4.0")' in compiler_text
    ninja = source(OLD_BUILD + 'build.ninja').read_text().splitlines()
    director = []
    link = []
    for index, line in enumerate(ninja):
        if line.startswith('build AI/DirectorAI/') and 'CDirectorAI.cpp.o:' in line:
            director = ninja[index:index + 8]
        if line.startswith('build bin/libvcmi.so:'):
            link = ninja[index:index + 10]
    assert director and link
    deps_source = source(OLD_BUILD + '.ninja_deps')
    data = deps_source.read_bytes()
    assert data[:12] == b'# ninjadeps\n' and struct.unpack_from('<I', data, 12)[0] == 4
    offset = 16
    paths = []
    dep_records = 0
    while offset < len(data):
        length, = struct.unpack_from('<I', data, offset)
        offset += 4
        size = length & 0x7fffffff
        assert size % 4 == 0 and offset + size <= len(data)
        record = data[offset:offset + size]
        offset += size
        if length & 0x80000000:
            dep_records += 1
        else:
            checksum, = struct.unpack_from('<I', record, size - 4)
            assert checksum == ((~len(paths)) & 0xffffffff)
            paths.append(record[:-4].rstrip(b'\0').decode())
    headers = sorted({p for p in paths if p.startswith('/usr/include/')})
    assert len(headers) == 3799
    records = {}
    with INVENTORY.open() as stream:
        for line in stream:
            row = json.loads(line)
            path = row['path']
            if path in ('/bin', '/sbin', '/lib', '/lib64') or path.startswith((
                '/usr/bin/', '/usr/include/', '/usr/lib/gcc/x86_64-linux-gnu/11/',
                '/usr/lib/x86_64-linux-gnu/', '/usr/share/pkgconfig/', '/etc/alternatives/')):
                records[path] = row
    inputs[str(INVENTORY)] = sha(INVENTORY)
    selected = {}
    link_paths = {}
    missing = []

    def add(path, why):
        path = posixpath.normpath(path)
        visited = set()
        for _ in range(40):
            assert path not in visited, 'Inventory symlink loop'
            visited.add(path)
            pieces = pathlib.PurePosixPath(path).parts
            changed = False
            for end in range(2, len(pieces) + 1):
                prefix = str(pathlib.PurePosixPath(*pieces[:end]))
                row = records.get(prefix)
                if row and stat.S_ISLNK(row['mode']):
                    link_paths[prefix] = dict(path=prefix, target=row['link'], source_inode=row['inode'], reason=why)
                    target = row['link'] if row['link'].startswith('/') else posixpath.join(posixpath.dirname(prefix), row['link'])
                    path = posixpath.normpath(posixpath.join(target, *pieces[end:]))
                    changed = True
                    break
            if changed:
                continue
            row = records.get(path)
            if not row or not stat.S_ISREG(row['mode']):
                missing.append(dict(path=path, requested=why))
                return
            value = selected.setdefault(path, dict(path=path, source_inode=row['inode'], source_size=row['size'],
                source_mode=row['mode'], reasons=[], expectation='source inventory metadata only; dual-reader payload qualification still required'))
            if why not in value['reasons']:
                value['reasons'].append(why)
            return
        raise AssertionError('Inventory symlink resolution depth exceeded')

    for path in headers:
        add(path, 'exact previously compiled system header from checksummed Ninja v4 path record')
    for path in records:
        if path.startswith('/usr/lib/gcc/x86_64-linux-gnu/11/') and (stat.S_ISREG(records[path]['mode']) or stat.S_ISLNK(records[path]['mode'])):
            add(path, 'GNU11 compiler internal programs/builtin headers/runtime link support')
    names = ('gcc-11', 'g++-11', 'cpp-11', 'gcc-ar-11', 'gcc-ranlib-11', 'gcc-nm-11',
             'as', 'ld', 'ld.bfd', 'ar', 'ranlib', 'nm', 'strip', 'objcopy', 'objdump', 'readelf', 'addr2line', 'ninja')
    for name in names:
        add('/usr/bin/' + name, 'compiler/binutils/Ninja entry point')
    patterns = ('libboost_filesystem.so*', 'libboost_program_options.so*', 'libboost_system.so*',
                'libSDL2*.so*', 'libSDL2main.a', 'libsquish.so*', 'libminizip.so*', 'libz.so*',
                'libtbb*.so*', 'libluajit-5.1.so*', 'libstdc++.so*', 'libgcc_s.so*',
                'libgmp.so*', 'libmpfr.so*', 'libmpc.so*', 'libisl.so*', 'libzstd.so*',
                'libbfd*.so*', 'libopcodes*.so*', 'libctf*.so*', 'libcc1.so*',
                'libc.so*', 'libc_nonshared.a', 'libm.so*', 'libmvec.so*', 'libpthread.a', 'libpthread.so*',
                'libdl.a', 'libdl.so*', 'librt.so*', 'libresolv.so*', 'libanl.so*', 'libutil.so*',
                'ld-linux-x86-64.so*', 'crt*.o', 'Scrt1.o', 'gcrt1.o')
    cmake_prefixes = tuple('/usr/lib/x86_64-linux-gnu/cmake/' + name for name in (
        'Boost-1.74.0/', 'boost_headers-1.74.0/', 'boost_filesystem-1.74.0/',
        'boost_system-1.74.0/', 'boost_program_options-1.74.0/', 'TBB/', 'SDL2/'))
    for path, row in records.items():
        if not (stat.S_ISREG(row['mode']) or stat.S_ISLNK(row['mode'])):
            continue
        if str(pathlib.PurePosixPath(path).parent) == '/usr/lib/x86_64-linux-gnu' and any(fnmatch.fnmatch(pathlib.PurePosixPath(path).name, p) for p in patterns):
            add(path, 'direct link/compiler runtime family; transitive ELF DT_NEEDED closure not yet checked')
        if path.startswith(cmake_prefixes):
            add(path, 'old dependency CMake import metadata')
        if path.startswith(('/usr/lib/x86_64-linux-gnu/pkgconfig/', '/usr/share/pkgconfig/')):
            add(path, 'bounded original pkg-config metadata; avoids host development-library discovery')
    tools = {name: shutil.which(name) for name in ('gcc', 'g++', 'clang', 'clang++', 'cmake', 'ninja', 'make',
                                                   'pkg-config', 'dpkg-deb', 'ar', 'ld', 'readelf', 'strings')}
    header_presence = {path: pathlib.Path(path).exists() for path in ('/usr/include/c++', '/usr/include/boost',
        '/usr/include/SDL2', '/usr/include/tbb', '/usr/include/luajit-2.1', '/usr/include/minizip', '/usr/include/zlib.h')}
    strategic = [r for p, r in manifest.items() if p.startswith(OLD_BUILD)]
    cmake = [r for p, r in manifest.items() if p.startswith('/root/heroes3-ai-lab/python-packages/cmake/')]
    package_file = HERE / 'ORIGINAL_PACKAGE_SET.json'
    assert package_file.is_file()
    inputs[str(package_file)] = sha(package_file)
    plan = dict(passed=not missing, source_ready_plan_only=True, current_system=pathlib.Path('/etc/os-release').read_text(),
        current_tools=tools, current_development_header_presence=header_presence,
        old_compiler=dict(id='GNU', version='11.4.0', dialect='gnu++20', director_build_lines=director,
            link_flags_and_libraries=[l for l in link[1:] if l.strip()], compile_commands_json_was_present=False),
        old_cmake_cache=cache, verified_build_inputs_sha256=inputs,
        old_strategic_build=dict(files=len(strategic), bytes=sum(r['size'] for r in strategic),
            object_files=sum(r['path'].endswith('.o') for r in strategic), precompiled_headers=sum(r['path'].endswith(('.gch', '.pch')) for r in strategic)),
        reusable_cmake_distribution=dict(files=len(cmake), bytes=sum(r['size'] for r in cmake), recorded_version='3.31.10',
            path_in_new_profile='heroes3-ai-lab/python-packages/cmake/data/bin/cmake', executed=False),
        ninja_dependency_paths=dict(nodes=len(paths), dependency_records=dep_records, checksum_validated=True, selected_system_headers=len(headers)),
        source_extraction_candidates=dict(ordinary_files=len(selected), ordinary_file_bytes=sum(r['source_size'] for r in selected.values()),
            symlinks=len(link_paths), missing=missing, files=selected, links=link_paths),
        scope='Metadata-only bounded old-source candidate list. No source payload extracted or qualified for toolchain, no compiler/program invoked, no download/global install/accepted-tree edit. Fresh compiler and transitive library qualification remains necessary.',
        actual_compilations=0, native_games=0, GPU_operations=0, optimizer_steps=0)
    output = HERE / 'TOOLCHAIN_SOURCE_PLAN.json'
    with output.open('x') as stream:
        stream.write(json.dumps(plan, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(dict(passed=not missing, selected_files=len(selected), selected_bytes=sum(r['source_size'] for r in selected.values()),
                         symlinks=len(link_paths), missing=missing, tools=tools), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
