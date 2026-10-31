"""Read-only parser-cache prototype; original auditor and every gate stay intact."""
import argparse,functools,hashlib,importlib.util,json,sys,time
from pathlib import Path
ROOT=Path('/mnt/g/Heroes3-AI-Lab')
PACKAGE=ROOT/'experiments/strategic-active-opponent-curriculum-v2-20261023'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--cell',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False,parents=True)
    sys.path.insert(0,str(PACKAGE))
    original=importlib.util.spec_from_file_location
    holder={}
    class CacheLoader:
        def __init__(self,loader):self.loader=loader
        def create_module(self,spec):return self.loader.create_module(spec)
        def exec_module(self,module):
            self.loader.exec_module(module)
            parser=module.log_records
            module.log_records=functools.lru_cache(maxsize=8)(parser)
            holder['cache']=module.log_records
    def spec(name,path,*args,**kwargs):
        result=original(name,path,*args,**kwargs)
        if name=='_actual_recruit_raw_auditor':result.loader=CacheLoader(result.loader)
        return result
    importlib.util.spec_from_file_location=spec
    entry=original('_unchanged_calibration_audit_entry',PACKAGE/'audit_game.py')
    module=importlib.util.module_from_spec(entry);entry.loader.exec_module(module)
    sys.argv=[str(PACKAGE/'audit_game.py'),str(a.cell/'native'),str(a.out/'raw')]
    start=time.monotonic();module.main();elapsed=time.monotonic()-start
    fresh=json.loads((a.out/'raw/AUDIT.json').read_text());old=json.loads((a.cell/'raw-audit/AUDIT.json').read_text())
    assert fresh==old,'Cache must preserve complete original audit values'
    info=holder['cache'].cache_info();assert info.hits>0 and info.misses>0
    result=dict(passed=True,complete_report_equal=True,cell=str(a.cell),cache_hits=info.hits,cache_misses=info.misses,
        cached_audit_wall_seconds=elapsed,source_sha256=sha(__file__),original_entry_sha256=sha(PACKAGE/'audit_game.py'),
        original_auditor_modified=False,original_running_process_modified=False,all_original_checks_executed=True,
        prototype_only=True,native_games=0,GPU_operations=0,optimizer_steps=0)
    (a.out/'EQUIVALENCE.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
if __name__=='__main__':main()
