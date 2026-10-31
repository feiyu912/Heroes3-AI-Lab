#!/usr/bin/env python3
"""Frozen CPU argmax paired development evaluation; no optimizer, no test maps."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time
import uuid

from collect_vector import V2,LAB,THROUGHPUT,audit_native_events,validate,sha,write
from measure import clean,batch_processes

HERE=Path(__file__).resolve().parent
CLEAN=V2/'checkpoints/threat-supply-clean-prior-v3.pt'
MAPS=['Maps/adv/takeover-v2-dev-01-river','Maps/adv/takeover-v2-dev-02-reserves']


def verify_native_consumption(agent,native,expected_sha):
    ready=json.loads((agent/'broker-ready.json').read_text())
    if ready.get('model_version')!='sha256:'+expected_sha or ready.get('mode')!='new-policy':
        raise ValueError('Broker checkpoint/mode differs from frozen new-policy evaluation')
    events=[json.loads(line) for line in (agent/'broker-trace.jsonl').open()]
    committed=[e for e in events if e.get('event')=='decision_committed']
    responses=[e for e in events if e.get('event')=='response_written']
    if any(e.get('event')=='protocol_error' for e in events):
        raise ValueError('Broker protocol error')
    decisions=[json.loads(line) for line in (Path(native['run_dir'])/'strategy-decisions.jsonl').open()]
    count=len(committed)
    if not count or len(decisions)!=count or len(responses)!=count or len(list(agent.glob('request-????????.json')))!=count or len(list(agent.glob('action-????????.json')))!=count:
        raise ValueError('Request/response/native count mismatch or zero observations')
    rows=[]
    for number,(event,response,decision) in enumerate(zip(committed,responses,decisions),1):
        request_path=agent/f'request-{number:08d}.json'
        action_path=agent/f'action-{number:08d}.json'
        raw=request_path.read_bytes()
        request=validate(json.loads(raw),number)
        action=event['action']
        if type(action)is not int or not 0<=action<len(request['candidates']):
            raise ValueError('Illegal archived action')
        selected=request['candidates'][action]
        if not (event['request_id']==response['request_id']==number and response['action']==action and
                event['request_file']==request_path.name and event['action_file']==action_path.name and
                event['model_version']=='sha256:'+expected_sha and event['mode']=='new-policy' and
                sha(request_path)==event['request_sha256'] and sha(action_path)==event['response_sha256']==response['response_sha256'] and
                action_path.read_bytes()==f'{action}\n'.encode() and decision['selected_candidate']==action and
                decision['candidates']==request['candidates'] and
                all(decision[key]==request[key] for key in ('player','day','hero','from')) and
                decision['destination']==selected['position'] and decision['step']==selected['next']):
            raise ValueError(f'Native/broker byte/content consumption mismatch at request {number}')
        rows.append(dict(request=request,action=action,request_sha256=hashlib.sha256(raw).hexdigest()))
    event_audit=audit_native_events(Path(native['run_dir']),count,bool(native.get('completed')),rows[-1])
    if not event_audit['valid']:
        raise ValueError('Strict native execution/event gate failed: '+json.dumps(event_audit))
    return dict(decisions=count,native_event_audit=event_audit,last_request=rows[-1]['request'])


def jobs_for(seed_count,seed_base):
    return [dict(map=map_name,opponent=opponent,role=role,seed=seed_base+mi*10000+oi*100+ri*10+si)
            for mi,map_name in enumerate(MAPS) for oi,opponent in enumerate(('EmptyAI','Nullkiller2'))
            for ri,role in enumerate(('red','blue')) for si in range(seed_count)]


def summarize(rows,jobs):
    pairs=[]
    for index,job in enumerate(jobs):
        pair={row['model']:row for row in rows if row['pair_index']==index}
        if set(pair)!=set(('baseline','candidate')) or not all(row['valid'] for row in pair.values()):
            raise ValueError('Cannot certify an incomplete/invalid pair')
        turns={name:pair[name]['native'].get('native_calendar_last_day',pair[name]['native'].get('turns')) for name in pair}
        pairs.append(dict(job=job,baseline_win=pair['baseline']['win'],candidate_win=pair['candidate']['win'],
            win_delta=int(pair['candidate']['win'])-int(pair['baseline']['win']),turns=turns,
            candidate_minus_baseline_days=turns['candidate']-turns['baseline'] if None not in turns.values() else None))
    group={}
    for opponent in ('EmptyAI','Nullkiller2'):
        for role in ('red','blue'):
            group[f'{opponent}/{role}']={name:dict(games=sum(r['model']==name and r['job']['opponent']==opponent and r['job']['role']==role for r in rows),
                wins=sum(r['model']==name and r['job']['opponent']==opponent and r['job']['role']==role and r['win'] for r in rows)) for name in ('baseline','candidate')}
    return dict(pairs=pairs,net_win_delta=sum(pair['win_delta'] for pair in pairs),by_opponent_role=group,
        discordant_pairs=dict(candidate_only_wins=sum(p['win_delta']==1 for p in pairs),baseline_only_wins=sum(p['win_delta']==-1 for p in pairs)),
        distinct_map_count=2,statistical_independence_not_assumed=True,confidence_interval=None,
        limitation='Development maps were historically seen; paired games share two map clusters. No 8-independent-maps CI or final-test/strength certification.')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--candidate',type=Path,required=True)
    p.add_argument('--baseline',type=Path,default=CLEAN)
    p.add_argument('--execute',action='store_true',help='Default prepares protocol only, no games')
    p.add_argument('--seeds',type=int,default=1)
    p.add_argument('--seed-base',type=int,default=2026110300)
    p.add_argument('--seconds',type=int,default=90)
    a=p.parse_args()
    if not 1<=a.seeds<=10 or a.seconds<1:
        p.error('seeds 1..10 and positive seconds required')
    a.out.mkdir(parents=True,exist_ok=False)
    models={name:path.resolve() for name,path in [('baseline',a.baseline),('candidate',a.candidate)]}
    inputs=list(models.values())+[Path(__file__),HERE/'collect_vector.py',THROUGHPUT/'measure.py',THROUGHPUT/'worker_runner.py']
    inputs += [V2/name for name in ('smoke_game.py','broker.py','encoder.py','model.py','legacy.py')]
    inputs.append(HERE.parent/'adventure_runner_v5.py')
    binary=LAB/'src/vcmi-adv-build/bin'
    inputs += [binary/name for name in ('vcmiclient','vcmiserver','libvcmi.so')]
    inputs += [path for path in binary.rglob('*.so*') if path.is_file()]
    inputs += [path for path in (binary/'config').rglob('*') if path.is_file()]
    inputs += [path for path in (LAB/'data/vcmi/Mods').rglob('*.json') if path.is_file()]
    inputs += list((LAB/'src/vcmi-adv/AI/DirectorAI').glob('*.[ch]*'))
    inputs += [LAB/('data/vcmi/'+name+'.vmap') for name in MAPS]
    hashes={str(path):sha(path) for path in inputs}
    jobs=jobs_for(a.seeds,a.seed_base)
    plan=dict(schema='strict-new-policy-paired-dev-v1',execute=a.execute,models={k:str(v) for k,v in models.items()},
        hashes=hashes,jobs=jobs,run_order='Alternate baseline/candidate first by pair index; serial smoke games',
        mode='new-policy CPU argmax',independent_of_optimizer=True,test_split_touched=False,
        development_maps_previously_seen=True,pair_unit='same map,role,opponent,native seed',
        limitations='Two historically seen dev maps, clustered roles/seeds; no final-test claim or map-independent CI')
    write(a.out/'plan.json',plan)
    if not a.execute:
        write(a.out/'results.json',dict(status='prepared_only',games_started=0,optimizer_steps=0,test_split_touched=False))
        return 0
    snapshots=a.out/'sources';snapshots.mkdir()
    for index,path in enumerate(dict.fromkeys(inputs)):
        if path.suffix in ('.py','.cpp','.h','.json'):
            shutil.copy2(path,snapshots/f'{index:04d}-{path.name}')
    token=uuid.uuid4().hex
    report=dict(status='running',rows=[],scores_certified=False,independent_of_optimizer=True,
                development_maps_previously_seen=True,test_split_touched=False,optimizer_steps=0)
    write(a.out/'results.json',report)
    def frozen():
        return all(sha(Path(path))==value for path,value in hashes.items())
    def stop(*_):
        raise InterruptedError('Evaluation interrupted; stop without imputing losses')
    oldterm=signal.signal(signal.SIGTERM,stop);oldint=signal.signal(signal.SIGINT,stop)
    try:
        for index,job in enumerate(jobs):
            for name in (('baseline','candidate') if index%2==0 else ('candidate','baseline')):
                if not frozen():
                    raise RuntimeError('Frozen evaluation source/runtime/model changed')
                assigned=dict(red='DirectorAI' if job['role']=='red' else job['opponent'],
                              blue='DirectorAI' if job['role']=='blue' else job['opponent'])
                cmd=[sys.executable,str(V2/'smoke_game.py'),'--mode','new-policy','--checkpoint',str(models[name]),
                     '--map',job['map'],'--red',assigned['red'],'--blue',assigned['blue'],'--seed',str(job['seed']),
                     '--seconds',str(a.seconds),'--tag',f'dev-{a.out.name}-{index}-{name}']
                row=dict(pair_index=index,job=job,model=name,valid=False,win=None,native={},
                         agent_dir=None,verification=None,verification_error=None,status='running')
                report['rows'].append(row);write(a.out/'results.json',report)
                with (a.out/f'{index:03d}-{name}.log').open('w') as log:
                    proc=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,
                        env=dict(os.environ,LAB_THROUGHPUT_BATCH=token,CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='1'))
                    try:
                        code=proc.wait(timeout=a.seconds+60)
                    finally:
                        clean([proc],token)
                text=(a.out/f'{index:03d}-{name}.log').read_text()
                found=re.search(r'^AGENT_DIR=(.+)$',text,re.M)
                agent=Path(found[1].strip()) if found else None
                smoke=json.loads((agent/'smoke-result.json').read_text()) if agent and (agent/'smoke-result.json').exists() else {}
                native=smoke.get('native_result') or {}
                valid=bool(code==0 and smoke.get('passed') and native.get('completed') and native.get('inputs_unchanged') and
                    native.get('actual_ai')==assigned and native.get('winner') in ('red','blue'))
                audit=None;error=None
                if valid:
                    try:
                        audit=verify_native_consumption(agent,native,hashes[str(models[name])])
                    except Exception as problem:
                        valid=False;error=repr(problem)
                if not frozen() or batch_processes(token):
                    valid=False;error='Changed frozen inputs or stale evaluation processes'
                row.update(valid=valid,win=native.get('winner')==job['role'] if valid else None,
                         native=native,agent_dir=str(agent) if agent else None,verification=audit,verification_error=error,
                         status='completed' if valid else 'invalid')
                write(a.out/'results.json',report)
                if not valid:
                    raise RuntimeError('Invalid dev evaluation game; no loss imputation')
        report.update(summarize(report['rows'],jobs));report.update(status='completed',scores_certified=True)
    except BaseException as error:
        report.update(status='failed',error=repr(error),scores_certified=False)
        raise
    finally:
        signal.signal(signal.SIGTERM,oldterm);signal.signal(signal.SIGINT,oldint)
        write(a.out/'results.json',report)
    return 0


if __name__=='__main__':
    raise SystemExit(main())
