"""Explicit locked incremental build and exact V8 restoration; default is read-only plan."""
import argparse,hashlib,json,os,shutil,signal,sys,traceback
from pathlib import Path
HERE=Path(__file__).resolve().parent
SUPPORT=HERE.parent/'multihero-mechanism-probe-v1/build-driver-frozen-03'
sys.path.insert(0,str(SUPPORT))
from capsule_support import source_manifest,validate_source_links,idle_locks,sha,write
from build_capsules import assert_no_native,fresh_write,accepted_loader_resolution,NAMES
import subprocess
LAB=Path('/root/heroes3-ai-lab');SOURCE=LAB/'src/vcmi-adv';BUILD=LAB/'src/vcmi-adv-build'
ACCEPTED=LAB/'evaluations/typed-director-terminal-drain-capsule-03/accepted-backup'
DELETE_ALLOWLIST={'TypedPolicyProtocol.h','SupplyController.h','SupplyAdapter.inc'}
def remove_added(target):
    assert target.parent.resolve()==(SOURCE/'AI/DirectorAI').resolve() and target.name in DELETE_ALLOWLIST
    assert not target.is_symlink()
    target.unlink(missing_ok=True)


def build(tree,log):
    with log.open('w') as output:
        child=subprocess.Popen(['ninja','-C',str(tree),'-j4','-v','vcmiclient','vcmiserver'],stdout=output,stderr=subprocess.STDOUT,start_new_session=True)
        try:code=child.wait()
        except BaseException:
            try:os.killpg(child.pid,signal.SIGTERM)
            except ProcessLookupError:pass
            try:child.wait(timeout=10)
            except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
            raise
    assert code==0,'Build failed; preserve log'
    assert 'CDirectorAI.cpp' in log.read_text(errors='replace'),'Director compilation not observed'

def execute(out):
    manifest=json.loads((HERE/'CANDIDATE_MANIFEST.json').read_text())
    payload={p:(HERE/'candidate'/p).read_bytes() for p in manifest['files']}
    for p,data in payload.items(): assert hashlib.sha256(data).hexdigest()==manifest['files'][p]['candidate_sha256']
    result={'passed':False,'native_runs':0,'optimizer_steps':0,'incremental_from_accepted_shared_tree':True}
    with idle_locks():
        assert_no_native(BUILD/'bin');base=source_manifest(SOURCE);validate_source_links(base)
        assert base==json.loads((ACCEPTED/'base-source-manifest.json').read_text()),'Not original accepted V8 source tree'
        for p,entry in manifest['files'].items():
            target=SOURCE/p
            if entry['baseline_sha256'] is None: assert not target.exists() and not target.is_symlink()
            else: assert sha(target)==entry['baseline_sha256'],p
        original={p:((SOURCE/p).read_bytes(),(SOURCE/p).stat().st_mode) if (SOURCE/p).exists() else None for p in payload}
        original_bins={n:((BUILD/'bin'/n).read_bytes(),(BUILD/'bin'/n).stat().st_mode) for n in NAMES}
        original_hash={n:sha(BUILD/'bin'/n) for n in NAMES}
        assert original_hash==json.loads((ACCEPTED/'binary-sha256.json').read_text()),'Not exact accepted V8 three binaries'
        backup=out/'accepted-backup';backup.mkdir()
        write(backup/'base-source-manifest.json',base);write(backup/'binary-sha256.json',original_hash)
        for p,value in original.items():
            if value is not None:
                dest=backup/'source'/p;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(value[0])
        for n,(data,mode) in original_bins.items():(backup/n).write_bytes(data)
        handlers={s:signal.getsignal(s) for s in (signal.SIGTERM,signal.SIGINT)}
        def interrupt(sig,frame): raise InterruptedError('Build interrupted '+str(sig))
        for s in handlers:signal.signal(s,interrupt)
        mutated=False
        try:
            mutated=True
            for p,data in payload.items():fresh_write(SOURCE/p,data,original[p][1] if original[p] else 0o644)
            compiled=source_manifest(SOURCE);validate_source_links(compiled)
            changed={p for p in set(base)|set(compiled) if base.get(p)!=compiled.get(p)}
            assert changed<=set(payload)
            write(out/'build-source-manifest.json',compiled)
            for p,data in payload.items():
                dest=out/'source-snapshot'/p;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
            build(BUILD,out/'build.log')
            assert source_manifest(SOURCE)==compiled
            bins=out/'bin';bins.mkdir()
            for n in NAMES:shutil.copy2(BUILD/'bin'/n,bins/n)
            shutil.copytree(BUILD/'bin/config',bins/'config')
            assert sha(bins/'libvcmi.so')!=original_hash['libvcmi.so']
            result['candidate_artifacts']={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file() and 'accepted-backup' not in p.parts}
            result['candidate_compiled']=True
        except BaseException as error:
            result.update(error=repr(error),context=traceback.format_exc())
        finally:
            for s in handlers:signal.signal(s,signal.SIG_IGN)
            if mutated:
                try:
                    for p,value in original.items():
                        target=SOURCE/p
                        if value is None:
                            remove_added(target)
                        else:fresh_write(target,*value)
                    assert source_manifest(SOURCE)==base
                    result['accepted_sources_restored']=True
                    build(BUILD,out/'restore-accepted-build.log')
                    result['restored_binary_hashes']={n:sha(BUILD/'bin'/n) for n in NAMES}
                    assert result['restored_binary_hashes']==original_hash
                    result['accepted_loader_resolution']=accepted_loader_resolution(BUILD/'bin',out)
                    result['accepted_binaries_restored']=True;result['rebuild_required']=False
                except BaseException as error:
                    result.update(restore_error=repr(error),restore_context=traceback.format_exc(),rebuild_required=True)
                    for p,value in original.items():
                        if value is None:remove_added(SOURCE/p)
                        else:fresh_write(SOURCE/p,*value)
                    for n,value in original_bins.items():fresh_write(BUILD/'bin'/n,*value)
                    result['fallback_binary_hashes']={n:sha(BUILD/'bin'/n) for n in NAMES}
            for s,h in handlers.items():signal.signal(s,h)
            result['passed']=bool(result.get('candidate_compiled') and result.get('accepted_sources_restored') and result.get('accepted_binaries_restored') and not result.get('rebuild_required') and not result.get('error'))
            write(out/'EXECUTION.json',result)
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--execute',action='store_true');args=p.parse_args()
    args.out.mkdir(parents=True,exist_ok=False)
    write(args.out/'PLAN.json',{'execute':args.execute,'driver_sha256':sha(Path(__file__)),'candidate_manifest_sha256':sha(HERE/'CANDIDATE_MANIFEST.json'),
          'lock_order':['gpu learner NB','pool NB'],'native_games':0,'optimizer_steps':0,'restore_requires_recompile':True})
    if not args.execute:return
    try:result=execute(args.out)
    except BaseException as error:
        result={'passed':False,'error':repr(error),'context':traceback.format_exc()};write(args.out/'BLOCKED_OR_FAILED.json',result)
    print(json.dumps({k:v for k,v in result.items() if k!='candidate_artifacts'},indent=2))
    if not result['passed']:raise SystemExit(1)
if __name__=='__main__':main()
