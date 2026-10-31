"""Read-only stack-aggregation component review; not historical native recertification."""
from pathlib import Path
import collections,hashlib,json,sys
HERE=Path(__file__).resolve().parent
EXP=HERE.parents[1]
sys.path.insert(0,str(EXP/'strategic-policy-v2'))
from audit_supply_raw import army
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def duplicate(unit):return len({c for c,n in unit['army']})<len(unit['army'])
def population(state):
 result=collections.Counter()
 for unit in state['heroes']+state['towns']:result.update(army(unit))
 return result
def review(root,stored=None):
 trace=root/'strategy-trace.jsonl';states=[json.loads(s)for s in trace.read_text().splitlines()]
 deliveries=[];recruits=[];errors=[]
 for i,b in enumerate(states[:-1]):
  if b['event']not in ('before_army_transfer','before_recruit'):continue
  a=states[i+1]
  try:
   assert a['event']=='economy_applied'
   if b['event']=='before_army_transfer':
    hb={h['id']:army(h)for h in b['heroes']};ha={h['id']:army(h)for h in a['heroes']}
    tb={t['id']:army(t)for t in b['towns']};ta={t['id']:army(t)for t in a['towns']}
    assert set(hb)==set(ha)and set(tb)==set(ta)
    hg={k:ha[k]-v for k,v in hb.items()if ha[k]!=v};tl={k:v-ta[k]for k,v in tb.items()if ta[k]!=v}
    assert len(hg)==len(tl)==1
    hero,gain=next(iter(hg.items()));town,loss=next(iter(tl.items()))
    assert gain and gain==loss and ha[hero]==hb[hero]+gain and tb[town]==ta[town]+loss
    deliveries.append(dict(before_line=i+1,hero=hero,town=town,creatures=dict(gain),count=sum(gain.values())))
   else:
    pb,pa=population(b),population(a);gain=pa-pb
    assert len(gain)==1 and pa==pb+gain
    count=sum(gain.values())
    assert sum(sum(t['available'])for t in b['towns'])-sum(sum(t['available'])for t in a['towns'])==count
    recruits.append(dict(before_line=i+1,creatures=dict(gain),count=count))
  except AssertionError:errors.append(dict(before_line=i+1,event=b['event']))
 total=sum(d['count']for d in deliveries)
 changes=[]
 if stored:
  old={d['before_line']:d for d in stored['deliveries']}
  for d in deliveries:
   prior=old.get(d['before_line']);prior_creatures={int(k):v for k,v in prior['creatures'].items()}if prior else None
   if prior_creatures!=d['creatures']:changes.append(dict(before_line=d['before_line'],old=prior,new=d))
  if len(old)!=len(deliveries):changes.append(dict(old_records=len(old),new_records=len(deliveries)))
 return dict(native_dir=str(root),trace_sha256=sha(trace),passed_component_checks=not errors,
     duplicate_slot_states=sum(any(duplicate(u)for u in s['heroes']+s['towns'])for s in states),
     corrected_delivered_count=total,old_delivered_count=stored['delivered_count']if stored else None,
     delivery_changes=changes,corrected_recruit_events=len(recruits),errors=errors,deliveries=deliveries)

results=[]
for folder in sorted((EXP/'strategic-economy-v4').glob('acceptance-*')):
 for path in sorted(folder.rglob('RAW_AUDIT.json')):
  data=json.loads(path.read_text())
  if not data.get('passed'):continue
  raw=data['raw'];native=Path(raw['native_dir']);trace=native/'strategy-trace.jsonl'
  assert raw['evidence_sha256'][str(trace)]==sha(trace),'Historical trace changed'
  result=review(native,raw);result.update(original_audit=str(path),original_audit_sha256=sha(path));results.append(result)
fifth=Path('/root/heroes3-ai-lab/workers/adv-runs/threat-a-native-pilot-01-baseline-4-2026101881-g2841epm')
out=dict(schema='historical-stack-sum-component-review-v1',scope='Only conserved transfer/recruit arithmetic with original trace SHA; not full old-native runtime recertification or rewritten training/evidence',
    audit_helper_sha256=sha(EXP/'strategic-policy-v2/audit_supply_raw.py'),episodes=results,
    original_failed_fifth_game_component=review(fifth),
    total_original_passed_audits=len(results),component_failures=sum(not r['passed_component_checks']for r in results),
    changed_old_delivery_totals=sum(r['corrected_delivered_count']!=r['old_delivered_count']for r in results))
target=HERE/'HISTORICAL_COMPONENT_REVIEW.json';assert not target.exists()
target.write_text(json.dumps(out,indent=2));print(json.dumps({k:v for k,v in out.items()if k not in ('episodes','original_failed_fifth_game_component')},indent=2))
