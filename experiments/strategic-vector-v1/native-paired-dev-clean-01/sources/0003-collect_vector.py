#!/usr/bin/env python3
"""Central-policy synchronous vector collection; no optimizer or training loop."""
import argparse
from contextlib import contextmanager, ExitStack
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
import time
import uuid

os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG', ':4096:8')
HERE = Path(__file__).resolve().parent
V2 = HERE.parent/'strategic-policy-v2'
THROUGHPUT = HERE.parent/'cpu-simulator-throughput-v1'
sys.path.insert(0, str(V2))
sys.path.insert(0, str(THROUGHPUT))
import torch
from encoder import collate, validate, ENCODER_VERSION
from model import load_checkpoint_bundle, atomic_torch_save
from measure import batch_processes, clean, memory, synthetic_lab, write, sha

LAB = Path('/root/heroes3-ai-lab')
DEFAULT_CHECKPOINT = V2/'checkpoints/threat-supply-initial-v3.pt'
WORKER = THROUGHPUT/'worker_runner.py'


class BatchAbort(RuntimeError):
    def __init__(self, message, episodes):
        super().__init__(message)
        self.episodes = episodes
        self.accepted_rows = []


def tensor_sha(model):
    return state_tensor_sha(model.state_dict())


def state_tensor_sha(state):
    h = hashlib.sha256()
    for key, tensor in sorted(state.items()):
        value = tensor.detach().cpu().contiguous()
        h.update(key.encode())
        h.update(str(value.dtype).encode())
        h.update(str(tuple(value.shape)).encode())
        h.update(value.numpy().tobytes())
    return h.hexdigest()


@contextmanager
def lease(path, inherited_fd=None, identity=None):
    if inherited_fd is None:
        lock = path.open('a')
        try:
            fcntl.flock(lock, fcntl.LOCK_EX|fcntl.LOCK_NB)
            yield lock
        finally:
            lock.close()
        return
    if identity is None or len(identity) != 2:
        raise ValueError('Inherited lease requires explicit (device,inode) identity')
    with os.fdopen(os.dup(inherited_fd),'a') as lock:
        stat = os.fstat(lock.fileno())
        target = path.stat()
        if (stat.st_dev,stat.st_ino) != tuple(identity) or (target.st_dev,target.st_ino) != tuple(identity):
            raise ValueError('Inherited lease identity mismatch')
        with path.open('a') as probe:
            try:
                fcntl.flock(probe,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:
                pass
            else:
                raise ValueError('Inherited lease is not already held')
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        yield lock
        # Never unlock a shared open file description owned by the caller.


def env_seed(job, policy_version):
    material = json.dumps(dict(seed=job['seed'],policy_version=str(policy_version),
                          map=job['map'],red=job['red'],blue=job['blue']),sort_keys=True).encode()
    return int.from_bytes(hashlib.sha256(material).digest()[:8],'little') % (2**63-1)


def sample_ready(model, pending, generators, device):
    requests = [entry[2] for entry in pending]
    with torch.no_grad():
        logits, values = model(**collate(requests,device))
        if not bool(torch.isfinite(values).all()):
            raise ValueError('Nonfinite critic value')
        results = []
        for row,(index,raw,request) in enumerate(pending):
            legal = logits[row,:len(request['candidates'])]
            if not bool(torch.isfinite(legal).all()):
                raise ValueError('Nonfinite legal logit')
            logp = legal.log_softmax(-1)
            probabilities = logp.exp()
            action = int(torch.multinomial(probabilities,1,generator=generators[index]).item())
            results.append((action,float(logp[action]),float(values[row])))
    return results


def audit_native_events(run,expected,completed,last_row=None):
    trace=run/'strategy-trace.jsonl'
    evidence=[]
    counts=dict(move_applied=0,move_failed=0,economy_failed=0,query_failed=0,server_rejected=0)
    if not trace.exists():
        return dict(valid=False,error='Native state trace missing',counts=counts,evidence=[])
    for number,line in enumerate(trace.open(),1):
        event=json.loads(line).get('event')
        if event in counts:
            counts[event]+=1
        if event in ('move_failed','economy_failed','query_failed'):
            evidence.append(dict(file=str(trace),line=number,event=event,text=line.rstrip()))
    replies=[]
    terminal_tail=[]
    for number,line in enumerate((run/'client.log').open(errors='replace'),1):
        if 'DirectorAI: step hero' in line:
            terminal_tail=[]
        terminal_tail.append((number,line.rstrip()))
        reply=re.search(r'DirectorAI: step finished result=(\d+)',line)
        if reply:
            replies.append(int(reply[1]))
        rejection=('has to answer queries' in line or 'Got false in applying' in line or
            bool(re.search(r'(?:QueryReply|query reply).*?(?:failed|success=0|result=0)',line,re.I)))
        if rejection:
            counts['server_rejected']+=1
            if 'QueryReply' in line or 'query reply' in line.lower():
                counts['query_failed']+=1
            evidence.append(dict(file=str(run/'client.log'),line=number,event='server_rejected',text=line.rstrip()))
    failed_reply=sum(value==0 for value in replies)
    missing_ack=expected-counts['move_applied']-counts['move_failed']
    missing_execution=expected-len(replies)
    # A terminal can interrupt the final response ACK after the native move was
    # already applied. Native move-result evidence must still exist for every row.
    terminal_ack_only=completed and missing_ack==1 and missing_execution==0 and failed_reply==0
    terminal_visit_proof=None
    if completed and missing_ack==1 and missing_execution==1 and last_row:
        request=last_row['request'];candidate=request['candidates'][last_row['action']]
        if candidate['kind'] in (0,1) and candidate['next']==candidate['position']:
            service=None;hero_name=None;visit=None;outcome=None
            for number,text in terminal_tail:
                if re.search(r'Player '+str(request['player'])+r' .*wants to move hero '+str(request['hero'])+r' from ',text):
                    service=number
                movement=re.search(r'Hero (.*?) starts movement from ',text)
                if service and movement:
                    hero_name=movement[1]
                if hero_name and 'Hero '+hero_name+' visits ' in text:
                    visit=number
                if visit and ('BattleResult' in text or 'SetObjectProperty' in text or 'ChangeObjectOwner' in text):
                    outcome=number
            if service and visit and outcome:
                terminal_visit_proof=dict(action_index=expected-1,server_request_line=service,
                    native_hero=hero_name,hero_visit_line=visit,battle_or_capture_outcome_line=outcome,
                    target=candidate['position'],kind=candidate['kind'],
                    note='Last military target request was received, this hero visited it, and native battle/capture outcome preceded terminal; no move reply/ACK is required to infer a nonexistent displacement.')
    valid=(not evidence and failed_reply==0 and (
           (missing_execution==0 and (missing_ack==0 or terminal_ack_only)) or terminal_visit_proof is not None))
    return dict(valid=bool(valid),counts=counts,evidence=evidence,move_reply_count=len(replies),
        failed_move_reply_count=failed_reply,blocking_visit_reply_count=sum(v==3 for v in replies),
        expected_actions=expected,missing_ack_count=missing_ack,missing_execution_reply_count=missing_execution,
        terminal_ack_missing_after_execution=bool(terminal_ack_only),
        terminal_native_visit_execution_proof=terminal_visit_proof,
        terminal_unconfirmed_action_indices=list(range(max(0,len(replies)),expected)) if completed and missing_execution>0 and terminal_visit_proof is None else [],
        classification='terminal_native_visit_execution_confirmed' if terminal_visit_proof else ('complete_execution_terminal_ack_missing' if terminal_ack_only else ('complete_execution' if valid else 'native_failure_or_unconfirmed_execution')))


def native_report(env):
    files = [p for p in env['directory'].glob('*.json') if p.name not in ('native-pid.json','episode.json')]
    result = json.loads(files[0].read_text()) if len(files)==1 else {}
    rows = env['rows']
    run = Path(result['run_dir']) if result.get('run_dir') else None
    native = []
    if run and (run/'strategy-decisions.jsonl').exists():
        native = [json.loads(line) for line in (run/'strategy-decisions.jsonl').open()]
    verified = bool(rows) and len(rows)==len(native)
    if verified:
        for row, choice in zip(rows,native):
            request = row['request']
            candidate = request['candidates'][row['action']]
            request_path = env['agent']/f"request-{request['request_id']:08d}.json"
            verified = verified and sha(request_path)==row['request_sha256'] and (
                choice['selected_candidate']==row['action'] and choice['candidates']==request['candidates'] and
                all(choice[key]==request[key] for key in ('player','day','hero','from')) and
                choice['destination']==candidate['position'] and choice['step']==candidate['next'])
    event_audit=audit_native_events(run,len(rows),bool(result.get('completed')),rows[-1] if rows else None) if run else dict(valid=False,error='No native run')
    valid = env['process'].returncode==0 and bool(result.get('completed')) and bool(result.get('inputs_unchanged')) and verified and event_audit['valid']
    color = 'red' if env['job']['red']=='DirectorAI' else 'blue'
    reward = (1. if result.get('winner')==color else -1.) if valid else None
    record = dict(episode_index=env['index'],episode_id=env['episode_id'],config=env['job'],valid=bool(valid),reward=reward,
                  decisions=len(rows),native_consumption_verified=bool(verified),native=result,
                  rollout_dir=str(env['agent']),generator_seed=env['generator_seed'],native_event_audit=event_audit)
    write(env['directory']/'episode.json',record)
    return record


def install_fake_engine(lab, reverse=False, invalid=False, failure_kind='none'):
    fixture = json.loads((V2/'fixtures/visible-request.json').read_text())
    engine = lab/'src/vcmi-adv-build/bin/vcmiclient'
    engine.write_text('#!'+sys.executable+'\n'+'''import json, os, time
from pathlib import Path
fixture = '''+repr(fixture)+'''
directory = Path(os.environ['LAB_ADV_AGENT_DIR'])
index = int(os.environ['LAB_VECTOR_INDEX'])
reverse = '''+repr(reverse)+'''
invalid = '''+repr(invalid)+'''
failure_kind = '''+repr(failure_kind)+'''
print('Player red will be lead by '+os.environ['LAB_ADV_AI_0'],flush=True)
print('Player blue will be lead by '+os.environ['LAB_ADV_AI_1'],flush=True)
position = [10,10,0]
for number in range(1,5):
    time.sleep(((3-index%4) if reverse else index%4)*.015)
    request = dict(fixture, request_id=number,day=number,player=0 if os.environ['LAB_ADV_AI_0']=='DirectorAI' else 1,hero=index,
                   **{'from':position, 'candidates':fixture['candidates'][:1 if number%2==0 else 2]})
    path = directory/('request-%08d.json'%number)
    temp = path.with_suffix('.tmp'); temp.write_text(json.dumps(request)); os.replace(temp,path)
    action_path = directory/('action-%08d.json'%number)
    until = time.monotonic()+15
    while not action_path.exists() and time.monotonic()<until: time.sleep(.001)
    action = int(action_path.read_text())
    candidate = request['candidates'][action]
    print('DirectorAI: step hero fake',flush=True)
    if not (failure_kind=='terminal_pending' and number==4 and index==0):
        print('DirectorAI: step finished result=%d points_left=100 from (1 1 0) to (2 1 0)'%(3 if failure_kind=='blocking' else 1),flush=True)
    with Path(os.environ['LAB_ADV_TRACE']).open('a') as states:
        event='move_applied'
        if index==0 and number==1 and failure_kind in ('move','economy'): event=failure_kind+'_failed'
        if not (number==4 and index==0 and failure_kind in ('terminal_ack','terminal_pending')):
            states.write(json.dumps(dict(event=event,day=number))+'\\n')
    if index==0 and number==1 and failure_kind=='query': print('Got false in applying 10QueryReply... that request must have been fishy!',flush=True)
    native = dict(request,selected_candidate=(action+1 if invalid and index==0 and number==1 else action),destination=candidate['position'],step=candidate['next'])
    with Path(os.environ['LAB_ADV_DECISIONS']).open('a') as trace: trace.write(json.dumps(native)+'\\n')
    position = candidate['next']
print('DirectorAI: native gameOver player=red victory=1 loss=0',flush=True)
print('All players have ended the game.',flush=True)
''')
    engine.chmod(0o755)


def collect_parallel(model, jobs, out, device, policy_version, *, checkpoint=DEFAULT_CHECKPOINT,
                     gpu_lock_fd=None, gpu_lock_identity=None,pool_lock_fd=None,pool_lock_identity=None,
                     seconds=90,batch_wait_ms=2,synthetic=False,synthetic_reverse=False,synthetic_invalid=False,
                     synthetic_failure_kind='none',inference_schedule='async'):
    """Return (accepted rows, episodes); BatchAbort guarantees accepted_rows=[] on any invalid episode.

    Caller may own the single learner lock and model. No optimizer is created or
    invoked here. One job/episode per environment, full-terminal synchronous barrier.
    """
    device = torch.device(device)
    actual_device = next(model.parameters()).device
    if device.index is None and actual_device.type == device.type:
        device = actual_device
    if not 1<=len(jobs)<=24 or batch_wait_ms<0 or seconds<1:
        raise ValueError('Expected 1..24 environments and positive duration')
    if inference_schedule not in ('async','barrier'):
        raise ValueError('inference_schedule must be async or barrier')
    if synthetic and device.type!='cpu':
        raise ValueError('Synthetic collection is CPU only')
    if next(model.parameters()).device != device:
        raise ValueError('Model must already be on manager device')
    if device.type=='cuda':
        if gpu_lock_fd is None:
            raise ValueError('CUDA API requires a supervisor-held GPU lease FD and identity; CLI acquires one before model loading')
        # Verify the caller's continuing lease before even copying GPU tensors
        # for the immutable policy digest. The caller retains its original FD.
        with lease(LAB/'evaluations/.gpu-learner-lock',gpu_lock_fd,gpu_lock_identity):
            pass
    for job in jobs:
        if sum(job[color]=='DirectorAI' for color in ('red','blue'))!=1:
            raise ValueError('Exactly one DirectorAI per environment')
    out = Path(out)
    out.mkdir(parents=True,exist_ok=False)
    token = uuid.uuid4().hex
    lab = synthetic_lab(out,False) if synthetic else LAB
    if synthetic:
        install_fake_engine(lab,synthetic_reverse,synthetic_invalid,synthetic_failure_kind)
    checkpoint = Path(checkpoint)
    sources = [Path(__file__),WORKER,THROUGHPUT/'measure.py',V2/'encoder.py',V2/'model.py',checkpoint]
    sources += [lab/'src/vcmi-adv-build/bin'/n for n in ('vcmiclient','vcmiserver','libvcmi.so')]
    sources += list((lab/'src/vcmi-adv/AI/DirectorAI').glob('*.[ch]*'))
    sources += sorted({lab/('data/vcmi/'+job['map']+'.vmap') for job in jobs})
    hashes = {str(path):sha(path) for path in sources}
    initial_weights = tensor_sha(model)
    checkpoint_bytes=checkpoint.read_bytes()
    if hashlib.sha256(checkpoint_bytes).hexdigest()!=hashes[str(checkpoint)]:
        raise ValueError('Checkpoint changed between freeze and single-read load')
    checkpoint_bundle=torch.load(io.BytesIO(checkpoint_bytes),map_location='cpu',weights_only=True)
    if state_tensor_sha(checkpoint_bundle['state_dict'])!=initial_weights:
        raise ValueError('Current checkpoint weights do not match manager model')
    baseline = memory()
    minimum_ram = max(2*1024**3,int(baseline['MemTotal']*.2))
    plan = dict(schema='synchronous-vector-collection-v2',synthetic=synthetic,device=str(device),jobs=jobs,
                environments=len(jobs),policy_version=str(policy_version),policy_tensor_sha256=initial_weights,
                checkpoint_sha256=hashes[str(checkpoint)],encoder_version=ENCODER_VERSION,hashes=hashes,
                checkpoint_tensor_matches_model=True,
                source_scope='Visible native candidate choices; scripted economy and native battles',
                inference_schedule=inference_schedule,
                per_environment_rng='SHA256(job seed,map,roles,logical policy version); parameter SHA is provenance only; torch.Generator(device); multinomial per legal row',
                optimization='No optimizer; all full native terminals and exact request consumption required before returning training rows',
                baseline_memory=baseline,token=token)
    write(out/'plan.json',plan)
    stop = False
    def stopping(*_):
        nonlocal stop
        stop = True
    old_term = signal.signal(signal.SIGTERM,stopping)
    old_int = signal.signal(signal.SIGINT,stopping)
    environments=[]
    generators={}
    episodes=[]
    failure=None
    started=time.monotonic()
    original_training=model.training
    model.eval()
    try:
        with ExitStack() as stack:
            if device.type=='cuda':
                stack.enter_context(lease(LAB/'evaluations/.gpu-learner-lock',gpu_lock_fd,gpu_lock_identity))
            lock=stack.enter_context(lease(lab/'evaluations/.pool-lock',pool_lock_fd,pool_lock_identity))
            identity=os.fstat(lock.fileno())
            if memory()['MemAvailable']<minimum_ram:
                raise RuntimeError('Available-memory gate before launch')
            resource=stack.enter_context((out/'resources.jsonl').open('w'))
            inference=stack.enter_context((out/'inference-batches.jsonl').open('w'))
            try:
                for index,job in enumerate(jobs):
                    directory=out/f'env-{index:03d}'; directory.mkdir()
                    agent=directory/'agent'; agent.mkdir()
                    seed=env_seed(job,str(policy_version))
                    episode_id=hashlib.sha256(json.dumps(dict(job=job,index=index,policy_version=str(policy_version),
                        policy_tensor_sha256=initial_weights),sort_keys=True).encode()).hexdigest()
                    generators[index]=torch.Generator(device=device).manual_seed(seed)
                    cmd=[sys.executable,str(WORKER),'--map',job['map'],'--red',job['red'],'--blue',job['blue'],
                         '--seed',str(job['seed']),'--seconds',str(seconds),'--tag',f'vector-{token[:8]}-{index}',
                         '--agent-dir',str(agent),'--report-dir',str(directory),'--native-pid-file',str(directory/'native-pid.json'),
                         '--lab-root',str(lab),'--pool-lock-fd',str(lock.fileno()),'--pool-lock-dev',str(identity.st_dev),
                         '--pool-lock-inode',str(identity.st_ino)]
                    env=dict(os.environ,LAB_THROUGHPUT_BATCH=token,LAB_THROUGHPUT_JOB=str(index),LAB_VECTOR_INDEX=str(index),
                             OMP_NUM_THREADS='1',CUDA_VISIBLE_DEVICES='')
                    with (directory/'worker.log').open('w') as log:
                        proc=subprocess.Popen(cmd,env=env,pass_fds=(lock.fileno(),),stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                    environments.append(dict(index=index,job=job,directory=directory,agent=agent,process=proc,rows=[],
                                             generator_seed=seed,episode_id=episode_id,completed=False))
                last_resource=0
                while not all(env['completed'] for env in environments):
                    if stop or time.monotonic()-started>seconds+20:
                        raise RuntimeError('Interrupted or manager deadline; invalid entire batch')
                    pending=[]
                    def scan():
                        pending.clear()
                        for env in environments:
                            if env['completed']:
                                continue
                            if env['process'].poll() is not None:
                                record=native_report(env)
                                episodes.append(record)
                                env['completed']=True
                                if not record['valid']:
                                    raise RuntimeError(f"Invalid native episode {env['index']}; abort all environments")
                                continue
                            number=len(env['rows'])+1
                            path=env['agent']/f'request-{number:08d}.json'
                            if path.exists():
                                raw=path.read_bytes(); request=validate(json.loads(raw),number)
                                pending.append((env['index'],raw,request))
                    scan()
                    if pending and batch_wait_ms:
                        time.sleep(batch_wait_ms/1000)
                        scan()
                    if inference_schedule=='barrier' and len(pending)!=sum(not env['completed'] for env in environments):
                        pending=[]
                    if pending:
                        before=time.monotonic()
                        chosen=sample_ready(model,pending,generators,device)
                        elapsed=time.monotonic()-before
                        inference.write(json.dumps(dict(seconds=before-started,batch_size=len(pending),
                            candidate_counts=[len(p[2]['candidates']) for p in pending],env_indices=[p[0] for p in pending],
                            forward_and_sampling_seconds=elapsed,device=str(device),policy_version=str(policy_version),
                            policy_tensor_sha256=initial_weights))+'\n'); inference.flush()
                        for (index,raw,request),(action,logprob,value) in zip(pending,chosen):
                            env=environments[index]
                            response=env['agent']/f"action-{request['request_id']:08d}.json"
                            if response.exists():
                                raise RuntimeError('Response already exists')
                            row=dict(episode_index=index,episode_id=env['episode_id'],request=request,action=action,old_logprob=logprob,old_value=value,
                                     request_sha256=hashlib.sha256(raw).hexdigest(),policy_version=str(policy_version),
                                     policy_tensor_sha256=initial_weights,checkpoint_sha256=plan['checkpoint_sha256'],
                                     generator_seed=env['generator_seed'],model_device=str(device))
                            with (env['directory']/'committed.jsonl').open('a') as trace:
                                trace.write(json.dumps(row,allow_nan=False)+'\n'); trace.flush(); os.fsync(trace.fileno())
                            temp=response.with_suffix('.tmp'); temp.write_text(str(action)+'\n'); os.replace(temp,response)
                            env['rows'].append(row)
                    else:
                        time.sleep(.001)
                    now=time.monotonic()
                    if now-last_resource>.2:
                        last_resource=now
                        mem=memory(); processes=batch_processes(token); rss=sum(p['rss'] for p in processes)
                        gpu=dict(allocated=torch.cuda.memory_allocated(device),reserved=torch.cuda.memory_reserved(device)) if device.type=='cuda' else None
                        resource.write(json.dumps(dict(seconds=now-started,memory=mem,processes=processes,batch_rss=rss,gpu_manager=gpu))+'\n'); resource.flush()
                        if mem['MemAvailable']<minimum_ram or mem['SwapUsed']-baseline['SwapUsed']>256*1024**2 or mem['disk_free']<5*1024**3 or rss>baseline['MemTotal']*.7:
                            raise RuntimeError('Resource gate; invalid entire batch')
                        if not all(sha(Path(p))==s for p,s in hashes.items()):
                            raise RuntimeError('Frozen inputs changed; invalid entire batch')
            finally:
                clean([env['process'] for env in environments],token)
    except Exception as error:
        failure=repr(error)
    finally:
        signal.signal(signal.SIGTERM,old_term); signal.signal(signal.SIGINT,old_int)
        model.train(original_training)
    for env in environments:
        if not env['completed']:
            try:
                episodes.append(native_report(env))
            except Exception as error:
                episodes.append(dict(episode_index=env['index'],config=env['job'],valid=False,error=repr(error)))
    episodes.sort(key=lambda episode:episode['episode_index'])
    weights_unchanged=tensor_sha(model)==initial_weights
    inputs_unchanged=all(sha(Path(p))==s for p,s in hashes.items())
    leftovers=batch_processes(token)
    valid=not failure and len(episodes)==len(jobs) and all(e['valid'] for e in episodes) and weights_unchanged and inputs_unchanged and not leftovers
    report=dict(status='complete_on_policy_batch' if valid else 'invalid_batch',synthetic=synthetic,episodes=episodes,
                error=failure,accepted_samples=sum(len(env['rows']) for env in environments) if valid else 0,
                learner_update_allowed=bool(valid),actual_optimizer_steps=0,policy_unchanged=weights_unchanged,
                inputs_unchanged=inputs_unchanged,remaining_processes=leftovers,wall_seconds=time.monotonic()-started)
    write(out/'batch.json',report)
    if not valid:
        raise BatchAbort(failure or 'Incomplete/on-policy/input/cleanup validation failed',episodes)
    rewards={episode['episode_index']:episode['reward'] for episode in episodes}
    rows=[dict(row,**{'return':rewards[env['index']]}) for env in environments for row in env['rows']]
    with (out/'accepted-rollout.jsonl').open('w') as stream:
        for row in rows:
            stream.write(json.dumps(row,allow_nan=False)+'\n')
    atomic_torch_save(dict(policy_version=str(policy_version),policy_tensor_sha256=initial_weights,
                          episode_generator_states={str(index):gen.get_state().cpu() for index,gen in generators.items()},
                          complete_collection_boundary=True,training_updates=0),out/'collection-boundary.pt')
    return rows,episodes


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--execute',action='store_true')
    p.add_argument('--device',choices=('cpu','cuda'),default='cuda')
    p.add_argument('--environments',type=int,default=2)
    p.add_argument('--checkpoint',type=Path,default=DEFAULT_CHECKPOINT)
    p.add_argument('--policy-version',default='initial-v3')
    p.add_argument('--seconds',type=int,default=90)
    p.add_argument('--batch-wait-ms',type=float,default=2)
    p.add_argument('--inference-schedule',choices=('async','barrier'),default='async')
    p.add_argument('--synthetic',action='store_true')
    p.add_argument('--synthetic-reverse',action='store_true')
    p.add_argument('--synthetic-invalid',action='store_true')
    p.add_argument('--synthetic-failure-kind',choices=('none','move','economy','query','terminal_ack','terminal_pending','blocking'),default='none')
    a=p.parse_args()
    if not 1<=a.environments<=24:
        p.error('environments must be 1..24')
    jobs=[]
    for i in range(a.environments):
        opponent='EmptyAI' if i%4<2 else 'Nullkiller2'
        jobs.append(dict(map='Maps/adv/takeover-v2-'+('train-01-mines' if i//4%2==0 else 'train-02-development'),
                         red='DirectorAI' if i%2==0 else opponent,blue=opponent if i%2==0 else 'DirectorAI',seed=2026102200+i))
    if not a.execute:
        a.out.mkdir(parents=True,exist_ok=False)
        write(a.out/'preparation.json',dict(ready_only=True,jobs=jobs,device=a.device,checkpoint=str(a.checkpoint),
              checkpoint_sha256=sha(a.checkpoint),claim='No rollout launched, no GPU accessed, no optimizer steps'))
        return 0
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    device='cpu' if a.synthetic else a.device
    # Lock before moving weights to CUDA; collect verifies this exact lease again.
    with ExitStack() as stack:
        gpu_lock=None;identity=None
        if device=='cuda':
            gpu_lock=stack.enter_context(lease(LAB/'evaluations/.gpu-learner-lock'))
            stat=os.fstat(gpu_lock.fileno());identity=(stat.st_dev,stat.st_ino)
        model,_,checkpoint_sha=load_checkpoint_bundle(a.checkpoint,device)
        try:
            rows,episodes=collect_parallel(model,jobs,a.out,device,a.policy_version,checkpoint=a.checkpoint,
                gpu_lock_fd=gpu_lock.fileno() if gpu_lock else None,gpu_lock_identity=identity,seconds=a.seconds,
                batch_wait_ms=a.batch_wait_ms,synthetic=a.synthetic,synthetic_reverse=a.synthetic_reverse,synthetic_invalid=a.synthetic_invalid,
                synthetic_failure_kind=a.synthetic_failure_kind,inference_schedule=a.inference_schedule)
        except BatchAbort as error:
            print(json.dumps(dict(status='invalid_batch',error=str(error),optimizer_steps=0)),flush=True)
            return 1
    print(json.dumps(dict(status='complete_collection',episodes=len(episodes),samples=len(rows),device=device,optimizer_steps=0)),flush=True)
    return 0


if __name__=='__main__':
    raise SystemExit(main())
