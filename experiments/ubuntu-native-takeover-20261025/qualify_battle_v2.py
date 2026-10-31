"""Four fixed historical games as an Ubuntu migration regression, never training."""
import argparse, fcntl, hashlib, importlib.util, json, os, signal, subprocess, sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
PROJECT=HERE.parent.parent
OUTPUTS=Path('/home/kaicheng/Documents/Codex/2026-10-24/hello/outputs')
RUNTIME=Path(os.environ.get('HEROES3_QUAL_RUNTIME_ROOT',str(OUTPUTS/'Heroes3-Ubuntu'))) 
LAB=Path(os.environ.get('HEROES3_QUAL_LAB_ROOT',str(OUTPUTS/'WSL迁出-20261025/files/root/heroes3-ai-lab')))
PYTHON=RUNTIME/'python-heroes3.sh'
CHECKPOINT=PROJECT/'experiments/battle-training-continuation-20261020/monitor-independent-01/user-pause-01/control-update-60.pt'
SHA='443863dd26ea0daaed17cd01ab3dd44a6a16544efac73c96a89839f5b72c0e20'
import leases
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def interrupt(signum,frame):raise KeyboardInterrupt('Migration regression interrupted')
def resources(out,phase,initial=False):
    m={k:int(v.split()[0]) for k,v in (line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines())}
    row=dict(phase=phase,available_mib=m['MemAvailable']/1024,swap_mib=(m['SwapTotal']-m['SwapFree'])/1024)
    with (out/'RESOURCES.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
    assert row['available_mib']>(4096 if initial else 2048) and row['swap_mib']<256
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--execute',action='store_true');a=p.parse_args()
    assert sha(CHECKPOINT)==SHA
    source=HERE/'restored-history/root/heroes3-ai-lab/evaluations/battle-observed-MC-DEV-01'
    expected=[]
    for opponent in ('BattleAI','MMAI_MODEL'):
        report=source/('parent60-'+opponent+'.json');data=json.loads(report.read_text())
        for role in ('attacker','defender'):
            matches=[g for g in data['battles'] if g['role']==role and g['seed']==2026128600]
            assert len(matches)==1 and data['checkpoint'].endswith('/update-60.pt')
            expected.append(dict(opponent=opponent,role=role,seed=2026128600,scenario=192,historical=matches[0],historical_report=str(report),historical_report_sha256=sha(report)))
    protected=json.loads((PROJECT/'experiments/takeover-20261023/first-pilot-protection.json').read_text())['protected_current_files']
    inputs={str(CHECKPOINT):SHA}
    for old,h in protected.items():
        prefix='/root/heroes3-ai-lab/src/gym/vcmi/rel/bin/'
        if old.startswith(prefix):
            original=LAB/old.removeprefix('/root/heroes3-ai-lab/')
            active=RUNTIME/'engine-battle'/Path(old).name
            assert sha(original)==sha(active)==h
            inputs[str(original)]=inputs[str(active)]=h
    for role,h in [('attacker','62adf45ea34a323d72e9ce953a0c8b6740e60c3cec3651f282bfacee785d3151'),('defender','73bca79446ebdcab01e47fbbfada0162380df907bc86b19a21d0c502500cfaa9')]:
        q=RUNTIME/'game-assets/vcmi/Data/MMAI/models'/('lab-upstream-'+role+'.onnx');assert sha(q)==h;inputs[str(q)]=h
    for root in (HERE,PROJECT/'experiments/battle-observed-MC-DEV-20261024'):
        for q in root.glob('*.py'):inputs[str(q)]=sha(q)
    for q in (PYTHON,RUNTIME/'native-paths.so',RUNTIME/'native-paths.c',RUNTIME/'prepare-worker-native.py',PROJECT/'research/diverse-curriculum.json',PROJECT/'research/lab-env.py',PROJECT/'research/recovered-graph.py'):
        inputs[str(q)]=sha(q)
    cases=json.loads((PROJECT/'research/diverse-curriculum.json').read_text())
    mapfile=RUNTIME/'game-assets/vcmi/Maps'/cases[192]['map']
    assert sha(mapfile)==cases[192]['sha256'];inputs[str(mapfile)]=sha(mapfile)
    for subtree in (RUNTIME/'runtime-libs',LAB/'onnxruntime/lib',LAB/'data/vcmi',LAB/'src/gym/vcmi/Mods',LAB/'src/gym/vcmi_gym/connectors/rel'):
        for q in subtree.rglob('*'):
            if q.is_file():inputs[str(q)]=sha(q)
    a.out.mkdir(parents=True,exist_ok=False)
    write(a.out/'PLAN.json',dict(scope='Technical migration regression: four pre-existing fixed historical cells; repeated games are not fresh independent strength evidence.',jobs=expected,checkpoint_sha256=SHA,optimizer_steps=0,final_test_touched=False,execute=a.execute))
    write(a.out/'FREEZE.json',dict(files=inputs))
    if not a.execute:return
    result=dict(passed=False,games=[],optimizer_steps=0,model_promoted=False,final_test_touched=False)
    fs=[]
    try:
        resources(a.out,'start',True)
        leases.LAB.mkdir(parents=True,exist_ok=True)
        for q in leases.PATHS:
            f=q.open('a+');fs.append(f);fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        inherited=[leases.metadata(f,q) for f,q in zip(fs,leases.PATHS)]
        write(a.out/'LEASES.json',dict(entries=inherited,order='GPU then pool',old_WSL_processes_cannot_survive_native_boot=True,lock_files_never_deleted=True))
        for j in expected:
            resources(a.out,j['opponent']+'/'+j['role']+'/before')
            assert all(sha(q)==h for q,h in inputs.items())
            name=j['opponent']+'-'+j['role'];output=a.out/(name+'.json');log=a.out/(name+'.log')
            env=dict(os.environ,HEROES3_LAB_ROOT=str(LAB),TERMINAL_CREDIT_LEASES=json.dumps(inherited),TERMINAL_CREDIT_POOL_LEASE=json.dumps(inherited[1]),LAB_WORKER_ROOT=str(RUNTIME/'workers'/a.out.name/name),LAB_STAGED_BOOT='1',CUDA_VISIBLE_DEVICES='')
            command=[str(PYTHON),str(HERE/'worker_entry_v2.py'),'--scenario','192','--role',j['role'],'--seed',str(j['seed']),'--policy','recovered','--checkpoint',str(CHECKPOINT),'--output',str(output),'--scenarios',str(PROJECT/'research/diverse-curriculum.json'),'--opponent',j['opponent'],'--teacher-turns','2']
            if j['opponent']=='MMAI_MODEL':command+=['--opponent-model','DATA/MMAI/models/lab-upstream-'+('defender' if j['role']=='attacker' else 'attacker')+'.onnx']
            with log.open('wb') as stream:
                child=subprocess.Popen(command,env=env,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True,pass_fds=tuple(f.fileno() for f in fs))
                try:
                    code=child.wait(timeout=300)
                    assert not leases.live_group_members(child.pid),'Worker descendants survived'
                finally:
                    if child.poll() is None or leases.live_group_members(child.pid):leases.stop_group(child)
            assert code==0, str(log)
            assert 'VCMI shutdown complete.' in log.read_text() and 'Traceback' not in log.read_text()
            pending=Path(str(output)+'.pending.json');g=json.loads(pending.read_text())
            assert g['terminated'] and not g['truncated'] and g['terminal_outcome']['result_type']==0 and g['invalid_actions']==0
            comparison={k:g[k]==j['historical'][k] for k in ('trajectory_sha256','steps','success','terminal_outcome','action_types')}
            os.replace(pending,output)
            result['games'].append(dict(name=name,report=str(output),sha256=sha(output),steps=g['steps'],historical_comparison=comparison))
            write(a.out/'PROGRESS.json',result)
            assert all(comparison.values()),'Historical behavior differs; preserve and diagnose, no retry'
            resources(a.out,name+'/after')
        assert all(sha(q)==h for q,h in inputs.items())
        result.update(passed=True,normal_completed_games=4,frozen_inputs_unchanged=True,historical_trajectories_equal=True)
    except BaseException as exc:result['error']=repr(exc)
    finally:
        for f in reversed(fs):f.close()
        write(a.out/'RESULT.json',result)
    return 0 if result['passed'] else 1
if __name__=='__main__':
    signal.signal(signal.SIGINT,interrupt);signal.signal(signal.SIGTERM,interrupt)
    raise SystemExit(main())
