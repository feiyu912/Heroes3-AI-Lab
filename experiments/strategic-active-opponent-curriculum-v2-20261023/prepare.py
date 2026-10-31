"""Preserve prepared v1; add bounded owned-session cleanup before native use."""
from pathlib import Path
import hashlib,json,shutil
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'strategic-active-opponent-curriculum-20261023'
LEASES=HERE.parent/'battle-terminal-credit-native-20261023/leases.py'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def once(s,a,b):
    assert s.count(a)==1,(a[:80],s.count(a))
    return s.replace(a,b,1)
def main():
    assert not (HERE/'run_calibration.py').exists(),'Preserve any prepared epoch'
    for name in ('pipeline_common.py','audit_game.py','derive_maps.py','MAP_MANIFEST.json','PLAN.md'):
        shutil.copy2(OLD/name,HERE/name)
    shutil.copy2(LEASES,HERE/'leases.py')
    collector=(OLD/'collect_calibration.py').read_text()
    collector=once(collector,'from contextlib import contextmanager','from contextlib import contextmanager\nfrom leases import stop_group')
    begin=collector.index('def stop(child):');end=collector.index('\ndef run(args):',begin)
    collector=collector[:begin]+'''def stop(child):
    if child is not None: stop_group(child)

def interrupted(signum, frame):
    raise KeyboardInterrupt('Calibration collector interrupted: '+str(signum))

signal.signal(signal.SIGTERM, interrupted)

'''+collector[end:]
    collector=once(collector,'cwd=work,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)',
        'cwd=work,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,pass_fds=lease_fds)')
    (HERE/'collect_calibration.py').write_text(collector)
    driver=(OLD/'run_calibration.py').read_text()
    driver=once(driver,'from pathlib import Path','from pathlib import Path\nimport os,signal\nimport leases\ndef interrupted(signum, frame):\n    raise KeyboardInterrupt("Calibration controller interrupted: "+str(signum))\nsignal.signal(signal.SIGTERM,interrupted)')
    driver=once(driver,"run=subprocess.run(command,capture_output=True,text=True);(root/(label+'.log')).write_text(run.stdout+'\\nSTDERR:\\n'+run.stderr)\n                assert run.returncode==0", "with (root/(label+'.log')).open('w') as stream:\n                    code=leases.run_owned(command,env=dict(os.environ),stream=stream)\n                assert code==0")
    driver=once(driver,"    write(a.out/'RESULT.json',report);", "    leases.finish_owned_groups()\n    write(a.out/'RESULT.json',report);")
    (HERE/'run_calibration.py').write_text(driver)
    (HERE/'COLLECTOR_DERIVATION.json').write_text(json.dumps({'parent_directory':str(OLD),'parent_collector_sha256':sha(OLD/'collect_calibration.py'),
        'collector_sha256':sha(HERE/'collect_calibration.py'),'driver_sha256':sha(HERE/'run_calibration.py'),'leases_sha256':sha(HERE/'leases.py'),
        'changes':['native inherits real GPU/pool flock descriptors','stop checks independent-session descendants before lease release','controller owns collector sessions and waits cleanup','SIGTERM triggers controlled finally cleanup'],
        'scientific_changes':False,'maps_models_seeds_selection_unchanged':True,'native_runs':0,'optimizer_steps':0},indent=2))
    with (HERE/'PLAN.md').open('a') as f:f.write('\n\nLifecycle correction v2: native and broker inherit actual resource lease descriptors; both independent sessions are stopped and verified empty before release. Controller owns collector sessions; SIGTERM enters cleanup. Map/model/seeds/12-cell selection are unchanged. Parent package remains preserved.\n')
if __name__=='__main__':main()
