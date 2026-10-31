"""Explicit capsule identity / process evidence; importing never builds or runs."""
from contextlib import contextmanager
import fcntl,hashlib,json,os
from pathlib import Path

LAB=Path('/root/heroes3-ai-lab')
PROC=Path('/proc')
RUNTIME_ASSET_LINKS={f'data/{name}':f'/root/heroes3-ai-lab/data/vcmi/{name}' for name in ('Data','Maps','Mods')}
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path,value):Path(path).write_text(json.dumps(value,indent=2))
_mapped_hash_cache={}
def mapped_sha(path):
    stat=Path(path).stat();key=(str(path),stat.st_dev,stat.st_ino,stat.st_size,stat.st_mtime_ns,stat.st_ctime_ns)
    if key not in _mapped_hash_cache:_mapped_hash_cache[key]=sha(path)
    return _mapped_hash_cache[key]

@contextmanager
def idle_locks():
    """Always GPU then pool, nonblocking; release first if second is busy."""
    handles=[]
    try:
        for name in ('.gpu-learner-lock','.pool-lock'):
            handle=(LAB/'evaluations'/name).open('a+')
            handles.append(handle)
            try:fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:raise RuntimeError('Resource busy: '+name+'; no native mutation or launch authorized by elapsed time')
        yield
    finally:
        for handle in reversed(handles):handle.close()

def source_manifest(root):
    """Every source-tree file, excluding Git metadata; symlinks recorded explicitly."""
    root=Path(root);result={}
    for folder,dirs,names in os.walk(root,followlinks=False):
        dirs[:]=sorted(d for d in dirs if d!='.git')
        for name in sorted(dirs+names):
            path=Path(folder)/name;relative=str(path.relative_to(root))
            if path.is_symlink():
                result[relative]={'symlink':os.readlink(path),'directory':path.is_dir()}
                if relative in RUNTIME_ASSET_LINKS and os.readlink(path)==RUNTIME_ASSET_LINKS[relative] and path.is_dir():
                    result[relative]['classification']='fixed_runtime_asset_link'
                if path.is_file():result[relative].update(target_sha256=sha(path),bytes=path.stat().st_size)
            elif path.is_file():result[relative]={'sha256':sha(path),'bytes':path.stat().st_size}
    return result

def validate_source_links(manifest):
    """Only three exact noncompiled runtime-asset directories are exempt."""
    for relative,info in manifest.items():
        if 'symlink' not in info:continue
        if info.get('classification')=='fixed_runtime_asset_link':
            assert info.get('directory') and relative in RUNTIME_ASSET_LINKS and info['symlink']==RUNTIME_ASSET_LINKS[relative], 'Wrong runtime asset symlink target'
        else:
            assert not info.get('directory') and 'target_sha256' in info,'Unknown external source-directory or dangling link: '+relative
            assert relative not in RUNTIME_ASSET_LINKS,'Runtime asset link target differs from fixed target'
    return {p:info for p,info in manifest.items() if info.get('classification')=='fixed_runtime_asset_link'}

def loaded_evidence(pid,bin_dir):
    """Record actual exe and each libvcmi mapping path/inode/hash, not guessed loader paths."""
    proc=PROC/str(pid);bin_dir=Path(bin_dir).resolve()
    try:
        executable=(proc/'exe').resolve(strict=True)
        if executable.name not in ('vcmiclient','vcmiserver'):return None
        expected_exe=bin_dir/executable.name
        evidence={'pid':pid,'executable':str(executable),'executable_sha256':mapped_sha(executable),
            'executable_matches_capsule':executable==expected_exe.resolve() and mapped_sha(executable)==mapped_sha(expected_exe),'libraries':[]}
        seen=set()
        for line in (proc/'maps').read_text().splitlines():
            fields=line.split(None,5)
            if len(fields)!=6 or '/libvcmi.so' not in fields[5]:continue
            if fields[5] in seen:continue
            seen.add(fields[5])
            target=Path(fields[5]);expected=(bin_dir/'libvcmi.so').resolve()
            item={'maps_line':line,'path':str(target),'deleted':fields[5].endswith(' (deleted)')}
            if not item['deleted'] and target.is_file():
                stat=target.stat();major,minor=(int(x,16) for x in fields[3].split(':'))
                item.update(sha256=mapped_sha(target),inode_matches=int(fields[4])==stat.st_ino,
                    device_matches=major==os.major(stat.st_dev) and minor==os.minor(stat.st_dev),
                    expected_path=str(expected),path_matches=target.resolve()==expected,
                    expected_sha256=mapped_sha(expected))
                item['valid']=all((item['inode_matches'],item['device_matches'],item['path_matches'],item['sha256']==item['expected_sha256']))
            else:item['valid']=False
            evidence['libraries'].append(item)
        evidence['valid']=evidence['executable_matches_capsule'] and bool(evidence['libraries']) and all(e['valid'] for e in evidence['libraries'])
        evidence['run_server_threads']=[]
        for comm in (proc/'task').glob('*/comm'):
            try:
                name=comm.read_text().strip()
                if name=='runServer':evidence['run_server_threads'].append({'tid':int(comm.parent.name),'comm':name,'proc_comm_path':str(comm)})
            except (FileNotFoundError,ProcessLookupError,PermissionError):pass
        return evidence
    except (ProcessLookupError,FileNotFoundError,PermissionError):return None

def session_evidence(session,bin_dir):
    results=[]
    for proc in PROC.iterdir():
        if not proc.name.isdigit():continue
        try:
            if os.getsid(int(proc.name))!=session:continue
            evidence=loaded_evidence(int(proc.name),bin_dir)
            if evidence:results.append(evidence)
        except (ProcessLookupError,PermissionError):pass
    return results

def thread_server_gate(observations,log,use_process):
    assert use_process is False,'This probe requires explicit server.useProcess=false'
    clients=[o for o in observations if Path(o['executable']).name=='vcmiclient']
    assert clients and all(o['valid'] for o in clients),'Actual client capsule library not proven'
    assert not any(Path(o['executable']).name=='vcmiserver' for o in observations),'Unexpected server process in declared thread mode'
    threads=[{'pid':o['pid'],**thread} for o in clients for thread in o.get('run_server_threads',[]) if thread['comm']=='runServer']
    assert threads,'Missing actual /proc client runServer thread evidence'
    markers={text:text in log for text in ('CVCMIServer created!','Server gives turn to ')}
    assert all(markers.values()),'Missing native server startup/turn evidence'
    return {'mode':'thread','settings_server_useProcess':False,'client_library_verified':True,'run_server_threads':threads,'native_server_log_markers':markers,'passed':True}

def verify_attestation(capsule,variant):
    capsule=Path(capsule).resolve();att=read_attestation(capsule)
    restored=json.loads((capsule.parent/'EXECUTION.json').read_text())
    assert restored['passed'] and restored['accepted_sources_restored'] and restored['accepted_published_binaries_restored'] and not restored['rebuild_required'],'Accepted build restoration must succeed before capsule may run'
    registered=next(item for item in restored['variants'] if item['variant']==variant)
    assert Path(registered['capsule']).resolve()==capsule and sha(capsule/'BUILD_ATTESTATION.json')==registered['attestation_sha256']
    assert att['variant']==variant and att['build_kind']=='incremental_from_accepted_shared_tree'
    assert att['ninja_exit']==0 and att['director_compile_observed']
    assert sha(capsule/'build.log')==att['build_log_sha256']
    assert sha(capsule/'base-source-manifest.json')==att['base_source_manifest_sha256']
    assert sha(capsule/'build-source-manifest.json')==att['build_source_manifest_sha256']
    for relative,digest in att['artifacts'].items():assert sha(capsule/relative)==digest,'Attested capsule input changed: '+relative
    assert all(not (capsule/'bin'/name).is_symlink() for name in ('vcmiclient','vcmiserver','libvcmi.so')),'Capsule binaries must be independent regular copies'
    assert 'CDirectorAI.cpp' in (capsule/'build.log').read_text(errors='replace')
    base=json.loads((capsule/'base-source-manifest.json').read_text())
    compiled=json.loads((capsule/'build-source-manifest.json').read_text())
    validate_source_links(base);validate_source_links(compiled)
    assert set(base)==set(compiled)
    assert {p for p in base if base[p]!=compiled[p]}<={'AI/DirectorAI/CDirectorAI.cpp','AI/DirectorAI/CDirectorAI.h'}
    for name in ('CDirectorAI.cpp','CDirectorAI.h'):
        relative='AI/DirectorAI/'+name
        assert sha(capsule/'source-snapshot'/relative)==compiled[relative]['sha256'],'Compiled/source snapshot identity differs'
    assert att['artifacts']['bin/libvcmi.so']!=att['accepted_artifacts']['libvcmi.so'],'Expected implementation-bearing libvcmi must change for this diagnostic'
    return att

def read_attestation(capsule):return json.loads((Path(capsule)/'BUILD_ATTESTATION.json').read_text())
