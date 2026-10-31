"""Exactly the registered 16 games; no action at import/help, new output only."""
import argparse
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
import traceback
from audit_supply_raw import sha,audit_episode

HERE=Path(__file__).resolve().parent
LAB=Path('/root/heroes3-ai-lab')
CHECKPOINT=HERE.parent/'strategic-policy-v1/takeover-03/native-boundary-01/continuous-2/update-2.pt'
CHECKPOINT_SHA='f524796161915cb43ae9e228f13dd72c195df016ce5d2c25dab7d8a7d2aeb7cc'
POLICY_SHA='20b3bb7c3797b311bbda315fe9d5f2c911bea8ed3a5b8c39668c47311ffb88fa'
MAPS=('Maps/adv/takeover-v2-train-01-mines','Maps/adv/takeover-v2-train-02-development')


def atomic(path,result):
    temp=path.with_suffix(path.suffix+'.tmp');temp.write_text(json.dumps(result,indent=2,ensure_ascii=False));os.replace(temp,path)


def terminate_owned(proc):
    # Processes created by smoke include separate native/broker sessions. Limit
    # cleanup to descendants found from this exact still-owned child PID.
    if proc.poll() is not None:return
    descendants={proc.pid}
    for _ in range(8):
        before=len(descendants)
        for entry in Path('/proc').iterdir():
            if not entry.name.isdigit():continue
            try:
                status=(entry/'status').read_text();parent=int(re.search(r'^PPid:\s+(\d+)',status,re.M)[1])
                if parent in descendants:descendants.add(int(entry.name))
            except (OSError,TypeError):continue
        if len(descendants)==before:break
    for pid in sorted(descendants,reverse=True):
        try:os.kill(pid,signal.SIGTERM)
        except ProcessLookupError:pass
    try:proc.wait(timeout=12)
    except subprocess.TimeoutExpired:
        for pid in sorted(descendants,reverse=True):
            try:os.kill(pid,signal.SIGKILL)
            except ProcessLookupError:pass
        proc.wait()


def frozen_inputs(checkpoint):
    assert sha(checkpoint)==CHECKPOINT_SHA,'Pilot requires the registered pre-migration parent checkpoint'
    files=set(HERE.glob('*.py'))|{HERE/'SUPPLY_PREREGISTRATION.md',checkpoint,HERE.parent/'adventure_runner_v5.py'}
    files|={HERE.parent/'strategic-policy-v1'/name for name in ('encoder.py','model.py')}
    build=LAB/'src/vcmi-adv-build'
    files|={build/'bin'/name for name in ('vcmiclient','vcmiserver','libvcmi.so')}
    files|=set((LAB/'src/vcmi-adv/AI/DirectorAI').glob('*.cpp'))|set((LAB/'src/vcmi-adv/AI/DirectorAI').glob('*.h'))
    files|={LAB/'data/vcmi'/(name+'.vmap') for name in MAPS}
    assert sha(HERE/'supply_policy.py')==POLICY_SHA,'Supply policy changed after CPU/pre-registration'
    return {str(path):sha(path) for path in sorted(files)}


def verify(frozen):assert all(sha(Path(p))==h for p,h in frozen.items()),'Frozen input changed; stop pilot'


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True)
    p.add_argument('--checkpoint',type=Path,default=CHECKPOINT);p.add_argument('--seconds',type=int,default=90)
    p.add_argument('--expected-broker-sha',required=True,help='Stable broker SHA supplied after integration freeze')
    args=p.parse_args();assert not args.out.exists(),'Fresh output directory required'
    assert sha(HERE/'broker.py')==args.expected_broker_sha,'Broker differs from scheduled stable version'
    frozen=frozen_inputs(args.checkpoint.resolve())
    args.out.mkdir(parents=True)
    snapshot=args.out/'source-snapshot';snapshot.mkdir()
    for i,(path,checksum) in enumerate(frozen.items()):
        source=Path(path)
        if source.suffix in ('.py','.h','.cpp','.md'):
            (snapshot/f'{i:03d}-{source.name}').write_bytes(source.read_bytes())
    atomic(args.out/'PROTOCOL.json',dict(schema='supply-pilot-protocol-v1',frozen=frozen,maps=MAPS,
        seeds=[2026101851,2026101852],modes=['legacy-policy','supply-aware'],checkpoint=str(args.checkpoint.resolve()),
        expected_broker_sha=args.expected_broker_sha,seconds=args.seconds,independent_evaluation=False,bc_eligible=False))
    status=dict(schema='supply-pilot-execution-v1',status='running',episodes=[],independent_evaluation=False,bc_eligible=False)
    current=None;proc=None;started=time.monotonic()
    try:
        for map_index,mapname in enumerate(MAPS):
            for role in ('red','blue'):
                for seed in (2026101851,2026101852):
                    for mode in ('legacy-policy','supply-aware'):
                        verify(frozen)
                        current=f'map{map_index}-{role}-{seed}-{mode}'
                        game=args.out/current;game.mkdir()
                        cmd=[sys.executable,str(HERE/'smoke_game.py'),'--map',mapname,'--seed',str(seed),
                            '--red','DirectorAI' if role=='red' else 'Nullkiller2',
                            '--blue','DirectorAI' if role=='blue' else 'Nullkiller2','--mode',mode,
                            '--checkpoint',str(args.checkpoint.resolve()),'--seconds',str(args.seconds),'--tag','supply-'+current]
                        with (game/'smoke.log').open('w') as log:
                            proc=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                            code=proc.wait()
                        text=(game/'smoke.log').read_text(errors='replace')
                        match=re.search(r'^AGENT_DIR=(.+)$',text,re.M)
                        if match:
                            native_summary=Path(match[1].strip())/'smoke-result.json'
                            if native_summary.exists():(game/'smoke-result.json').write_bytes(native_summary.read_bytes())
                        assert code==0,f'Game returned {code}: {game}'
                        verify(frozen)
                        result=audit_episode(game/'smoke-result.json')
                        atomic(game/'RAW_AUDIT.json',result)
                        status['episodes'].append(dict(tag=current,audit=str(game/'RAW_AUDIT.json'),
                            map=mapname,role=role,seed=seed,mode=mode,won=result['won'],
                            original_main_status=result['original_main_status'],original_main_loss_day=result['original_main_loss_day'],
                            delivered_count=result['delivered_count'],delivered_to_main_count=result['delivered_to_main_count'],
                            override_count=result['override_count'],single_candidate_decisions=result['single_candidate_decisions']))
                        atomic(args.out/'EXECUTION.json',status)
                        print(json.dumps(status['episodes'][-1]),flush=True)
        pairs=[]
        for mapname in MAPS:
            for role in ('red','blue'):
                for seed in (2026101851,2026101852):
                    rows={r['mode']:r for r in status['episodes']if (r['map'],r['role'],r['seed'])==(mapname,role,seed)}
                    b,c=rows['legacy-policy'],rows['supply-aware']
                    raw_b=json.loads(Path(b['audit']).read_text());raw_c=json.loads(Path(c['audit']).read_text())
                    assert raw_b['initial_state_sha256']==raw_c['initial_state_sha256'],'Paired starting state mismatch'
                    pairs.append(dict(map=mapname,role=role,seed=seed,delta_wins=c['won']-b['won'],
                        baseline_main_status=b['original_main_status'],supply_main_status=c['original_main_status'],
                        baseline_main_loss_day=b['original_main_loss_day'],supply_main_loss_day=c['original_main_loss_day'],
                        delta_delivered_count=c['delivered_count']-b['delivered_count'],
                        delta_delivered_to_main_count=c['delivered_to_main_count']-b['delivered_to_main_count']))
        status.update(status='completed',pairs=pairs,net_wins=sum(r['delta_wins'] for r in pairs),
            delta_delivered_to_main_count=sum(r['delta_delivered_to_main_count'] for r in pairs),
            wall_seconds=time.monotonic()-started,certified=False,ability_improvement_proven=False)
        verify(frozen);atomic(args.out/'EXECUTION.json',status)
    except BaseException:
        if proc is not None:terminate_owned(proc)
        status.update(status='failed',failed_episode=current,error=traceback.format_exc(),wall_seconds=time.monotonic()-started)
        atomic(args.out/'EXECUTION.json',status)
        raise


if __name__=='__main__':main()
