"""Four EmptyAI mechanism games, then eight NK development games; no auto training."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import time
import traceback
from audit_economy_raw import audit_economy,sha

HERE=Path(__file__).resolve().parent
V2=HERE.parent/'strategic-policy-v2'
sys.path.insert(0,str(V2))
from run_supply_pilot import frozen_inputs,verify,atomic,terminate_owned,CHECKPOINT,MAPS


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--expected-broker-sha',required=True)
    p.add_argument('--expected-native-lib-sha',required=True)
    p.add_argument('--seconds',type=int,default=120)
    args=p.parse_args()
    assert not args.out.exists(),'New output directory required; do not mix protocols'
    assert sha(V2/'broker.py')==args.expected_broker_sha
    native_lib=Path('/root/heroes3-ai-lab/src/vcmi-adv-build/bin/libvcmi.so')
    assert sha(native_lib)==args.expected_native_lib_sha,'Native build differs from scheduled completed version'
    frozen=frozen_inputs(CHECKPOINT)
    extra=set(HERE.glob('*.py'))|{HERE/'PLAN.md',HERE/'EXPERIMENT_PROTOCOL.md'}
    extra|=set((native_lib.parent/'config').rglob('*.json'))
    frozen.update({str(path):sha(path)for path in sorted(extra)})
    args.out.mkdir(parents=True);snap=args.out/'source-snapshot';snap.mkdir()
    for i,(path,checksum)in enumerate(frozen.items()):
        f=Path(path)
        if f.suffix in ('.py','.cpp','.h','.md','.json'):
            (snap/f'{i:03d}-{f.name}').write_bytes(f.read_bytes())
    protocol=dict(schema='economy-v4-acceptance-protocol-v1',frozen=frozen,
        checkpoint=str(CHECKPOINT),checkpoint_sha256=sha(CHECKPOINT),maps=MAPS,
        engineering_seed=2026101860,nk_seeds=[2026101861,2026101862],
        expected_broker_sha=args.expected_broker_sha,expected_native_lib_sha=args.expected_native_lib_sha,
        mode='legacy-policy',scripted_economy=True,training_updates=0,independent_evaluation=False)
    atomic(args.out/'PROTOCOL.json',protocol)
    state=dict(schema='economy-v4-acceptance-execution-v1',status='running',episodes=[],
        scripted_economy=True,learned_improvement=False,bc_eligible=0)
    start=time.monotonic();current=None;proc=None
    try:
        for stage,opponent,seeds in [('engineering','EmptyAI',(2026101860,)),('nk-development','Nullkiller2',(2026101861,2026101862))]:
            if stage=='nk-development':
                engineering=[r for r in state['episodes']if r['stage']=='engineering']
                assert len(engineering)==4
                if not all(r['mechanism_gate_passed']for r in engineering):
                    state.update(status='engineering_gate_failed',nk_games_started=0,wall_seconds=time.monotonic()-start)
                    atomic(args.out/'EXECUTION.json',state)
                    print(json.dumps(dict(status=state['status'],reason='Valid native games did not all demonstrate required military development')),flush=True)
                    return 2
            for map_index,mapname in enumerate(MAPS):
                for role in ('red','blue'):
                    for seed in seeds:
                        verify(frozen)
                        current=f'{stage}-map{map_index}-{role}-{seed}'
                        game=args.out/current;game.mkdir()
                        cmd=[sys.executable,str(V2/'smoke_game.py'),'--map',mapname,'--red',
                            'DirectorAI'if role=='red'else opponent,'--blue',
                            'DirectorAI'if role=='blue'else opponent,'--seed',str(seed),
                            '--mode','legacy-policy','--checkpoint',str(CHECKPOINT),
                            '--seconds',str(args.seconds),'--tag','economy-v4-'+current]
                        with (game/'smoke.log').open('w')as log:
                            proc=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                            code=proc.wait()
                        text=(game/'smoke.log').read_text(errors='replace')
                        match=re.search(r'^AGENT_DIR=(.+)$',text,re.M)
                        if match:
                            source=Path(match[1].strip())/'smoke-result.json'
                            if source.exists():(game/'smoke-result.json').write_bytes(source.read_bytes())
                        assert code==0,f'Native/protocol game failed: {game}'
                        verify(frozen)
                        audit=audit_economy(game/'smoke-result.json')
                        atomic(game/'RAW_AUDIT.json',audit)
                        raw=audit['raw']
                        row=dict(tag=current,stage=stage,map=mapname,role=role,seed=seed,
                            audit=str(game/'RAW_AUDIT.json'),won=raw['won'],native_days=raw['native_days'],
                            original_main_loss_day=raw['original_main_loss_day'],original_main_status=raw['original_main_status'],
                            delivered_count=raw['delivered_count'],delivered_to_main_count=raw['delivered_to_main_count'],
                            mechanism_gate_passed=audit['mechanism_gate_passed'],
                            first_building33=audit['first_building33'],first_building32=audit['first_building32'],
                            recruited_types=audit['recruited_creature_types'],transferred_types=audit['transferred_creature_types'])
                        state['episodes'].append(row);atomic(args.out/'EXECUTION.json',state)
                        print(json.dumps(row),flush=True)
        state.update(status='completed',wall_seconds=time.monotonic()-start,
            engineering_games=4,nk_games=8,nk_wins=sum(r['won']for r in state['episodes']if r['stage']=='nk-development'))
        verify(frozen);atomic(args.out/'EXECUTION.json',state)
        return 0
    except BaseException:
        if proc is not None:terminate_owned(proc)
        state.update(status='failed',failed_episode=current,error=traceback.format_exc(),wall_seconds=time.monotonic()-start)
        atomic(args.out/'EXECUTION.json',state)
        raise


if __name__=='__main__':raise SystemExit(main())
