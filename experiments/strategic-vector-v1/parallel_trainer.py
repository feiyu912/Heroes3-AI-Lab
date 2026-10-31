#!/usr/bin/env python3
"""Single-learner synchronous vector PPO with complete-update recovery."""
import argparse
from contextlib import ExitStack
import hashlib
import io
import json
import os
from pathlib import Path
import random
import shutil
import sys

os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG', ':4096:8')
from collect_vector import (torch, V2, HERE, THROUGHPUT, LAB, DEFAULT_CHECKPOINT, WORKER,
                            collect_parallel, lease, tensor_sha, BatchAbort, write, sha)
from encoder import ENCODER_VERSION, STATE_DIM, CANDIDATE_DIM
from model import model_from_bundle, PRIOR_FORMAT, atomic_torch_save
from episode_balanced_ppo import (PROTOCOL, ppo_update, optimizer_steps,
                                  parameter_snapshot, parameter_delta)

TRAINING_SCHEMA='strategic-parallel-episode-balanced-ppo-v1'
MAPS=['Maps/adv/takeover-v2-train-01-mines','Maps/adv/takeover-v2-train-02-development']


def schedule(update,environments,seed_base):
    """2/4/8 slots collect 8 episodes; 24 slots collect 3 seeds x 8 cells."""
    jobs=[]
    for seed_index in range(3 if environments==24 else 1):
        for map_index,map_name in enumerate(MAPS):
            for opponent_index,opponent in enumerate(('EmptyAI','Nullkiller2')):
                for role in range(2):
                    jobs.append(dict(map=map_name,red='DirectorAI' if role==0 else opponent,
                        blue=opponent if role==0 else 'DirectorAI',
                        seed=seed_base+update*1000+seed_index*16+map_index*4+opponent_index*2+role))
    return jobs


def digest_json(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def read_bundle(path):
    raw=Path(path).read_bytes()
    return torch.load(io.BytesIO(raw),map_location='cpu',weights_only=True),hashlib.sha256(raw).hexdigest()


def freeze_ok(hashes):
    return all(Path(path).exists() and sha(Path(path))==value for path,value in hashes.items())


def save_checkpoint(model,optimizer,path,*,update,complete,protocol,protocol_sha,parent_sha,
                    lineage,collection_states,attempted_update,progress):
    cuda=next(model.parameters()).device.type=='cuda'
    data=dict(format=PRIOR_FORMAT,encoder_version=ENCODER_VERSION,state_dim=STATE_DIM,candidate_dim=CANDIDATE_DIM,
        hidden=model.hidden,prior_config=dict(prior_scale=float(model.prior_scale.detach().cpu()),prior_feature_index=model.prior_feature_index),
        state_dict={k:v.detach().cpu().clone() for k,v in model.state_dict().items()},optimizer=optimizer.state_dict(),
        training_schema=TRAINING_SCHEMA,training_updates=update,optimizer_steps_total=optimizer_steps(optimizer),
        complete_update_boundary=complete,attempted_update=attempted_update,progress=progress,
        protocol=protocol,protocol_sha256=protocol_sha,parent_checkpoint_sha256=parent_sha,lineage=lineage,
        torch_rng=torch.get_rng_state(),cuda_rng=torch.cuda.get_rng_state_all() if cuda else [],python_rng=random.getstate(),
        collection_episode_generator_states=collection_states,policy_tensor_sha256=tensor_sha(model),
        trained=optimizer_steps(optimizer)>0 or bool(lineage.get('parent_training_updates',0)) or bool(lineage.get('parent_trained',False)),
        value_is_win_probability=False,scope='Target choice; economy scripted; native battles; training outcomes are not independent evaluation')
    atomic_torch_save(data,path)
    # File and rename were fsynced by atomic helper; also persist directory entry.
    fd=os.open(Path(path).parent,os.O_RDONLY|os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    return sha(Path(path))


def restore(bundle,optimizer,device,protocol_sha,total_updates):
    if bundle.get('training_schema')!=TRAINING_SCHEMA or not bundle.get('complete_update_boundary',False):
        raise ValueError('Resume requires this trainer complete-update checkpoint; partial is never resumable')
    if bundle.get('protocol_sha256')!=protocol_sha:
        raise ValueError('Resume protocol/source/runtime changed; explicit weights-only initialization required')
    update=int(bundle['training_updates'])
    if not 0<=update<total_updates:
        raise ValueError('Target total updates must exceed resumed complete update')
    optimizer.load_state_dict(bundle['optimizer'])
    if optimizer_steps(optimizer)!=bundle['optimizer_steps_total']:
        raise ValueError('Adam step metadata mismatch')
    if device.type=='cuda' and not bundle.get('cuda_rng'):
        raise ValueError('CUDA resume requires saved CUDA RNG')
    if not bundle.get('collection_episode_generator_states') and update>0:
        raise ValueError('Complete update lacks collection RNG provenance')
    torch.set_rng_state(bundle['torch_rng'].cpu())
    if device.type=='cuda':
        torch.cuda.set_rng_state_all([value.cpu() for value in bundle['cuda_rng']])
    random.setstate(bundle['python_rng'])
    return update


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--execute',action='store_true',help='Default prepares only; no model/GPU/game launch')
    p.add_argument('--environments',type=int,choices=(2,4,8,24),default=2)
    p.add_argument('--updates',type=int,default=1,help='Target total completed updates, including resumed ones')
    p.add_argument('--synthetic',action='store_true',help='CPU fake engine fixture; never actual GPU/game')
    p.add_argument('--seed-base',type=int,default=2026102300)
    p.add_argument('--seconds',type=int,default=90)
    p.add_argument('--epochs',type=int,default=4)
    p.add_argument('--minibatch-size',type=int,default=64)
    p.add_argument('--batch-wait-ms',type=float,default=2)
    p.add_argument('--inference-schedule',choices=('async','barrier'),default='barrier')
    origin=p.add_mutually_exclusive_group()
    origin.add_argument('--resume',type=Path)
    origin.add_argument('--initialize-from',type=Path)
    p.add_argument('--inject-optimizer-failure-step',type=int,default=0,help='Synthetic-only failure AFTER actual Adam step')
    a=p.parse_args()
    if min(a.updates,a.epochs,a.minibatch_size,a.seconds)<1 or a.batch_wait_ms<0:
        p.error('Positive updates/epochs/minibatch/seconds and nonnegative batch wait required')
    if a.inject_optimizer_failure_step and not a.synthetic:
        p.error('Failure injection is synthetic only')
    if not a.execute:
        a.out.mkdir(parents=True,exist_ok=False)
        write(a.out/'preparation.json',dict(schema=TRAINING_SCHEMA,execute=False,environments=a.environments,
            total_updates=a.updates,update1_jobs=schedule(1,a.environments,a.seed_base),
            mode='CPU synthetic' if a.synthetic else 'CUDA real',optimizer_steps=0,
            note='No GPU/game/model loaded. Runtime/source/map hashes freeze only at actual execution.'))
        return 0
    a.out.mkdir(parents=True,exist_ok=False)
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    device=torch.device('cpu' if a.synthetic else 'cuda')
    origin_path=(a.resume or a.initialize_from or DEFAULT_CHECKPOINT).resolve()
    with ExitStack() as stack:
        gpu_lock=None;gpu_identity=None
        if device.type=='cuda':
            gpu_lock=stack.enter_context(lease(LAB/'evaluations/.gpu-learner-lock'))
            st=os.fstat(gpu_lock.fileno());gpu_identity=(st.st_dev,st.st_ino)
            if not torch.cuda.is_available():
                raise RuntimeError('CUDA required; no CPU fallback for actual training')
        bundle,origin_sha=read_bundle(origin_path)
        if a.resume and (bundle.get('training_schema')!=TRAINING_SCHEMA or not bundle.get('complete_update_boundary',False)):
            raise ValueError('Partial/foreign checkpoint is not resumable')
        sources=[Path(__file__).resolve(),HERE/'collect_vector.py',HERE/'episode_balanced_ppo.py',
                 V2/'encoder.py',V2/'model.py',WORKER,THROUGHPUT/'measure.py']
        if a.synthetic:
            sources.append(V2/'fixtures/visible-request.json')
        else:
            sources += [LAB/'src/vcmi-adv-build/bin'/n for n in ('vcmiclient','vcmiserver','libvcmi.so')]
            sources += list((LAB/'src/vcmi-adv/AI/DirectorAI').glob('*.[ch]*'))
            sources += [path for path in (LAB/'src/vcmi-adv-build/bin/config').rglob('*') if path.is_file()]
            sources += [path for path in (LAB/'data/vcmi/Mods').rglob('*.json') if path.is_file()]
            sources += [LAB/('data/vcmi/'+name+'.vmap') for name in MAPS]
        hashes={str(path):sha(path) for path in sources}
        initialization=(bundle.get('protocol',{}).get('initialization') if a.resume else
            dict(mode='weights-only' if a.initialize_from else 'migrated-v3-initial',checkpoint=str(origin_path),sha256=origin_sha))
        if not initialization:
            raise ValueError('Missing original initialization recipe in resume protocol')
        # Retain the original initialization bytes as a recipe input on resume.
        hashes[initialization['checkpoint']]=sha(Path(initialization['checkpoint']))
        if hashes[initialization['checkpoint']]!=initialization['sha256']:
            raise ValueError('Initialization input changed')
        algorithm=dict(PROTOCOL,epochs=a.epochs,minibatch_size=a.minibatch_size)
        protocol=dict(schema=TRAINING_SCHEMA,encoder_version=ENCODER_VERSION,algorithm=algorithm,
            lr=.0003,environments=a.environments,synthetic=a.synthetic,seed_base=a.seed_base,
            seconds=a.seconds,batch_wait_ms=a.batch_wait_ms,initialization=initialization,hashes=hashes,
            inference_schedule=a.inference_schedule,random_stream='job seed + logical update version; parameter digest is provenance only',
            schedule='8=2map*2opponent*2role, one seed; 24=three seed*8; seed=base+update*1000+seed_index*16+map*4+opponent*2+role',
            collection='Synchronous complete-terminal waves; fixed policy across all waves; all invalid abort before PPO',
            scalar_reward='native terminal win +1/loss -1; no shaping')
        protocol_sha=digest_json(protocol)
        write(a.out/'protocol.json',dict(protocol=protocol,sha256=protocol_sha))
        snapshot=a.out/'source-snapshot';snapshot.mkdir()
        for index,path in enumerate(sources):
            if path.suffix in ('.py','.cpp','.h'):
                shutil.copy2(path,snapshot/f'{index:02d}-{path.name}')
        plan=dict(schema=TRAINING_SCHEMA,protocol_sha256=protocol_sha,target_total_updates=a.updates,
            resumed_from=str(a.resume) if a.resume else None,origin_checkpoint=str(origin_path),origin_sha256=origin_sha,
            device=str(device),independent_evaluation=False)
        write(a.out/'plan.json',plan)
        torch.random.default_generator.manual_seed(2026102301)
        random.seed(2026102301)
        if device.type=='cuda':
            torch.cuda.manual_seed_all(2026102301)
        model=model_from_bundle(bundle,device)
        optimizer=torch.optim.Adam(model.parameters(),lr=.0003)
        completed=restore(bundle,optimizer,device,protocol_sha,a.updates) if a.resume else 0
        collection_states=bundle.get('collection_episode_generator_states',{}) if a.resume else {}
        lineage=dict(mode='resume' if a.resume else ('weights-only' if a.initialize_from else 'migrated-v3-initial'),
            parent_checkpoint=str(origin_path),parent_sha256=origin_sha,parent_training_updates=int(bundle.get('training_updates',0)),
            parent_protocol_sha256=bundle.get('protocol_sha256'),parent_migration_protocol_sha256=bundle.get('migration_protocol_sha256'),
            parent_lineage=bundle.get('lineage'),parent_trained=bool(bundle.get('trained',False)),
            reset_optimizer=not bool(a.resume),reset_rng=not bool(a.resume))
        report=dict(status='running',synthetic=a.synthetic,device=str(device),CUDA_training=False,CPU_training=False,
            CUDA_inference=False,independent_evaluation=False,resumed_from_update=completed,
            optimizer_steps_total=optimizer_steps(optimizer),optimizer_steps_this_run=0,updates=[],episodes=[],lineage=lineage)
        initial_steps=optimizer_steps(optimizer)
        parent_sha=origin_sha
        active=None
        attempted=None
        def checkpoint(path,complete=True,update_override=None):
            return save_checkpoint(model,optimizer,path,update=completed if update_override is None else update_override,complete=complete,protocol=protocol,
                protocol_sha=protocol_sha,parent_sha=parent_sha,lineage=lineage,collection_states=collection_states,
                attempted_update=attempted,progress=active)
        if a.inject_optimizer_failure_step:
            real_step=optimizer.step
            def fail_after_step(*args,**kwargs):
                answer=real_step(*args,**kwargs)
                if optimizer_steps(optimizer)-initial_steps>=a.inject_optimizer_failure_step:
                    raise RuntimeError('Injected failure after real Adam step')
                return answer
            optimizer.step=fail_after_step
        try:
            current_checkpoint=a.out/f'update-{completed}.pt'
            parent_sha=checkpoint(current_checkpoint)
            for update in range(completed+1,a.updates+1):
                attempted=update
                active=dict(update=update,metrics={},waves=[])
                report['active_update']=active
                if not freeze_ok(hashes) or sha(origin_path)!=origin_sha:
                    raise RuntimeError('Frozen inputs changed before collection')
                version=f'update-{completed}'
                fixed_weights=tensor_sha(model)
                jobs=schedule(update,a.environments,a.seed_base)
                rows=[];episodes=[];new_states={}
                for offset in range(0,len(jobs),a.environments):
                    wave=offset//a.environments
                    wave_out=a.out/f'update-{update:03d}-wave-{wave:02d}'
                    accepted,records=collect_parallel(model,jobs[offset:offset+a.environments],wave_out,device,version,
                        checkpoint=current_checkpoint,gpu_lock_fd=gpu_lock.fileno() if gpu_lock else None,
                        gpu_lock_identity=gpu_identity,seconds=a.seconds,batch_wait_ms=a.batch_wait_ms,synthetic=a.synthetic,
                        inference_schedule=a.inference_schedule)
                    if not freeze_ok(hashes) or tensor_sha(model)!=fixed_weights or sha(origin_path)!=origin_sha:
                        raise RuntimeError('Source/runtime/model changed during on-policy collection')
                    boundary,collection_sha=read_bundle(wave_out/'collection-boundary.pt')
                    new_states[f'wave-{wave}']=dict(collection_sha256=collection_sha,
                        episode_generator_states=boundary['episode_generator_states'],
                        policy_version=boundary['policy_version'],policy_tensor_sha256=boundary['policy_tensor_sha256'])
                    rows.extend(accepted);episodes.extend(records)
                    active['waves'].append(dict(index=wave,episodes=len(records),samples=len(accepted),collection_boundary_sha256=collection_sha))
                    report['episodes'].extend(records)
                    report['CUDA_inference']=device.type=='cuda'
                    write(a.out/'training.json',report)
                if len(episodes)!=len(jobs) or len({e['episode_id'] for e in episodes})!=len(jobs):
                    raise RuntimeError('Balanced update missing or duplicated complete episodes')
                if not freeze_ok(hashes) or tensor_sha(model)!=fixed_weights:
                    raise RuntimeError('Frozen input/model changed before optimizer')
                before=parameter_snapshot(model)
                metrics=ppo_update(model,optimizer,rows,device,active['metrics'],episodes=episodes,
                                   epochs=a.epochs,minibatch_size=a.minibatch_size)
                if not metrics['completed'] or not freeze_ok(hashes) or sha(origin_path)!=origin_sha:
                    raise RuntimeError('Incomplete update or changed input after optimizer')
                active['parameter_delta_from_previous_update']=parameter_delta(model,before)
                collection_states=new_states
                path=a.out/f'update-{update}.pt'
                digest=checkpoint(path,update_override=update)
                completed=update
                report['updates'].append(dict(update=update,samples=len(rows),episodes=len(episodes),policy_version_collected=version,
                    checkpoint=str(path),sha256=digest,metrics=metrics,parameter_delta_from_previous_update=active['parameter_delta_from_previous_update']))
                parent_sha=digest
                current_checkpoint=path
                report['optimizer_steps_total']=optimizer_steps(optimizer)
                report['optimizer_steps_this_run']=optimizer_steps(optimizer)-initial_steps
                report['CUDA_training']=device.type=='cuda' and report['optimizer_steps_this_run']>0
                report['CPU_training']=device.type=='cpu' and report['optimizer_steps_this_run']>0
                active=None;report.pop('active_update',None)
                write(a.out/'training.json',report)
            report['status']='completed'
        except BaseException as error:
            report['status']='failed';report['error']=repr(error)
            report['CUDA_inference']=device.type=='cuda' and any(path.stat().st_size>0 for path in a.out.glob('update-*-wave-*/inference-batches.jsonl'))
            if isinstance(error,BatchAbort):
                report['failed_collection_episodes']=error.episodes
            report['optimizer_steps_total']=optimizer_steps(optimizer)
            report['optimizer_steps_this_run']=optimizer_steps(optimizer)-initial_steps
            report['CUDA_training']=device.type=='cuda' and report['optimizer_steps_this_run']>0
            report['CPU_training']=device.type=='cpu' and report['optimizer_steps_this_run']>0
            partial=a.out/'failed-partial-not-resumable.pt'
            try:
                digest=checkpoint(partial,False)
                report['failed_partial_checkpoint']=dict(path=str(partial),sha256=digest,resumable=False)
            except BaseException as save_error:
                report['partial_save_error']=repr(save_error)
            raise
        finally:
            write(a.out/'training.json',report)
    print(json.dumps(dict(status=report['status'],synthetic=a.synthetic,updates=completed,
        optimizer_steps_this_run=report['optimizer_steps_this_run'],CUDA_training=report['CUDA_training'])),flush=True)
    return 0


if __name__=='__main__':
    raise SystemExit(main())
