"""Independent raw evidence audit; no imports from runner or its audit gate."""
import argparse,copy,hashlib,json,re
from collections import Counter
from pathlib import Path

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def one(rows,name):
    found=[r for r in rows if r['event']==name]
    assert len(found)==1, name
    return found[0]
def armies(state):
    result={}
    for h in state['heroes']:
        c=Counter()
        for creature,count in h['army']:
            assert type(count) is int and count>0
            c[creature]+=count
        result[h['id']]=c
    return result

def check(events,states,raw,execution,variant):
    log=re.sub(r'\x1b\[[0-9;]*m','',raw).splitlines()
    sent={};received={};applied={}
    for line_no,line in enumerate(log,1):
        m=re.search(r'Sending a request "(\d+\w+)"\. It.ll have an ID=(\d+)\.',line)
        if m: sent.setdefault(m[1],[]).append((int(m[2]),line_no))
        m=re.search(r'Received CPack of type (\d+\w+)$',line)
        if m: received.setdefault(m[1],[]).append(line_no)
        m=re.search(r'Message (\d+\w+) successfully applied!',line)
        if m: applied.setdefault(m[1],[]).append(line_no)
    assert not any(t in raw for t in ('Got false in applying','has to answer queries','DirectorAI: external policy failed'))
    assert execution['loaded_library_verified'] and not execution['loaded_library_errors']
    assert execution['thread_server_verification']['passed']
    assert not execution['game_completed'] and execution['winner'] is None
    assert not any(r['event'] in ('victory','defeat','move_failed','economy_failed','query_failed') for r in states)
    callback=one(events,'exchange_callback'); q=callback['query_id']
    adds=[i for i,s in enumerate(log,1) if 'Entering void QueriesProcessor::addQuery(PlayerColor, QueryPtr)' in s and 'CGarrisonDialogQuery' in s and f'qid = {q} ' in s]
    pops=[i for i,s in enumerate(log,1) if 'Entering void QueriesProcessor::popQuery(PlayerColor, QueryPtr)' in s and 'CGarrisonDialogQuery' in s and f'qid = {q} ' in s]
    assert len(adds)==1
    evidence=[]
    for prefix,pack in [('move','8MoveHero'),('transfer','13ArrangeStacks'),('close','10QueryReply'),('endturn','7EndTurn')]:
        es=[r for r in events if r['event']==prefix+'_sent']
        ea=[r for r in events if r['event']==prefix+'_ack']
        assert len(es)==len(ea)
        assert len({r['request_id'] for r in es})==len(es)
        for s in es:
            a=[r for r in ea if r['request_id']==s['request_id']]
            assert len(a)==1 and a[0]['result']==1
            k=[j for j,t in enumerate(sent.get(pack,[])) if t[0]==s['request_id']]
            assert len(k)==1
            j=k[0]; assert j<len(received.get(pack,[])) and j<len(applied.get(pack,[]))
            sl=sent[pack][j][1];rl=received[pack][j];al=applied[pack][j]
            assert sl<rl<al
            evidence.append(dict(op=prefix,request_id=s['request_id'],sent_line=sl,received_line=rl,applied_line=al))
    assert len([e for e in evidence if e['op']=='move'])==2
    before=one(states,'probe_before_exchange');b=armies(before)
    donor,receiver=callback['courier'],callback['receiver']
    assert b[donor]==Counter({0:10,2:3}) and b[receiver]==Counter({0:5})
    if variant=='original-unhandled':
        assert execution['timed_out'] and not execution['controlled_stop']
        assert not pops and all(e['op']=='move' for e in evidence)
        assert not any(r['event'] in ('transfer_sent','close_sent','endturn_sent') for r in events)
        return dict(negative_control_stalled_with_open_query=True,normal_game=False,winner=None,request_evidence=evidence)
    assert len(pops)==1 and adds[0]<pops[0]
    assert execution['controlled_stop'] and not execution['timed_out']
    close=next(e for e in evidence if e['op']=='close');end=next(e for e in evidence if e['op']=='endturn')
    assert close['received_line']<pops[0]<close['applied_line']<end['sent_line']
    after=one(states,'probe_after_close');a=armies(after)
    assert b[donor]+b[receiver]==a[donor]+a[receiver]
    assert all(sum(c.values())>=1 for c in a.values())
    assert before['towns']==after['towns']
    for field in ('gold','wood','ore','day'): assert before[field]==after[field]
    assert [(h['id'],h['x'],h['y'],h['z']) for h in before['heroes']]==[(h['id'],h['x'],h['y'],h['z']) for h in after['heroes']]
    if variant=='transfer-close':
        transfer=next(e for e in evidence if e['op']=='transfer')
        assert transfer['applied_line']<close['sent_line']
        assert a[donor]==Counter({2:3}) and a[receiver]==Counter({0:15})
    else: assert b==a and not any(e['op']=='transfer' for e in evidence)
    return dict(mechanism_pass=True,normal_game=False,winner=None,query_removed_line=pops[0],request_evidence=evidence,
        donor_before=dict(b[donor]),donor_after=dict(a[donor]),receiver_before=dict(b[receiver]),receiver_after=dict(a[receiver]))

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);args=p.parse_args()
    reports=[];mutations=[]
    for name,variant in [('multihero-probe-close-04','close-only'),('multihero-probe-transfer-01','transfer-close'),('multihero-probe-unhandled-01','original-unhandled')]:
        folder=args.root/name
        events=[json.loads(s) for s in (folder/'probe.jsonl').read_text().splitlines()]
        states=[json.loads(s) for s in (folder/'strategy-trace.jsonl').read_text().splitlines()]
        raw=(folder/'client.log').read_text(errors='replace');execution=json.loads((folder/'execution.json').read_text())
        plan=json.loads((folder/'plan.json').read_text())
        assert all(sha(Path(f))==digest for f,digest in plan['hashes'].items())
        report=check(events,states,raw,execution,variant)
        report.update(run=name,variant=variant,raw_sha256={n:sha(folder/n) for n in ('client.log','probe.jsonl','strategy-trace.jsonl','execution.json','plan.json')})
        reports.append(report)
        if variant=='transfer-close':
            bad=copy.deepcopy(states);one(bad,'probe_after_close')['heroes'][0]['army'][0][1]+=1
            candidates=[('missing_native_transfer_apply',events,states,raw.replace('Message 13ArrangeStacks successfully applied!','removed transfer proof'),execution),
                        ('broken_army_conservation',events,bad,raw,execution)]
            bad_events=copy.deepcopy(events);one(bad_events,'transfer_ack')['request_id']+=100
            candidates.append(('wrong_transfer_ack_id',bad_events,states,raw,execution))
            for label,e,s,r,x in candidates:
                try:check(e,s,r,x,variant)
                except AssertionError:mutations.append(dict(case=label,rejected=True))
                else:raise AssertionError('Accepted tamper: '+label)
    args.out.mkdir(parents=True,exist_ok=False)
    result=dict(passed=True,runs=reports,negative_checks=mutations,training_samples=0,optimizer_steps=0,
        scope='Native two-owned-hero land meeting fixture only; no general courier AI or win-rate claim.',auditor_sha256=sha(Path(__file__)))
    (args.out/'AUDIT.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))

if __name__=='__main__':main()
