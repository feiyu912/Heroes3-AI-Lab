#!/usr/bin/env python3
"""Independent slot-summing historical recomputation. No mutable audit imports."""
import hashlib,json
from collections import Counter
from pathlib import Path

HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def army(unit,old=False):
    if old:return Counter({int(c):int(n) for c,n in unit['army']})
    out=Counter()
    for creature,count in unit['army']:
        assert int(count)>=0
        out[int(creature)]+=int(count)
    return out
def transfers(states,old=False):
    deliveries=[];errors=[]
    first=next(s for s in states if s['event']=='turn_start')
    main_id=first['heroes'][0]['id'] if len(first['heroes'])==1 else None
    for index,before in enumerate(states):
        if before['event']!='before_army_transfer':continue
        try:
            after=states[index+1];assert after['event']=='economy_applied','No immediate successful economy ACK'
            hb={h['id']:army(h,old) for h in before['heroes']};ha={h['id']:army(h,old) for h in after['heroes']}
            tb={t['id']:army(t,old) for t in before['towns']};ta={t['id']:army(t,old) for t in after['towns']}
            assert set(hb)==set(ha) and set(tb)==set(ta),'Owner-object set changed'
            hd={k:ha[k]-hb[k] for k in hb if ha[k]!=hb[k]};td={k:tb[k]-ta[k] for k in tb if ta[k]!=tb[k]}
            assert len(hd)==len(td)==1,'Ambiguous transfer state'
            hero,gain=next(iter(hd.items()));town,loss=next(iter(td.items()))
            assert gain and gain==loss and ha[hero]==hb[hero]+gain and tb[town]==ta[town]+loss,'Nonconserved transfer'
            deliveries.append(dict(line=index+1,after_line=index+2,day=before['day'],hero=hero,town=town,
                creatures=dict(gain),count=sum(gain.values()),to_original_main=hero==main_id))
        except (AssertionError,IndexError) as error:errors.append(dict(line=index+1,day=before['day'],error=str(error)))
    total=Counter();main=Counter()
    for d in deliveries:
        total.update(d['creatures'])
        if d['to_original_main']:main.update(d['creatures'])
    return dict(deliveries=deliveries,errors=errors,delivered_count=sum(total.values()),delivered_to_main_count=sum(main.values()),
                delivered_by_creature=dict(total),delivered_to_main_by_creature=dict(main),main_id=main_id)

def recruitment(states):
    changes=[];errors=[]
    def total(state):
        out=Counter()
        for unit in state['heroes']+state['towns']:out.update(army(unit))
        return out
    for index,before in enumerate(states):
        if before['event']!='before_recruit':continue
        try:
            after=states[index+1];assert after['event']=='economy_applied'
            b=total(before);a=total(after);gain=a-b
            assert len(gain)==1 and a==b+gain
            count=sum(gain.values())
            assert sum(sum(t['available']) for t in before['towns'])-sum(sum(t['available']) for t in after['towns'])==count
            changes.append(dict(line=index+1,day=before['day'],creatures=dict(gain),count=count))
        except (AssertionError,IndexError) as error:errors.append(dict(line=index+1,day=before['day'],error=str(error)))
    return dict(events=changes,errors=errors,recruited_count=sum(e['count'] for e in changes))

def natives(value):
    if isinstance(value,dict):
        if value.get('schema')=='adventure-run-v5':yield value
        else:
            for item in value.values():yield from natives(item)
    elif isinstance(value,list):
        for item in value:yield from natives(item)

def sources():
    for name,folder in [('threat_A_failed_pilot01',ROOT/'strategic-threat-response-v1/native-pilot-01'),
        ('supply_pilot01',ROOT/'strategic-policy-v2/supply-native-pilot-01'),
        ('acceptance06',ROOT/'strategic-economy-v4/acceptance-06')]:
        for path in folder.rglob('smoke-result.json'):yield name,path
    for path in (ROOT/'strategic-economy-v4').glob('acceptance-*/*/RAW_AUDIT.json'):
        if path.parent.parent.name=='acceptance-06' or not read(path).get('passed'):continue
        yield 'historical_accepted_economy_other',path.parent/'smoke-result.json'
    for path in (ROOT/'strategic-vector-v1/native-cuda-boundary-clean-4env-01').glob('*/training.json'):yield 'CUDA_boundary',path
    yield 'paired_dev',ROOT/'strategic-vector-v1/native-paired-dev-clean-01/results.json'
    for size in (8,12,24):yield f'capacity_{size}',ROOT/f'strategic-vector-v1/native-capacity-learned-01/scale-{size:02d}/batch.json'
    yield 'turnstart_restore',ROOT/'strategic-vector-audits/cleanprior-turnstart-2026102401/restore-run/result.json'
    prep=read(ROOT/'strategic-vector-audits/cleanprior-turnstart-2026102401/PREPARATION.json')
    yield 'turnstart_fresh',Path(prep['original_agent'])/'smoke-result.json'

def main():
    reports=[];seen=set();missing=[]
    for cohort,source in sources():
        if not source.exists():missing.append(str(source));continue
        for native in natives(read(source)):
            key=cohort,native['run_dir']
            if key in seen:continue
            seen.add(key)
            trace=Path(native['run_dir'])/'strategy-trace.jsonl'
            if not trace.exists():missing.append(str(trace));continue
            raw=trace.read_bytes();states=[json.loads(s) for s in raw.splitlines() if s.strip()]
            assert hashlib.sha256(raw).hexdigest()==native['strategy_trace_sha256']
            new=transfers(states);old=transfers(states,True)
            duplicate_states=[];affected=[]
            for index,state in enumerate(states):
                for kind in ('heroes','towns'):
                    for unit in state[kind]:
                        if army(unit)!=army(unit,True):duplicate_states.append(dict(line=index+1,kind=kind,id=unit['id']))
            old_events={d['line']:d for d in old['deliveries']};new_events={d['line']:d for d in new['deliveries']}
            for line in sorted(set(old_events)|set(new_events)):
                if old_events.get(line)!=new_events.get(line):
                    before=states[line-1];after=states[line]
                    affected.append(dict(line=line,day=before['day'],old=old_events.get(line),corrected=new_events.get(line),
                        heroes_before=before['heroes'],heroes_after=after['heroes'],towns_before=before['towns'],towns_after=after['towns']))
            reports.append(dict(cohort=cohort,source=str(source),source_sha256=sha(source),native_dir=native['run_dir'],
                raw_trace_sha256=hashlib.sha256(raw).hexdigest(),native_completed=native['completed'],winner_unchanged=native['winner'],
                old=old,corrected=new,recruitment_corrected=recruitment(states),
                duplicate_stack_state_count=len(duplicate_states),duplicate_stack_first_examples=duplicate_states[:5],affected_transfers=affected))
            published=source.parent/'RAW_AUDIT.json'
            if published.exists():
                p=read(published);praw=p.get('raw',p)
                if 'delivered_count' in praw:
                    reports[-1]['published_comparison']={'path':str(published),'sha256':sha(published),
                        'published_delivered_count':praw['delivered_count'],'published_main_count':praw['delivered_to_main_count'],
                        'matches_corrected':praw['delivered_count']==new['delivered_count'] and praw['delivered_to_main_count']==new['delivered_to_main_count']}
                if 'recruit_events' in p:
                    reports[-1]['published_recruit_count_comparison']={'count':sum(e['count'] for e in p['recruit_events']),
                        'matches_corrected':sum(e['count'] for e in p['recruit_events'])==reports[-1]['recruitment_corrected']['recruited_count']}
    summary={}
    for cohort in sorted({r['cohort'] for r in reports}):
        rs=[r for r in reports if r['cohort']==cohort]
        summary[cohort]=dict(episodes=len(rs),episodes_with_duplicate_states=sum(r['duplicate_stack_state_count']>0 for r in rs),
            affected_transfer_events=sum(len(r['affected_transfers']) for r in rs),old_transfer_error_count=sum(len(r['old']['errors']) for r in rs),
            corrected_transfer_error_count=sum(len(r['corrected']['errors']) for r in rs),
            old_successfully_parsed_count=sum(r['old']['delivered_count'] for r in rs),corrected_delivered_count=sum(r['corrected']['delivered_count'] for r in rs),
            old_successfully_parsed_main_count=sum(r['old']['delivered_to_main_count'] for r in rs),corrected_delivered_to_main_count=sum(r['corrected']['delivered_to_main_count'] for r in rs),
            corrected_recruitment_errors=sum(len(r['recruitment_corrected']['errors']) for r in rs))
        summary[cohort]['published_transfer_reports_checked']=sum('published_comparison' in r for r in rs)
        summary[cohort]['published_transfer_reports_changed']=sum(not r['published_comparison']['matches_corrected'] for r in rs if 'published_comparison' in r)
    output=dict(read_only=True,native_games_started=0,optimizer_steps=0,missing_inputs=missing,summary=summary,episodes=reports,
        caveat='Old counts are parsed valid events only when old errors exist; not a valid full old total. Corrected transfer counts alone do not certify game or policy validity.',
        auditor_sha256=sha(Path(__file__)))
    (HERE/'RECOMPUTED.json').write_text(json.dumps(output,indent=2));print(json.dumps({'summary':summary,'missing_inputs':missing},indent=2))

if __name__=='__main__':main()
