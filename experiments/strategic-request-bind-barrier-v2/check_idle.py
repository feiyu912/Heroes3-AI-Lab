"""Read-only post-experiment runtime, resources and accepted artifacts snapshot."""
import fcntl,hashlib,json,os,subprocess,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;LAB=Path('/root/heroes3-ai-lab')
expected={'src/vcmi-adv/AI/DirectorAI/CDirectorAI.cpp':'e198e32f9d3c787e14d575f2fe1c33bba44a8d1351403ffc833c54e4a3079b00',
 'src/vcmi-adv-build/bin/vcmiclient':'b94162bb0d20566ae88512457bdb33266415d338fe92e50c4a6aa6dbd578dd78',
 'src/vcmi-adv-build/bin/vcmiserver':'bbe0de38b7791c7900b2393d1809b38f5f1856ac8922f30d742095759cd43fac',
 'src/vcmi-adv-build/bin/libvcmi.so':'d7016313e9f0e0dfc36d46a9e24d718fb2e7552e6433b5dcd0ca6a26cdaa285a'}
actual={k:hashlib.sha256((LAB/k).read_bytes()).hexdigest() for k in expected};assert actual==expected
handles=[];processes=[]
try:
    for name in ('.gpu-learner-lock','.pool-lock'):
        h=(LAB/'evaluations'/name).open('a+');handles.append(h);fcntl.flock(h,fcntl.LOCK_EX|fcntl.LOCK_NB)
    for p in Path('/proc').iterdir():
        if not p.name.isdigit() or int(p.name)==os.getpid():continue
        try:
            exe=(p/'exe').resolve(strict=True);cmd=(p/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
            if exe.name in ('vcmiclient','vcmiserver') or ('python' in exe.name and any(t in cmd for t in ('onpolicy_broker','train_update','parallel_trainer','train_certified','collect_balanced','paired_eval'))):processes.append(dict(pid=p.name,exe=str(exe),command=cmd))
        except OSError:continue
    assert not processes,processes
    frozen=subprocess.run(['bash',str(HERE.parent/'adv-verify-frozen.sh')],capture_output=True,text=True);assert frozen.returncode==0
    gpu=subprocess.run(['nvidia-smi','--query-compute-apps=pid,process_name,used_memory','--format=csv,noheader'],capture_output=True,text=True)
    memory={x.split(':',1)[0]:x.split(':',1)[1].strip() for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith(('MemAvailable:','SwapFree:','SwapTotal:'))}
    result=dict(passed=True,time_unix=time.time(),accepted_sha256=actual,locks='both acquired exclusively for this snapshot',native_or_learning_processes=processes,
        frozen_battle=frozen.stdout,gpu=dict(exit=gpu.returncode,stdout=gpu.stdout,stderr=gpu.stderr),memory=memory,optimizer_steps=0,goal_complete=False)
    out=HERE/'idle-after-proxy-abort-01.json';assert not out.exists();out.write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
finally:
    for h in reversed(handles):h.close()
