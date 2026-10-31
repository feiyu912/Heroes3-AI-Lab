#!/usr/bin/env python3
"""Strict completed parallel-trainer comparison. Reads CPU tensors only; launches nothing."""
import argparse
from collections import Counter
import hashlib
import io
import json
import math
from pathlib import Path
import re
import traceback

import torch


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def bundle(path):
    raw=Path(path).read_bytes()
    return torch.load(io.BytesIO(raw),map_location='cpu',weights_only=True),hashlib.sha256(raw).hexdigest()


def rows(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines()]


def tensor_sha(state):
    digest=hashlib.sha256()
    for name,value in sorted(state.items()):
        value=value.cpu().contiguous()
        digest.update(name.encode());digest.update(str(value.dtype).encode());digest.update(str(tuple(value.shape)).encode())
        digest.update(value.numpy().tobytes())
    return digest.hexdigest()


def differences(a,b,path='root',limit=8):
    result=[]
    def visit(x,y,key):
        if len(result)>=limit:return
        if isinstance(x,torch.Tensor):
            if not isinstance(y,torch.Tensor) or x.shape!=y.shape or x.dtype!=y.dtype or not torch.equal(x,y):
                maximum=float((x.double()-y.double()).abs().max()) if isinstance(y,torch.Tensor) and x.shape==y.shape and x.numel() else None
                result.append(dict(path=key,reason='tensor differs',max_abs=maximum if maximum is None or math.isfinite(maximum) else str(maximum)))
        elif isinstance(x,dict) and isinstance(y,dict):
            if x.keys()!=y.keys():result.append(dict(path=key,reason='keys differ'))
            for child in sorted(x.keys() & y.keys(),key=str):visit(x[child],y[child],key+'.'+str(child))
        elif isinstance(x,(tuple,list)) and isinstance(y,type(x)):
            if len(x)!=len(y):result.append(dict(path=key,reason='length differs',left=len(x),right=len(y)))
            for index,(xx,yy) in enumerate(zip(x,y)):
                visit(xx,yy,key+'['+str(index)+']')
                if len(result)>=limit:break
        elif type(x)!=type(y) or x!=y:
            result.append(dict(path=key,reason='scalar differs',left=repr(x)[:160],right=repr(y)[:160]))
    visit(a,b,path)
    return result


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def audit_native_episode(episode,wave,require_native):
    index=episode['episode_index'];agent=wave/f'env-{index:03d}/agent'
    saved=rows(wave/f'env-{index:03d}/committed.jsonl')
    assert episode['valid'] and episode['native_consumption_verified'] and episode['native']['completed'] and episode['native']['inputs_unchanged']
    assert episode['reward'] in (-1.,1.) and len(saved)==episode['decisions']>0
    native_audit=episode['native_event_audit']
    assert native_audit['valid'] and not native_audit.get('terminal_unconfirmed_action_indices')
    native=episode['native'];config=episode['config']
    role='red' if config['red']=='DirectorAI' else 'blue'
    assert native['winner'] in ('red','blue') and episode['reward']==(1. if native['winner']==role else -1.)
    assert native['actual_ai']=={color:config[color] for color in ('red','blue')}
    for row in saved:
        number=row['request']['request_id'];request_path=agent/f'request-{number:08d}.json';action_path=agent/f'action-{number:08d}.json'
        assert read(request_path)==row['request'] and sha(request_path)==row['request_sha256']
        assert int(action_path.read_text())==row['action']
    if require_native:
        native=episode['native'];run=Path(native['run_dir'])
        choices=rows(run/'strategy-decisions.jsonl');state=rows(run/'strategy-trace.jsonl')
        assert len(choices)==len(saved)
        assert sha(run/'client.log')==native['log_sha256'] and sha(run/'strategy-decisions.jsonl')==native['strategy_decisions_sha256']
        assert sha(run/'strategy-trace.jsonl')==native['strategy_trace_sha256']
        counts=Counter(event['event'] for event in state)
        assert all(counts[key]==0 for key in ('move_failed','economy_failed','query_failed'))
        log=(run/'client.log').read_text(errors='replace')
        replies=[int(value) for value in re.findall(r'DirectorAI: step finished result=(\d+)',log)]
        assert all(value in (1,3) for value in replies),'Native movement failure or unsupported movement result'
        if len(replies)==len(saved):
            assert counts['move_applied']==len(saved) or (counts['move_applied']==len(saved)-1 and native_audit['terminal_ack_missing_after_execution'])
        else:
            proof=native_audit.get('terminal_native_visit_execution_proof')
            assert len(replies)==len(saved)-1 and proof,'A sampled action lacks native execution evidence'
            last=saved[-1];candidate=last['request']['candidates'][last['action']]
            assert proof['action_index']==len(saved)-1 and proof['target']==candidate['position'] and proof['kind']==candidate['kind']
            raw=log.splitlines()
            assert 'wants to move hero '+str(last['request']['hero']) in raw[proof['server_request_line']-1]
            assert 'Hero '+proof['native_hero']+' visits ' in raw[proof['hero_visit_line']-1]
            assert any(marker in raw[proof['battle_or_capture_outcome_line']-1] for marker in ('BattleResult','SetObjectProperty','ChangeObjectOwner'))
        assert not any(text in log for text in ('has to answer queries','Got false in applying','external policy failed'))
        assert not re.search(r'(?:QueryReply|query reply).*?(?:failed|success=0|result=0)',log,re.I)
        for sample,choice in zip(saved,choices):
            request=sample['request'];candidate=request['candidates'][sample['action']]
            assert choice['selected_candidate']==sample['action'] and choice['candidates']==request['candidates']
            assert all(choice[key]==request[key] for key in ('player','day','hero','from'))
            assert choice['destination']==candidate['position'] and choice['step']==candidate['next']
    native=episode['native']
    return dict(config=episode['config'],episode_id=episode['episode_id'],reward=episode['reward'],decisions=episode['decisions'],
        native={key:native.get(key) for key in ('completed','winner','actual_ai','turns','moves_requested','move_replies',
            'displacement_replies','blocking_visit_replies','failed_move_replies')},
        native_execution_audit={key:native_audit.get(key) for key in ('counts','expected_actions','missing_ack_count',
            'missing_execution_reply_count','terminal_ack_missing_after_execution','classification','terminal_unconfirmed_action_indices')})


def audit_stage(directory,expected_updates,device,synthetic):
    report=read(directory/'training.json');plan=read(directory/'plan.json');recipe=read(directory/'protocol.json')
    assert report['status']=='completed' and report['synthetic']==synthetic
    assert report['device'].split(':')[0]==device and plan['device'].split(':')[0]==device
    assert recipe['sha256']==plan['protocol_sha256']==canonical_hash(recipe['protocol'])
    assert recipe['protocol']['synthetic']==synthetic,'Requested synthetic/real scope differs from protocol'
    assert recipe['protocol']['inference_schedule']=='barrier','Exact regeneration comparator requires registered barrier inference'
    for filename,digest in recipe['protocol']['hashes'].items():
        source=Path(filename)
        if source.suffix in ('.py','.cpp','.h'):
            snapshots=list((directory/'source-snapshot').glob('*-'+source.name))
            assert any(sha(path)==digest for path in snapshots),'Source snapshot missing/mismatched: '+filename
    assert [update['update'] for update in report['updates']]==expected_updates
    assert report['optimizer_steps_this_run']==sum(update['metrics']['optimizer_steps'] for update in report['updates'])>0
    assert report['CUDA_training']==(device=='cuda') and report['CPU_training']==(device=='cpu')
    by_update={}
    all_episode_ids=set()
    for update in expected_updates:
        selected=[];episodes=[];policy_hashes=set();versions=set();wave_evidence=[]
        for wave in sorted(directory.glob(f'update-{update:03d}-wave-*')):
            wave_plan=read(wave/'plan.json');batch=read(wave/'batch.json')
            assert wave_plan['synthetic']==synthetic and wave_plan['inference_schedule']=='barrier'
            assert wave_plan['device'].split(':')[0]==device
            assert batch['status']=='complete_on_policy_batch' and batch['actual_optimizer_steps']==0
            assert batch['policy_unchanged'] and batch['inputs_unchanged'] and not batch['remaining_processes']
            current=directory/f'update-{update-1}.pt'
            assert wave_plan['checkpoint_sha256']==sha(current)
            parent,_=bundle(current);assert tensor_sha(parent['state_dict'])==wave_plan['policy_tensor_sha256']
            accepted=rows(wave/'accepted-rollout.jsonl');selected.extend(accepted)
            assert batch['accepted_samples']==len(accepted)
            certified={episode['episode_id']:episode for episode in batch['episodes']}
            for row in accepted:
                assert row['model_device'].split(':')[0]==device and row['checkpoint_sha256']==wave_plan['checkpoint_sha256']
                assert row['policy_tensor_sha256']==wave_plan['policy_tensor_sha256'] and row['policy_version']==wave_plan['policy_version']
                assert row['episode_id'] in certified and row['return']==certified[row['episode_id']]['reward']
                assert row['episode_index']==certified[row['episode_id']]['episode_index']
                assert all(isinstance(row[key],(int,float)) and not isinstance(row[key],bool) and math.isfinite(row[key])
                           for key in ('old_logprob','old_value'))
            policy_hashes.add(wave_plan['policy_tensor_sha256']);versions.add(wave_plan['policy_version'])
            for episode in batch['episodes']:
                assert episode['episode_id'] not in all_episode_ids
                all_episode_ids.add(episode['episode_id'])
                episodes.append(audit_native_episode(episode,wave,not synthetic))
            boundary,_=bundle(wave/'collection-boundary.pt')
            assert boundary['complete_collection_boundary'] and boundary['policy_tensor_sha256']==wave_plan['policy_tensor_sha256']
            wave_evidence.append(dict(path=str(wave),batch_token=wave_plan['token'],policy_hash=wave_plan['policy_tensor_sha256'],
                collection_episode_RNG=boundary['episode_generator_states']))
        assert len(policy_hashes)==len(versions)==1
        cell=Counter((episode['config']['map'],episode['config']['red'],episode['config']['blue']) for episode in episodes)
        assert len(cell)==8 and len(set(cell.values()))==1
        expected_count=24 if recipe['protocol']['environments']==24 else 8
        assert len(episodes)==expected_count
        by_update[update]=dict(rows=selected,episodes=episodes,waves=wave_evidence)
    completed=expected_updates[-1];last,digest=bundle(directory/f'update-{completed}.pt')
    assert last['complete_update_boundary'] and last['training_updates']==completed
    assert last['optimizer_steps_total']==report['optimizer_steps_total']
    assert last['protocol_sha256']==recipe['sha256'] and not differences(last['protocol'],recipe['protocol'])
    if device=='cuda':assert last['cuda_rng'] and all(isinstance(state,torch.Tensor) and state.numel()>0 for state in last['cuda_rng'])
    return dict(report=report,plan=plan,recipe=recipe,by_update=by_update,last=last,last_sha256=digest)


def compare(continuous,split,resume,device='cuda',synthetic=False):
    a=audit_stage(continuous,[1,2],device,synthetic);b=audit_stage(split,[1],device,synthetic);c=audit_stage(resume,[2],device,synthetic)
    checks={}
    def check(name,left,right):
        diff=differences(left,right);checks[name]=dict(equal=not diff,differences=diff)
    check('source_protocol_continuous_split',a['recipe'],b['recipe']);check('source_protocol_continuous_resume',a['recipe'],c['recipe'])
    check('initialization_continuous_split',a['recipe']['protocol']['initialization'],b['recipe']['protocol']['initialization'])
    lineage=c['last']['lineage'];parent_path=split/'update-1.pt'
    assert lineage['mode']=='resume' and Path(lineage['parent_checkpoint']).resolve()==parent_path.resolve()
    assert lineage['parent_sha256']==sha(parent_path) and not lineage['reset_optimizer'] and not lineage['reset_rng']
    assert Path(c['plan']['resumed_from']).resolve()==parent_path.resolve()
    assert c['plan']['origin_sha256']==sha(parent_path)
    start=next(iter(a['report']['updates']))['update']-1
    zero_a,_=bundle(continuous/f'update-{start}.pt');zero_b,_=bundle(split/f'update-{start}.pt')
    for field in ('state_dict','optimizer','torch_rng','cuda_rng','python_rng','training_updates','optimizer_steps_total'):
        check('initial_boundary.'+field,zero_a[field],zero_b[field])
    row_fields=('request','action','old_logprob','old_value','return','generator_seed','policy_version','episode_id','policy_tensor_sha256')
    checkpoint_fields=('state_dict','optimizer','torch_rng','cuda_rng','python_rng','training_updates','optimizer_steps_total',
        'complete_update_boundary','encoder_version','state_dim','candidate_dim','protocol','protocol_sha256','policy_tensor_sha256')
    for update,other in ((1,b),(2,c)):
        left=a['by_update'][update];right=other['by_update'][update]
        for field in row_fields:check(f'update{update}.rollout.{field}',[row[field] for row in left['rows']],[row[field] for row in right['rows']])
        check(f'update{update}.episodes',left['episodes'],right['episodes'])
        check(f'update{update}.collection_RNG',[wave['collection_episode_RNG'] for wave in left['waves']],
                                              [wave['collection_episode_RNG'] for wave in right['waves']])
        first,_=bundle(continuous/f'update-{update}.pt');second,_=bundle((split if update==1 else resume)/f'update-{update}.pt')
        for field in checkpoint_fields:check(f'update{update}.checkpoint.{field}',first[field],second[field])
    return dict(passed_exact=all(item['equal'] for item in checks.values()),checks=checks,device_required=device,synthetic=synthetic,
        independent_native_strength_evaluation=False,
        optimizer_steps=dict(continuous=a['report']['optimizer_steps_this_run'],split=b['report']['optimizer_steps_this_run'],
            resume=c['report']['optimizer_steps_this_run']),
        source_protocol_sha256=a['recipe']['sha256'],initialization=a['recipe']['protocol']['initialization'],resume_lineage=lineage,
        limitations='Exact scoped comparison only; no tolerance silently promotes differences. Native game evidence checked for CUDA runs. '
                    'Checkpoint file bytes may differ due lineage; all tensors, Adam, RNG and source protocol are compared. '
                    'Completed-boundary recovery does not certify mid-game recovery or strategic ability.')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--continuous',required=True,type=Path);parser.add_argument('--split',required=True,type=Path)
    parser.add_argument('--resume',required=True,type=Path);parser.add_argument('--out',required=True,type=Path)
    parser.add_argument('--device',choices=('cuda','cpu'),default='cuda')
    parser.add_argument('--synthetic',action='store_true')
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=False);torch.set_num_threads(1)
    try:
        report=compare(args.continuous.resolve(),args.split.resolve(),args.resume.resolve(),args.device,args.synthetic)
    except Exception as error:
        report=dict(passed_exact=False,validation_error=repr(error),validation_context=traceback.format_exc(),
                    device_required=args.device,synthetic=args.synthetic)
    assert not torch.cuda.is_initialized()
    report.update(audit_launches_games=False,audit_optimizer_steps=0,audit_CUDA_initialized=False,
                  comparator_sha256=sha(Path(__file__)))
    (args.out/'AUDIT.json').write_text(json.dumps(report,indent=2,allow_nan=False))
    (args.out/Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    print(json.dumps(dict(passed_exact=report['passed_exact'],validation_error=report.get('validation_error'),
                         failed_checks=[name for name,value in report.get('checks',{}).items() if not value['equal']]),indent=2))
    return 0 if report['passed_exact'] else 1


if __name__=='__main__':
    raise SystemExit(main())
