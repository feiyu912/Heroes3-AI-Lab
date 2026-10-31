"""Preserve the complete failed paired attempt before any next fixture."""
from pathlib import Path
import hashlib,json,shutil
HERE=Path(__file__).resolve().parent
LAB=Path('/root/heroes3-ai-lab/evaluations')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    out=HERE/'native-evidence-02';out.mkdir(exist_ok=False)
    report={'engineering_pass':False,'scheduler_qualified':False,'optimizer_steps':0,'final_test_touched':False,'runs':{}}
    for arm in ('baseline','filtered'):
        raw=LAB/f'multihero-scheduler-garrison-{arm}-02'
        dest=out/arm;dest.mkdir()
        files={}
        for name in ('probe.jsonl','strategy-trace.jsonl','client.log','plan.json','execution.json','AUDIT_SCHEDULER.json'):
            shutil.copy2(raw/name,dest/name)
            assert sha(raw/name)==sha(dest/name)
            files[name]=sha(dest/name)
        audit=json.loads((raw/'AUDIT_SCHEDULER.json').read_text())
        report['runs'][arm]={'raw':str(raw),'sha256':files,'blockers':audit['blockers'],'strict_checks':audit['strict_checks']}
    (out/'ARCHIVE.json').write_text(json.dumps(report,indent=2))
    (HERE/'ENGINEERING_STOP.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({'archived':True,'qualified':False,'runs':2,'optimizer_steps':0}))
if __name__=='__main__':main()
