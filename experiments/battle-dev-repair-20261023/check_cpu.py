"""Recover actual logs + regression for interpreter exit during close; no games."""
import argparse,ast,json,os,subprocess,sys
from pathlib import Path
import run_dev as d
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    for path in Path(__file__).parent.glob('*.py'):ast.parse(path.read_text())
    training=Path('/root/heroes3-ai-lab/evaluations/battle-resume-20261023-01');parent=Path(d.read(training/'PLAN.json')['parent_checkpoint']);source=d.LAB/'evaluations/1792726710179968280';restored=[]
    for idx in range(192,200):
        for role in ['attacker','defender']:
            game=d.recovered(source,parent,idx,role,2026103600+idx*100)
            if game:restored.append(game)
    assert restored;example=restored[0]
    # Simulate a native close ending its interpreter immediately after writing
    # pending. The actual game data is historical; this is not another game.
    pending=a.out/'exit-fixture.json.pending.json';out=a.out/'exit-fixture.json';log=a.out/'exit-fixture.log';payload=a.out/'payload.json';d.write(payload,example)
    script="import os,pathlib,shutil,sys;shutil.copyfile(sys.argv[1],sys.argv[2]);print('CPU REGRESSION FIXTURE: no native game',flush=True);print('VCMI shutdown complete.',flush=True);os._exit(0)"
    with log.open('w') as stream:r=subprocess.run([sys.executable,'-c',script,str(payload),str(pending)],stdout=stream)
    assert not out.exists() and pending.exists();d.finalize(out,log,r.returncode);assert out.exists() and not pending.exists()
    rejected=[]
    for name,code,text in [('nonzero',1,'VCMI shutdown complete.'),('no_shutdown',0,'CPU fixture'),('traceback',0,'VCMI shutdown complete.\nTraceback')]:
        target=a.out/(name+'.json');logpath=a.out/(name+'.log');d.write(str(target)+'.pending.json',example);logpath.write_text(text)
        try:d.finalize(target,logpath,code)
        except AssertionError:rejected.append(name)
        else:raise AssertionError(name)
        assert not target.exists()
    d.write(a.out/'AUDIT.json',dict(passed=True,actual_original_games_recoverable=len(restored),recovered_ids=[dict(scenario=g['scenario'],role=g['role'],seed=g['seed']) for g in restored],CPU_close_exit_regression=True,missing_shutdown_nonzero_traceback_rejected=rejected,new_native_games=0,optimizer_steps=0,GPU_operations=0))
    print(json.dumps(dict(passed=True,recoverable=len(restored),new_native_games=0)))
if __name__=='__main__':main()
