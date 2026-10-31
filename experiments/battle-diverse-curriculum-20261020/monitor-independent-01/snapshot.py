"""One read-only live OS snapshot, then immutable completed-boundary checks. No polling."""
import datetime,hashlib,json,os,re,subprocess,time
from pathlib import Path
OUT=Path(__file__).resolve().parent;HERE=OUT.parent;LAB=Path('/root/heroes3-ai-lab');B=LAB/'evaluations/battle-diverse60-native-02'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,v):Path(p).write_text(json.dumps(v,indent=2)+'\n')
def read_process(pid):
    root=Path('/proc')/str(pid)
    try:
        status=root.joinpath('status').read_text();cmd=root.joinpath('cmdline').read_bytes().decode(errors='replace').split('\0');cmd=[x for x in cmd if x]
        return dict(pid=int(pid),ppid=int(re.search(r'^PPid:\s*(\d+)',status,re.M)[1]),comm=root.joinpath('comm').read_text().strip(),cmdline=cmd)
    except (FileNotFoundError,ProcessLookupError,PermissionError):return None
def main():
    started=time.monotonic();utc=datetime.datetime.now(datetime.timezone.utc).isoformat();processes={}
    for p in Path('/proc').iterdir():
        if p.name.isdigit():
            row=read_process(p.name)
            if row:processes[row['pid']]=row
    launchers=[p for p in processes.values() if str(HERE/'run.py') in p['cmdline'] and str(B) in p['cmdline']];assert len(launchers)==1
    launcher=launchers[0];owned={launcher['pid']}
    while True:
        extended=owned|{pid for pid,p in processes.items() if p['ppid'] in owned}
        if extended==owned:break
        owned=extended
    learners=[p for pid,p in processes.items() if pid in owned and str(HERE/'train_last_graph.py') in p['cmdline']];assert len(learners)==1;learner=learners[0]
    workers=[p for p in processes.values() if p['ppid']==learner['pid'] and any('multiprocessing.spawn' in a for a in p['cmdline'])]
    mem={k:int(v.strip().split()[0]) for k,v in (line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines())}
    locks_raw=Path('/proc/locks').read_text();lock_proof={}
    for name in ('.gpu-learner-lock','.pool-lock'):
        p=LAB/'evaluations'/name;s=p.stat();identity='%02x:%02x:%d'%(os.major(s.st_dev),os.minor(s.st_dev),s.st_ino)
        lines=[l for l in locks_raw.splitlines() if identity in l];assert len(lines)==1 and int(lines[0].split()[4])==launcher['pid']
        lock_proof[name]=dict(device_inode=identity,actual_kernel_record=lines[0],holder_pid=launcher['pid'])
    detail=[]
    for pid in sorted(owned):
        row=dict(processes[pid]);root=Path('/proc')/str(pid);pss={};threads=[];native=[]
        try:
            for line in root.joinpath('smaps_rollup').read_text().splitlines():
                m=re.match(r'^(Rss|Pss|Private_Clean|Private_Dirty|Swap|SwapPss):\s*(\d+) kB',line)
                if m:pss[m[1]+'_KiB']=int(m[2])
            for t in root.joinpath('task').iterdir():
                try:threads.append(dict(tid=int(t.name),comm=(t/'comm').read_text().strip()))
                except FileNotFoundError:pass
            maps=root.joinpath('maps').read_text();native=sorted({l.split()[-1] for l in maps.splitlines() if any(s in l for s in ('libmlclient.so','libmlserverplugin.so','libvcmi.so','connector_v15.so'))})
        except (FileNotFoundError,ProcessLookupError,PermissionError):row['exited_during_snapshot']=True
        row.update(memory=pss,threads=threads,native_mapped_libraries=native);detail.append(row)
    gpu={}
    for label,args in [('device',['--query-gpu=name,memory.used,memory.total,utilization.gpu,temperature.gpu']),('compute_apps',['--query-compute-apps=pid,process_name,used_gpu_memory'])]:
        r=subprocess.run(['nvidia-smi',*args,'--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=10);gpu[label]=dict(returncode=r.returncode,stdout=r.stdout.strip(),stderr=r.stderr.strip())
    report_bytes=(B/'training.json').read_bytes();report=json.loads(report_bytes);write(OUT/'TRAINING_REPORT_SNAPSHOT.json',report)
    os_snapshot=dict(captured_UTC=utc,read_window_seconds=time.monotonic()-started,launcher_pid=launcher['pid'],learner_pid=learner['pid'],worker_pids=[p['pid'] for p in workers],worker_count=len(workers),locks=lock_proof,
        owned_process_tree=detail,mem_available_MiB=mem['MemAvailable']/1024,host_swap_used_MiB=(mem['SwapTotal']-mem['SwapFree'])/1024,
        owned_PSS_MiB=sum(p['memory'].get('Pss_KiB',0) for p in detail)/1024,owned_swap_MiB=sum(p['memory'].get('Swap_KiB',0) for p in detail)/1024,gpu=gpu,
        other_training_commands=[p for pid,p in processes.items() if pid not in owned and any(Path(a).name in ('train_last_graph.py','train_update_v3.py','train_efficiency.py','train-graph-finetune.py','train-recovered-heads.py') for a in p['cmdline'])],
        report_snapshot_original_sha256=hashlib.sha256(report_bytes).hexdigest(),report_snapshot_stable_copy=str(OUT/'TRAINING_REPORT_SNAPSHOT.json'))
    write(OUT/'OS_SNAPSHOT.json',os_snapshot)
    # All further checks concern immutable completed files, not a second OS poll.
    import torch
    freeze=json.loads((B/'FREEZE.json').read_text());assert all(sha(p)==h for p,h in freeze['input_sha256'].items())
    record=report['records'][-1];checkpoint=Path(report['checkpoint']);state=torch.load(checkpoint,map_location='cpu',weights_only=True)
    assert sha(checkpoint)==record['checkpoint_sha256'] and state['completed_updates']==record['update'] and state['actual_Adam_steps']==record['actual_Adam_steps_total'] and state['complete_update_boundary']
    raw=state['rollout_evidence'];assert raw==record['rollout'] and sha(raw['path'])==raw['sha256'] and Path(raw['path']).stat().st_size==raw['bytes']
    assert state['frozen_inputs']==freeze and state['config']['workers']==16 and state['config']['updates']==30 and not state['native_environment_restorable']
    wd={p['pid']:p for p in detail if p['pid'] in {w['pid'] for w in workers}}
    native_workers=[pid for pid,p in wd.items() if any('libmlclient.so' in q for q in p['native_mapped_libraries']) and any('libvcmi.so' in q for q in p['native_mapped_libraries'])]
    out=dict(snapshot_checks_passed=True,experiment_completed_at_snapshot=report['completed'],final_experiment_passed=False,new_native_games=0,new_GPU_operations=0,new_optimizer_steps=0,
        observed_workers=len(workers),native_library_bound_workers=len(native_workers),native_worker_pids=native_workers,actual_scale_observed_is_24=False,
        native_scope='Native engine embedded in worker processes; see task names/maps. Do not invent 16 separate native executable PIDs.',
        latest_completed_update=record['update'],actual_Adam_steps_total=state['actual_Adam_steps'],sample_rows_through_saved_updates=sum(r['samples'] for r in report['records']),
        checkpoint_sha256=sha(checkpoint),complete_rollout_sha256=raw['sha256'],source_freeze_current=True,OS_snapshot_file=str(OUT/'OS_SNAPSHOT.json'),
        final_30_updates_and_64_DEV_certified=False,limitations='One bounded /proc and nvidia-smi read window, not simultaneous atomic process/resource accounting. No polling or CUDA replay; active experiment remains unqualified.',
        input_sha256={str(p):sha(p) for p in [Path(__file__),B/'FREEZE.json',B/'PLAN.json',checkpoint,Path(raw['path']),OUT/'OS_SNAPSHOT.json',OUT/'TRAINING_REPORT_SNAPSHOT.json']})
    write(OUT/'AUDIT.json',out);print(json.dumps({k:out[k] for k in ['snapshot_checks_passed','observed_workers','native_library_bound_workers','latest_completed_update','actual_Adam_steps_total','final_30_updates_and_64_DEV_certified']},indent=2));print(json.dumps({k:os_snapshot[k] for k in ['launcher_pid','learner_pid','mem_available_MiB','host_swap_used_MiB','owned_PSS_MiB','owned_swap_MiB','gpu']},indent=2))
if __name__=='__main__':main()
