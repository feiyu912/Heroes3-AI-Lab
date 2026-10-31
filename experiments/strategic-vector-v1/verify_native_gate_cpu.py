"""CPU fake integration tests for native failures and terminal ACK distinctions."""
import copy
import json
from pathlib import Path
import sys

from collect_vector import (torch,load_checkpoint_bundle,DEFAULT_CHECKPOINT,collect_parallel,
                            BatchAbort,audit_native_events,V2)

out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=False)
torch.set_num_threads(1)
model,_,_=load_checkpoint_bundle(DEFAULT_CHECKPOINT,'cpu')
jobs=[dict(map='Maps/adv/takeover-v2-train-01-mines',red='DirectorAI',blue='EmptyAI',seed=2026102600+i) for i in range(2)]
cases=[]
for kind,expected in [('none',True),('move',False),('economy',False),('query',False),
                      ('terminal_ack',True),('terminal_pending',False),('blocking',True)]:
    directory=out/kind
    accepted=False
    try:
        rows,episodes=collect_parallel(model,jobs,directory,'cpu','gate-test',synthetic=True,synthetic_failure_kind=kind)
        accepted=True
    except BatchAbort as error:
        rows=[];episodes=error.episodes
    report=json.loads((directory/'batch.json').read_text())
    cases.append(dict(case=kind,expected_accept=expected,actual_accept=accepted,accepted_samples=len(rows),
                      update_allowed=report['learner_update_allowed'],remaining=report['remaining_processes'],
                      event_audits=[e.get('native_event_audit') for e in episodes]))
# A final request may execute a native military visit/battle and reach gameOver
# before TryMoveHero reply; verify the explicit causal-event evidence route.
proof=out/'terminal-battle-proof';proof.mkdir()
(proof/'strategy-trace.jsonl').write_text(''.join(json.dumps(dict(event='move_applied',day=1))+'\n' for _ in range(3)))
log=''.join('DirectorAI: step finished result=1\n' for _ in range(3))
log+='DirectorAI: step hero 1 (10 10 0) -> (11 10 0)\n'
log+='Player 0 (red) wants to move hero 1 from (11 10 0) to (12 10 0)\n'
log+='Hero fixture hero starts movement from (11 10 0) to (12 10 0)\n'
log+='Hero fixture hero visits fixture military target (34)\n'
log+='Applied on gameState(): 12BattleResult\nDirectorAI: native gameOver player=red victory=1 loss=0\n'
(proof/'client.log').write_text(log)
request=json.loads((V2/'fixtures/visible-request.json').read_text())
request['candidates'][0].update(kind=0,position=[11,10,0],next=[11,10,0])
audit=audit_native_events(proof,4,True,dict(request=request,action=0))
report=dict(cpu_fake_only=True,cases=cases,terminal_battle_proof=audit,optimizer_steps=0,
            passed=all(c['expected_accept']==c['actual_accept'] and not c['remaining'] and (c['actual_accept'] or c['accepted_samples']==0) for c in cases) and audit['valid'] and audit['terminal_native_visit_execution_proof'] is not None)
(out/'AUDIT.json').write_text(json.dumps(report,indent=2))
print(json.dumps(dict(passed=report['passed'],cases=[(c['case'],c['actual_accept']) for c in cases],terminal_proof_accepted=audit['valid'])))
raise SystemExit(0 if report['passed'] else 1)
