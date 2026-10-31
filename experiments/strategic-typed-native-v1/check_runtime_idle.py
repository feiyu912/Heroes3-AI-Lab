"""Read-only accepted-epoch, lock, process and frozen battle integrity audit."""
import fcntl,hashlib,json,os,subprocess
from pathlib import Path
LAB=Path('/root/heroes3-ai-lab');HERE=Path(__file__).resolve().parent
expected={'AI/DirectorAI/CDirectorAI.cpp':'e198e32f9d3c787e14d575f2fe1c33bba44a8d1351403ffc833c54e4a3079b00'}
expected_bins={'vcmiclient':'b94162bb0d20566ae88512457bdb33266415d338fe92e50c4a6aa6dbd578dd78','vcmiserver':'bbe0de38b7791c7900b2393d1809b38f5f1856ac8922f30d742095759cd43fac','libvcmi.so':'d7016313e9f0e0dfc36d46a9e24d718fb2e7552e6433b5dcd0ca6a26cdaa285a'}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
sources={p:sha(LAB/'src/vcmi-adv'/p) for p in expected};bins={n:sha(LAB/'src/vcmi-adv-build/bin'/n) for n in expected_bins}
assert sources==expected and bins==expected_bins
assert not (LAB/'src/vcmi-adv/AI/DirectorAI/TypedPolicyProtocol.h').exists()
leases=[];locks={}
try:
    for n in ['.gpu-learner-lock','.pool-lock']:
        h=(LAB/'evaluations'/n).open('a+');leases.append(h);fcntl.flock(h,fcntl.LOCK_EX|fcntl.LOCK_NB);locks[n]='available'
finally:
    for h in reversed(leases):h.close()
native=[];learners=[]
for p in Path('/proc').iterdir():
    if not p.name.isdigit():continue
    try:
        exe=(p/'exe').resolve(strict=True);cmd=(p/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
        if exe.name in ['vcmiclient','vcmiserver']:native.append({'pid':p.name,'exe':str(exe)})
        if 'python' in exe.name and any(x in cmd for x in ['parallel_trainer.py','train_ppo_pilot.py']):learners.append({'pid':p.name,'command':cmd})
    except (OSError,ProcessLookupError):continue
assert not native and not learners
frozen=subprocess.run(['bash',str(HERE.parent/'adv-verify-frozen.sh')],capture_output=True,text=True);assert frozen.returncode==0
gpu=subprocess.run(['nvidia-smi','--query-compute-apps=pid,process_name,used_memory','--format=csv,noheader'],capture_output=True,text=True)
result={'passed':True,'accepted_source':sources,'accepted_binaries':bins,'native_processes':native,'learner_processes':learners,'locks':locks,'frozen_battle_audit':frozen.stdout,'gpu_compute_query':{'exit':gpu.returncode,'stdout':gpu.stdout,'stderr':gpu.stderr},'goal_complete':False}
out=HERE/'idle-integrity-01.json';assert not out.exists();out.write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
