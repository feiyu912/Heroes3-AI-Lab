"""Independent supplemental native rejection and lifecycle audit, no mutations."""
from pathlib import Path
import hashlib,json,re,sys
ROOT=Path('/mnt/g/Heroes3-AI-Lab/experiments/strategic-economy-v4/acceptance-06')
sys.path.insert(0,str(ROOT.parent.parent/'strategic-policy-v2'))
from audit_supply_raw import audit_terminal_tail,records,sha
execution=json.loads((ROOT/'EXECUTION.json').read_text())
assert execution['status']=='completed',execution['status']
assert len(execution['episodes'])==12
results=[]
for episode in execution['episodes']:
 audit=json.loads(Path(episode['audit']).read_text());raw=audit['raw'];native=Path(raw['native_dir'])
 text=(native/'client.log').read_text(errors='replace').splitlines()
 bad=[dict(line=i,text=re.sub(r'\x1b\[[0-9;]*m','',s))for i,s in enumerate(text,1)
      if any(x in s.lower()for x in ('got false in applying','player is not allowed','has to answer queries before attempting'))]
 assert not bad,(episode['tag'],bad)
 states=records(native/'strategy-trace.jsonl')
 tail=audit_terminal_tail(states)
 block=sum(s['event']=='native_battle_blocked'for _,s in states)
 ready=sum(s['event']=='native_battle_ready'for _,s in states)
 # Terminal closes the client before END may be consumed; this is diagnostic,
 # not an additional requirement on terminal transport delivery.
 assert ready<=block,(episode['tag'],block,ready)
 moveblock=sum(s['event']=='native_movement_blocked'for _,s in states)
 moveunblock=sum(s['event']=='native_movement_unblocked'for _,s in states)
 assert moveunblock<=moveblock
 sent=sum('Sending a request "10QueryReply"'in s for s in text)
 applied=sum('Message 10QueryReply successfully applied!'in s for s in text)
 assert sent==applied
 results.append(dict(tag=episode['tag'],won=episode['won'],days=episode['native_days'],
     moves=len(audit['confirmed_movement_acks']),native_rejection_lines=bad,
     battle_block_ready=[block,ready],movement_block_unblock=[moveblock,moveunblock],
     terminal_unconsumed_battle_ready=block-ready,terminal_unconsumed_move_unblock=moveblock-moveunblock,
     queries_sent_applied=[sent,applied],terminal_tail_transport=tail,
     main_loss_day=raw['original_main_loss_day'],delivered=raw['delivered_count'],
     evidence_sha256={str(native/f):sha(native/f)for f in ('client.log','strategy-trace.jsonl','strategy-decisions.jsonl')}))
result=dict(schema='acceptance06-independent-lifecycle-audit-v1',passed=True,episodes=results,
    engineering_wins=sum(r['won']for r in results[:4]),nk_development_wins=sum(r['won']for r in results[4:]),
    gradient_updates=0,independent_capability_evaluation=False,bc_eligible=0)
out=Path(__file__).parent/'ACCEPTANCE06_RAW_REVIEW.json';assert not out.exists()
out.write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items()if k!='episodes'}))
