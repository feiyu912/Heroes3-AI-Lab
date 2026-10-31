"""One bounded read-only live snapshot; no polling or native/CUDA execution."""
import datetime,hashlib,json,os,re,subprocess,time
from pathlib import Path
OUT=Path(__file__).resolve().parent;HERE=OUT.parent;LAB=Path('/root/heroes3-ai-lab');RUN=LAB/'evaluations/battle-continuation-lr-paired-01'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(name,data):(OUT/name).write_text(json.dumps(data,indent=2)+'\n')
def process(pid):
    root=Path('/proc')/str(pid)
    try:
        s=(root/'status').read_text();return dict(pid=int(pid),ppid=int(re.search(r'^PPid:\s*(\d+)',s,re.M)[1]),cmdline=[v for v in (root/'cmdline').read_bytes().decode(errors='replace').split('\0') if v])
    except (FileNotFoundError,ProcessLookupError,PermissionError):return None
def main():
    begin=time.monotonic();utc=datetime.datetime.now(datetime.timezone.utc).isoformat();processes={}
    for p in Path('/proc').iterdir():
        if p.name.isdigit():
            row=process(p.name)
            if row:processes[row['pid']]=row
    launch=[p for p in processes.values() if str(HERE/'run.py') in p['cmdline'] and str(RUN) in p['cmdline']];assert len(launch)==1;launcher=launch[0]
    owned={launcher['pid']}
    while True:
        extended=owned|{p['pid'] for p in processes.values() if p['ppid'] in owned}
        if extended==owned:break
        owned=extended
    learners=[p for p in processes.values() if p['pid'] in owned and str(HERE/'train_last_graph.py') in p['cmdline']];assert len(learners)==1;learner=learners[0]
    arm=learner['cmdline'][learner['cmdline'].index('--arm')+1];assert arm=='control'
    workers=[p for p in processes.values() if p['ppid']==learner['pid'] and any('multiprocessing.spawn' in v for v in p['cmdline'])]
    locks={};text=Path('/proc/locks').read_text()
    for name in ('.gpu-learner-lock','.pool-lock'):
        s=(LAB/'evaluations'/name).stat();key='%02x:%02x:%d'%(os.major(s.st_dev),os.minor(s.st_dev),s.st_ino)
        rows=[line for line in text.splitlines() if key in line];assert len(rows)==1 and int(rows[0].split()[4])==launcher['pid'];locks[name]=rows[0]
    env={v.split('=',1)[0]:v.split('=',1)[1] for v in (Path('/proc')/str(learner['pid'])/'environ').read_bytes().decode(errors='replace').split('\0') if '=' in v}
    whitelist={k:env.get(k) for k in ('LAB_STAGED_BOOT','LAB_NATIVE_ONNX_CUDA','LAB_ONNX_CUDA','LAB_BATTLEAI_TEACHER')}
    assert whitelist['LAB_STAGED_BOOT']=='1' and all(whitelist[k] in (None,'','0') for k in ('LAB_NATIVE_ONNX_CUDA','LAB_ONNX_CUDA','LAB_BATTLEAI_TEACHER'))
    details=[]
    for pid in sorted(owned):
        row=dict(processes[pid]);root=Path('/proc')/str(pid);memory={};native=[];threads=[]
        try:
            for line in (root/'smaps_rollup').read_text().splitlines():
                m=re.match(r'^(Rss|Pss|Swap|SwapPss):\s*(\d+) kB',line)
                if m:memory[m[1]+'_KiB']=int(m[2])
            native=sorted({line.split()[-1] for line in (root/'maps').read_text().splitlines() if any(n in line for n in ('libvcmi.so','libmlclient.so','libmlserverplugin.so','connector_v15.so'))})
            for t in (root/'task').iterdir():
                try:threads.append(dict(tid=int(t.name),comm=(t/'comm').read_text().strip()))
                except FileNotFoundError:pass
        except (FileNotFoundError,ProcessLookupError,PermissionError):row['exited_during_window']=True
        row.update(memory=memory,native_mapped_libraries=native,threads=threads);details.append(row)
    mem={k:int(v.strip().split()[0]) for k,v in (line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines())}
    gpu={}
    for key,args in [('device',['--query-gpu=name,memory.used,memory.total,utilization.gpu,temperature.gpu']),('compute_apps',['--query-compute-apps=pid,process_name,used_gpu_memory'])]:
        r=subprocess.run(['nvidia-smi',*args,'--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=10);gpu[key]=dict(returncode=r.returncode,stdout=r.stdout.strip(),stderr=r.stderr.strip())
    GPU_pids=[int(s.split(',')[0].strip()) for s in gpu['compute_apps']['stdout'].splitlines() if s.split(',')[0].strip().isdigit()]
    assert GPU_pids==[learner['pid']]
    snapshot=dict(captured_UTC=utc,read_window_seconds=time.monotonic()-begin,arm=arm,launcher_pid=launcher['pid'],learner_pid=learner['pid'],worker_pids=[p['pid'] for p in workers],worker_count=len(workers),owned_tree=details,locks=locks,selected_environment=whitelist,gpu=gpu,sole_GPU_learner_observed=True,
        host_MemAvailable_MiB=mem['MemAvailable']/1024,host_swap_used_MiB=(mem['SwapTotal']-mem['SwapFree'])/1024,owned_PSS_MiB=sum(p['memory'].get('Pss_KiB',0) for p in details)/1024,owned_swap_MiB=sum(p['memory'].get('Swap_KiB',0) for p in details)/1024)
    write('OS_SNAPSHOT.json',snapshot)
    # Subsequent evidence checks are CPU reads of stable saved boundaries, not another OS scan.
    restore_path=RUN/arm/'training.restoration.json';raw_restore=restore_path.read_bytes();restoration=json.loads(raw_restore);write('RESTORATION_SNAPSHOT.json',restoration)
    assert restoration['parent_checkpoint_sha256']=='dcaab92162b9c5b4cb9e5d9773067a320fe9b81fe91c1907449d4a7f8374cdaa'
    assert restoration['actual_Adam_counter_before_first_sampling']==3840 and restoration['CUDA_restore_executed'] is True and all(restoration['all_RNG_before_first_sampling'].values())
    assert restoration['lr_override']==dict(arm='control',group='last_graph',before=1e-6,after=1e-6,heads_unchanged=1e-5)
    frozen=json.loads((RUN/'FREEZE.json').read_text());assert all(sha(p)==h for p,h in frozen['input_sha256'].items())
    tp=RUN/arm/'training.json';record=None;boundary=None
    if tp.exists():
        raw_report=tp.read_bytes();report=json.loads(raw_report);write('TRAINING_REPORT_SNAPSHOT.json',report)
        if report.get('records'):
            import torch
            record=report['records'][-1];cp=Path(report['checkpoint']);state=torch.load(cp,map_location='cpu',weights_only=True)
            assert sha(cp)==record['checkpoint_sha256'] and state['completed_updates']==record['update'] and state['actual_Adam_steps']==record['actual_Adam_steps_total']
            assert state['frozen_inputs']==frozen and state['complete_update_boundary'] and not state['native_environment_restorable']
            assert state['actual_Adam_steps']-3840==record['actual_Adam_steps_this_stage'] and state['completed_updates']>=31
            evidence=state['rollout_evidence'];assert evidence==record['rollout'] and sha(evidence['path'])==evidence['sha256'] and Path(evidence['path']).stat().st_size==evidence['bytes']
            boundary=dict(global_update=state['completed_updates'],stage_updates=state['completed_updates']-30,cumulative_Adam_steps=state['actual_Adam_steps'],stage_Adam_steps=state['actual_Adam_steps']-3840,stage_sampled_rows=sum(r['samples'] for r in report['records']),checkpoint_sha256=sha(cp),rollout_sha256=evidence['sha256'])
    native_workers=[p['pid'] for p in details if p['pid'] in {w['pid'] for w in workers} and any('libvcmi.so' in s for s in p['native_mapped_libraries']) and any('libmlclient.so' in s for s in p['native_mapped_libraries'])]
    result=dict(snapshot_checks_passed=True,new_native_games=0,GPU_operations=0,optimizer_steps_performed=0,parent_historical_Adam_steps=3840,arm=arm,observed_workers=len(workers),native_library_bound_workers=len(native_workers),native_worker_pids=native_workers,
        latest_complete_saved_boundary=boundary,source_freeze_current=True,input_count=len(frozen['input_sha256']),final_two_arm_DEV_certified=False,actual_scale_observed_is_24=False,
        limitation='One bounded process/resource read window; engine is embedded in worker threads, not separate executable PIDs. This is monitoring, not final or independent GPU restoration.',
        restoration_original_sha256=hashlib.sha256(raw_restore).hexdigest(),input_sha256={str(p):sha(p) for p in [Path(__file__),RUN/'FREEZE.json',RUN/'PLAN.json',OUT/'OS_SNAPSHOT.json',OUT/'RESTORATION_SNAPSHOT.json']})
    write('AUDIT.json',result);print(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in snapshot.items() if k not in ('owned_tree','worker_pids')},indent=2))
if __name__=='__main__':main()
