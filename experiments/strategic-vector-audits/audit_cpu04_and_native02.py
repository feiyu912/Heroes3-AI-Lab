#!/usr/bin/env python3
"""Independent completed-evidence checks. No sampling, backward, optimizer or GPU."""
import argparse
from collections import Counter
import hashlib
import io
import json
from pathlib import Path
import re

import torch

EXPERIMENTS=Path(__file__).resolve().parent.parent
ROOT=EXPERIMENTS/'strategic-vector-v1'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def lines(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines()]


def bundle(path):
    raw=Path(path).read_bytes()
    return torch.load(io.BytesIO(raw),map_location='cpu',weights_only=True),hashlib.sha256(raw).hexdigest()


def exact(a,b):
    if isinstance(a,torch.Tensor):
        return isinstance(b,torch.Tensor) and a.dtype==b.dtype and a.shape==b.shape and torch.equal(a,b)
    if isinstance(a,dict):
        return isinstance(b,dict) and a.keys()==b.keys() and all(exact(a[key],b[key]) for key in a)
    if isinstance(a,(tuple,list)):
        return isinstance(b,type(a)) and len(a)==len(b) and all(exact(x,y) for x,y in zip(a,b))
    return type(a)==type(b) and a==b


def tensor_digest(state):
    digest=hashlib.sha256()
    for key,value in sorted(state.items()):
        value=value.detach().cpu().contiguous()
        digest.update(key.encode());digest.update(str(value.dtype).encode());digest.update(str(tuple(value.shape)).encode())
        digest.update(value.numpy().tobytes())
    return digest.hexdigest()


def stage_rows(stage,update):
    result=[]
    for wave in sorted(stage.glob(f'update-{update:03d}-wave-*')):
        result.extend(lines(wave/'accepted-rollout.jsonl'))
    return result


def audit_cpu():
    names=('trainer-cpu-continuous-04','trainer-cpu-split-04','trainer-cpu-resume-04')
    stages={name:read(ROOT/name/'training.json') for name in names}
    assert all(stage['status']=='completed' and stage['synthetic'] and not stage['CUDA_training'] for stage in stages.values())
    assert [stages[name]['optimizer_steps_this_run'] for name in names]==[8,4,4]
    plans={name:read(ROOT/name/'plan.json') for name in names}
    protocol_hashes={plan['protocol_sha256'] for plan in plans.values()}
    assert len(protocol_hashes)==1
    assert plans[names[0]]['resumed_from'] is None and plans[names[1]]['resumed_from'] is None
    assert Path(plans[names[2]]['resumed_from'])==(ROOT/names[1]/'update-1.pt')
    tokens,run_dirs,agents,labs=set(),set(),set(),set()
    worker_records=[]
    for name in names:
        stage=ROOT/name
        for wave in sorted(stage.glob('update-???-wave-*')):
            plan=read(wave/'plan.json');result=read(wave/'batch.json')
            assert plan['synthetic'] and plan['inference_schedule']=='barrier'
            assert plan['token'] not in tokens
            tokens.add(plan['token'])
            assert result['status']=='complete_on_policy_batch' and not result['remaining_processes']
            current=next(path for path in plan['hashes'] if '/update-' in path and path.endswith('.pt'))
            saved,_=bundle(current)
            assert tensor_digest(saved['state_dict'])==plan['policy_tensor_sha256']
            assert plan['hashes'][current]==sha(current)
            for episode in result['episodes']:
                native=episode['native'];run=Path(native['run_dir']);agent=Path(episode['rollout_dir'])
                assert str(run) not in run_dirs and str(agent) not in agents
                run_dirs.add(str(run));agents.add(str(agent));labs.add(native['config']['lab_root'])
                assert agent.exists() and native['config']['lab_root'].startswith('/tmp/throughput-synthetic-')
                assert episode['valid'] and episode['decisions']==4 and native['completed']
                env=wave/f"env-{episode['episode_index']:03d}"
                process=read(env/'native-pid.json')
                assert process['batch']==plan['token']
                assert ('RUN_DIR='+str(run)) in (env/'worker.log').read_text()
                if run.exists():
                    assert sha(run/'client.log')==native['log_sha256']
                    assert sha(run/'strategy-decisions.jsonl')==native['strategy_decisions_sha256']
                assert len(list(agent.glob('request-????????.json')))==4
                assert len(list(agent.glob('action-????????.json')))==4
                worker_records.append(dict(stage=name,wave=wave.name,run_dir=str(run),agent_dir=str(agent),
                    pid=process['pid'],batch_token=process['batch'],worker_log_sha256=sha(env/'worker.log'),
                    temporary_native_directory_still_available=run.exists()))
    comparisons={}
    row_fields=('request','action','old_logprob','old_value','return','generator_seed','policy_version','episode_id','policy_tensor_sha256')
    for update,other in ((1,names[1]),(2,names[2])):
        left,right=stage_rows(ROOT/names[0],update),stage_rows(ROOT/other,update)
        assert len(left)==len(right)==32
        comparisons[f'update{update}_rollout']={field:exact([row[field] for row in left],[row[field] for row in right]) for field in row_fields}
        a,_=bundle(ROOT/names[0]/f'update-{update}.pt');b,_=bundle(ROOT/other/f'update-{update}.pt')
        comparisons[f'update{update}_checkpoint']={field:exact(a[field],b[field]) for field in
            ('state_dict','optimizer','torch_rng','cuda_rng','python_rng','protocol','protocol_sha256','optimizer_steps_total')}
        # collection file digests are provenance; compare the actual generator states and policy identity.
        def generators(data):
            return {wave:{key:value for key,value in values.items() if key!='collection_sha256'}
                    for wave,values in data['collection_episode_generator_states'].items()}
        comparisons[f'update{update}_checkpoint']['episode_generator_states']=exact(generators(a),generators(b))
    assert all(all(values.values()) for values in comparisons.values())
    partial,_=bundle(ROOT/'trainer-cpu-partial-04/failed-partial-not-resumable.pt')
    assert not partial['complete_update_boundary'] and partial['optimizer_steps_total']==1
    return dict(passed=True,scope='CPU fake-engine barrier end-to-end, independently regenerated environments; no CUDA/native strategic-strength claim',
        optimizer_steps_this_process={name:stage['optimizer_steps_this_run'] for name,stage in stages.items()},
        unique_fake_environments=len(run_dirs),unique_agent_directories=len(agents),unique_wave_batch_tokens=len(tokens),
        unique_fake_lab_roots=len(labs),independent_environment_evidence=worker_records,
        comparisons=comparisons,partial_rejected_complete_flag=False,partial_actual_steps=1,
        protocol_sha256=next(iter(protocol_hashes)),archived_batch_substitution_used=False)


def live_batch_processes(token):
    matches=[]
    for directory in Path('/proc').iterdir():
        if not directory.name.isdigit():
            continue
        try:
            environment=(directory/'environ').read_bytes().split(b'\0')
            if ('LAB_THROUGHPUT_BATCH='+token).encode() in environment:
                matches.append(int(directory.name))
        except (OSError,PermissionError):
            pass
    return matches


def audit_native():
    root=ROOT/'native-collect-02';result=read(root/'batch.json');plan=read(root/'plan.json')
    assert not result['synthetic'] and result['status']=='complete_on_policy_batch' and result['accepted_samples']==572
    assert result['actual_optimizer_steps']==0 and result['policy_unchanged'] and not result['remaining_processes']
    rows=lines(root/'accepted-rollout.jsonl')
    assert len(rows)==572
    source_checkpoint=next(path for path in plan['hashes'] if path.endswith('.pt'))
    saved,saved_sha=bundle(source_checkpoint)
    policy_digest=tensor_digest(saved['state_dict'])
    assert saved_sha==plan['checkpoint_sha256'] and policy_digest==plan['policy_tensor_sha256']
    boundary,_=bundle(root/'collection-boundary.pt')
    assert boundary['policy_tensor_sha256']==policy_digest and boundary['training_updates']==0
    episodes=[]
    for episode in result['episodes']:
        index=episode['episode_index'];env=root/f'env-{index:03d}';agent=env/'agent';run=Path(episode['native']['run_dir'])
        native=episode['native'];commits=lines(env/'committed.jsonl');choices=lines(run/'strategy-decisions.jsonl')
        selected=[row for row in rows if row['episode_index']==index]
        assert len(selected)==len(commits)==len(choices)==episode['decisions']
        trace=lines(run/'strategy-trace.jsonl');events=Counter(event['event'] for event in trace)
        assert events['before_move']==events['move_applied']==len(selected)
        assert all(events[event]==0 for event in ('move_failed','economy_failed','query_failed'))
        log=(run/'client.log').read_text(errors='replace')
        replies=[int(value) for value in re.findall(r'DirectorAI: step finished result=(\d+)',log)]
        assert len(replies)==len(selected) and all(value in (1,3) for value in replies)
        rejected=[line for line in log.splitlines() if 'has to answer queries' in line or 'Got false in applying' in line or
                  re.search(r'(?:QueryReply|query reply).*?(?:failed|success=0|result=0)',line,re.I)]
        assert not rejected and 'external policy failed' not in log
        assert sha(run/'client.log')==native['log_sha256'] and sha(run/'strategy-trace.jsonl')==native['strategy_trace_sha256']
        assert sha(run/'strategy-decisions.jsonl')==native['strategy_decisions_sha256']
        for number,(row,commit,choice) in enumerate(zip(selected,commits,choices),1):
            request=read(agent/f'request-{number:08d}.json');action=int((agent/f'action-{number:08d}.json').read_text())
            assert row['request']==commit['request']==request
            assert sha(agent/f'request-{number:08d}.json')==row['request_sha256']
            assert row['action']==commit['action']==choice['selected_candidate']==action
            assert choice['candidates']==request['candidates']
            assert all(choice[key]==request[key] for key in ('player','day','hero','from'))
            assert choice['destination']==request['candidates'][action]['position'] and choice['step']==request['candidates'][action]['next']
            assert row['policy_tensor_sha256']==policy_digest and row['checkpoint_sha256']==saved_sha
        audit=episode['native_event_audit']
        assert audit['missing_ack_count']==audit['missing_execution_reply_count']==0 and audit['terminal_unconfirmed_action_indices']==[]
        episodes.append(dict(episode_id=episode['episode_id'],role='red' if index==0 else 'blue',decisions=len(selected),
            actual_move_result_1_displacements=replies.count(1),actual_move_result_3_blocking_visits=replies.count(3),
            move_applied_ACKs=events['move_applied'],unconfirmed_final_actions=0,server_rejections=0,
            winner=native['winner'],run_dir=str(run),client_log_sha256=sha(run/'client.log'),
            source_snapshot=[dict(path=str(path),sha256=sha(path)) for path in (run/'source-snapshot').glob('*') if path.is_file()]))
    live=live_batch_processes(plan['token']);assert not live
    # Explicitly record historical source hashes. Later legal native revisions do
    # not retroactively invalidate a completed run or demand live-tree equality.
    return dict(passed=True,scope='Actual 2-environment CUDA inference/native collection, no optimizer',samples=572,episodes=episodes,
        checkpoint_sha256=saved_sha,policy_tensor_sha256=policy_digest,actual_optimizer_steps=0,
        manager_policy_unchanged_at_collection_boundary=True,live_owned_batch_processes=live,
        recorded_remaining_processes=result['remaining_processes'],old_plan_frozen_hashes=plan['hashes'],
        unchanged_parent_checkpoint_verified_now=True,
        limitations='Blocking visits are executed interactions, not tile displacements. Only EmptyAI paired roles; no NK or independent strength claim. '
                    'Manager unchanged is supported by its before/after digest gate and saved boundary, not an after-exit RAM observation. '
                    'This old native snapshot precedes later query-ACK gate changes; no assertion that newer runtime files have the old hashes.')


def audit_clean_prior():
    path=EXPERIMENTS/'strategic-policy-v2/checkpoints/threat-supply-clean-prior-v3.pt'
    data,digest=bundle(path)
    assert digest.startswith('6ced669')
    assert data['training_updates']==data['optimizer_steps_total']==0 and data['optimizer'] is None
    assert not bool(data['trained'])
    assert all(bool(data['state_dict'][name].eq(0).all()) for name in ('actor.4.weight','actor.4.bias'))
    parent=Path(data['lineage']['parent_checkpoint'])
    assert sha(parent)==data['lineage']['parent_sha256']
    return dict(sha256=digest,path=str(path),trained=False,optimizer_steps=0,training_updates=0,
                actor_residual_output_zero=True,lineage=data['lineage'],historical_learned_checkpoint_preserved=True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=False);torch.set_num_threads(1)
    report=dict(passed=True,audit_GPU_initialized=False,audit_game_started=False,audit_optimizer_steps=0,
                cpu04=audit_cpu(),native02=audit_native(),clean_prior=audit_clean_prior())
    assert not torch.cuda.is_initialized()
    report['audit_source_sha256']=sha(Path(__file__))
    (args.out/'AUDIT.json').write_text(json.dumps(report,indent=2))
    (args.out/Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    print(json.dumps(dict(passed=True,CPU04_scope=report['cpu04']['scope'],independent_fake_environments=report['cpu04']['unique_fake_environments'],
        native_samples=report['native02']['samples'],native_execution_counts=report['native02']['episodes'],
        clean_prior=report['clean_prior']),indent=2))


if __name__=='__main__':
    main()
