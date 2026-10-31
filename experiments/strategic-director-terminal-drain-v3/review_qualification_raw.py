"""Independent CPU-only reaudits of terminal qualification and prefix/ledger facts."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess

HERE=Path(__file__).resolve().parent
LAB=Path('/root/heroes3-ai-lab')
REPLAN=HERE.parent/'strategic-threat-replan-v2'
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
rows=lambda path:[json.loads(s) for s in path.read_text().splitlines()]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    original=LAB/'evaluations/typed-director-terminal-drain-qualification-01'
    qualification=json.loads((original/'RESULT.json').read_text());assert qualification['passed'] and len(qualification['games'])==3
    plan=json.loads((original/'PLAN.json').read_text());assert all(sha(Path(p))==h for p,h in plan['input_sha256'].items())
    args.out.mkdir(parents=True,exist_ok=False)
    inputs=[Path(__file__),original/'RESULT.json',original/'PLAN.json'];games=[]
    for game in qualification['games']:
        name=game['name'];root=original/name/'native';out=args.out/name;out.mkdir()
        commands=[['/usr/bin/python3',HERE/'audit_game_v6.py',root,out/'raw-audit'],
                  ['/usr/bin/python3',HERE/'audit_replan_v3.py',root,out/'raw-audit/AUDIT.json',out/'replan-audit'],
                  [LAB/'venv/bin/python',REPLAN/'audit_proxy.py',root,out/'replan-audit/AUDIT.json',out/'proxy-audit']]
        for index,command in enumerate(commands):
            result=subprocess.run(list(map(str,command)),capture_output=True,text=True,timeout=60)
            (out/f'audit-command-{index}.log').write_text(result.stdout+'\nSTDERR:\n'+result.stderr)
            assert result.returncode==0,(name,index,result.stderr)
        proof=json.loads((out/'raw-audit/AUDIT.json').read_text());assert proof['whole_game_valid']
        raw=(root/'client.log').read_text(errors='replace')
        registered={};acks={};generic={};sends=[]
        for number,line in enumerate(raw.splitlines(),1):
            line=re.sub(r'\x1b\[[0-9;]*m','',line)
            m=re.search(r'DirectorNativeRequestRegistered id=(\d+) player=(\d+) pack_type=(\d+) type=(\S+)$',line)
            if m:
                identity,owner,kind=map(int,m.groups()[:3]);assert identity not in registered
                registered[identity]=dict(owner=owner,pack_type=kind,type=m[4],line=number)
            m=re.search(r'DirectorNativeRequestAck id=(\d+) player=(\d+) pack_type=(\d+) success=([01])$',line)
            if m:
                identity,owner,kind,success=map(int,m.groups());assert identity not in acks and success==1
                acks[identity]=dict(owner=owner,pack_type=kind,line=number)
            m=re.search(r'(?<!Director)NativeRequestAck id=(\d+) player=(\d+) pack_type=(\d+) success=([01])$',line)
            if m:
                identity,owner,kind,success=map(int,m.groups());assert identity not in generic
                generic[identity]=dict(owner=owner,pack_type=kind,success=success,line=number)
            m=re.search(r'Sending a request "(\S+)"\. It.ll have an ID=(\d+)\.',line)
            if m:sends.append(dict(native_request_id=int(m[2]),type=m[1],line=number))
        owned=json.loads((root/'PLAN.json').read_text())['owned_player']
        assert set(registered)==set(acks)
        for identity,value in registered.items():
            assert value['owner']==acks[identity]['owner']==generic[identity]['owner']==owned
            assert value['pack_type']==acks[identity]['pack_type']==generic[identity]['pack_type']
            assert value['line']<generic[identity]['line']<acks[identity]['line']
        registry=proof['director_registry_proof'];cancelled=set(registry['actual_atomic_cleared_ids'])
        assert not cancelled & set(registered)
        assert set(s['native_request_id'] for s in sends)==set(generic)|cancelled
        assert len(sends)==len({s['native_request_id'] for s in sends})
        typed=rows(root/'typed.jsonl');policy=[e for e in typed if e['event']=='native_action_sent']
        bytype=Counter(value['type'] for value in registered.values())
        extra=[identity for identity in registered if identity not in {e['native_request_id'] for e in policy}]
        extra_types=Counter(registered[identity]['type'] for identity in extra)
        facts=dict(name=name,winner=proof['winner'],normal_exit=json.loads((root/'EXECUTION.json').read_text())['client_exit'],
                   counts=proof['counts'],owned_all_request_count=len(registered),registered_by_type=dict(bytype),
                   policy_and_auto_request_count=len(policy),additional_owned_requests=len(extra),additional_owned_types=dict(extra_types),
                   cancelled_foreign_wait_ids=sorted(cancelled),cancelled_director_ids=[],
                   all_client_request_count=len(sends),all_actual_ack_count=len(generic),
                   all_send_ids_accounted_by_real_ack_or_atomic_clear=True,
                   registry=registry,whole_game_reaudited=True,
                   reauditor_output_sha256={name:sha(out/name/'AUDIT.json') for name in ['raw-audit','replan-audit','proxy-audit']})
        games.append(facts);inputs.extend([root/'client.log',root/'typed.jsonl',root/'EXECUTION.json'])
    old=LAB/'evaluations/typed-clearance-proxy-paired-02/pair-03/b/native'
    new=original/'hang-repro/native';comparison={}
    for pattern in ['agent/request-*.json','agent/action-*.json']:
        a=sorted(old.glob(pattern));b=sorted(new.glob(pattern))
        assert len(a)==len(b)==237
        comparison[pattern]=dict(count=237,all_bytes_exact=all(x.name==y.name and x.read_bytes()==y.read_bytes() for x,y in zip(a,b)))
        assert comparison[pattern]['all_bytes_exact'];inputs.extend(a+b)
    for name in ['strategy-decisions.jsonl','strategy-trace.jsonl.targets.jsonl','strategy-trace.jsonl.replan.jsonl']:
        comparison[name]=dict(bytes_exact=(old/name).read_bytes()==(new/name).read_bytes());assert comparison[name]['bytes_exact']
        inputs.extend([old/name,new/name])
    a=rows(old/'strategy-trace.jsonl');b=rows(new/'strategy-trace.jsonl')
    assert len(a)==len(b)+1 and a[:-1]==b and a[-1]['event']=='native_battle_ready' and b[-1]['event']=='defeat'
    assert {k:v for k,v in a[-1].items() if k!='event'}=={k:v for k,v in b[-1].items() if k!='event'}
    comparison['strategy-trace.jsonl']=dict(old_rows=len(a),new_rows=len(b),whole_bytes_exact=False,
        common_prefix_bytes_exact=(old/'strategy-trace.jsonl').read_bytes().startswith((new/'strategy-trace.jsonl').read_bytes()),
        differing_tail=a[-1:],last_common=b[-1],only_difference='Old post-terminal native_battle_ready snapshot with state identical to terminal.')
    inputs.extend([old/'strategy-trace.jsonl',new/'strategy-trace.jsonl',old/'EXECUTION.json'])
    old_execution=json.loads((old/'EXECUTION.json').read_text())
    assert old_execution['client_exit']==-15 and not old_execution['game_completed'] and not old_execution['transport_drained']
    result=dict(passed=True,engineering_only=True,new_native_games=0,GPU_operations=0,optimizer_steps=0,training_samples=0,
                expert_labels=0,games=games,reproduction_comparison=comparison,old_timeout_remains_invalid_unscored=True,
                input_sha256={str(path):sha(path) for path in inputs},ability_improvement_claim=False,
                limitation='Three engineering qualifications. Foreign wait clearing is not application/ACK success and does not prove non-execution. Complete world determinism is not certified.')
    (args.out/'AUDIT.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(dict(passed=True,games=[{k:v for k,v in game.items() if k not in ['registry','reauditor_output_sha256']} for game in games],trace_comparison=comparison['strategy-trace.jsonl']),indent=2))


if __name__=='__main__':main()
