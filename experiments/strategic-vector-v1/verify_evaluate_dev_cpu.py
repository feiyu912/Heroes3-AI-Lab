"""Fabricated IO/trace mismatch rejection tests only; never launches a game."""
import copy
import hashlib
import json
from pathlib import Path
import sys

from evaluate_dev import verify_native_consumption,jobs_for,summarize,V2

out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=False)
digest='a'*64


def fixture(name):
    directory=out/name;directory.mkdir();agent=directory/'agent';agent.mkdir();run=directory/'native';run.mkdir()
    request=json.loads((V2/'fixtures/visible-request.json').read_text())
    raw=json.dumps(request).encode();response=b'0\n'
    (agent/'request-00000001.json').write_bytes(raw);(agent/'action-00000001.json').write_bytes(response)
    ready=dict(mode='new-policy',model_version='sha256:'+digest)
    (agent/'broker-ready.json').write_text(json.dumps(ready))
    event=dict(request_id=1,request_file='request-00000001.json',action_file='action-00000001.json',
        request_sha256=hashlib.sha256(raw).hexdigest(),response_sha256=hashlib.sha256(response).hexdigest(),
        model_version='sha256:'+digest,mode='new-policy',action=0)
    (agent/'broker-trace.jsonl').write_text(json.dumps(dict(event,event='decision_committed'))+'\n'+json.dumps(dict(event,event='response_written'))+'\n')
    c=request['candidates'][0]
    decision=dict(request,selected_candidate=0,destination=c['position'],step=c['next'])
    (run/'strategy-decisions.jsonl').write_text(json.dumps(decision)+'\n')
    (run/'strategy-trace.jsonl').write_text(json.dumps(dict(event='move_applied',day=7))+'\n')
    (run/'client.log').write_text('DirectorAI: step finished result=3 points_left=100 from (1 1 0) to (2 1 0)\n')
    return agent,run,dict(run_dir=str(run),completed=True)


results=[]
for name in ('valid_blocking','wrong_checkpoint','wrong_action_bytes','native_selected_mismatch',
             'native_candidates_mismatch','strict_v3_missing_field','economy_failed','terminal_pending'):
    agent,run,native=fixture(name)
    if name=='wrong_checkpoint':
        (agent/'broker-ready.json').write_text(json.dumps(dict(mode='new-policy',model_version='sha256:'+'b'*64)))
    elif name=='wrong_action_bytes':
        (agent/'action-00000001.json').write_text('1\n')
    elif name.startswith('native_'):
        decision=json.loads((run/'strategy-decisions.jsonl').read_text())
        if name=='native_selected_mismatch':decision['selected_candidate']=1
        else:decision['candidates'][0]['next']=[33,33,0]
        (run/'strategy-decisions.jsonl').write_text(json.dumps(decision)+'\n')
    elif name=='strict_v3_missing_field':
        req=json.loads((agent/'request-00000001.json').read_text());del req['own_towns']
        (agent/'request-00000001.json').write_text(json.dumps(req))
    elif name=='economy_failed':
        with (run/'strategy-trace.jsonl').open('a') as stream:stream.write(json.dumps(dict(event='economy_failed',day=7))+'\n')
    elif name=='terminal_pending':
        (run/'strategy-trace.jsonl').write_text('');(run/'client.log').write_text('DirectorAI: step hero 1 pending\nDirectorAI: native gameOver player=red victory=1 loss=0\n')
    accepted=False;error=None
    try:
        verify_native_consumption(agent,native,digest);accepted=True
    except (ValueError,KeyError) as problem:error=str(problem)
    results.append(dict(case=name,accepted=accepted,error=error,expected_accept=name=='valid_blocking'))
jobs=jobs_for(1,2026110300)
rows=[dict(pair_index=i,job=job,model=model,valid=True,win=(model=='candidate'),native=dict(native_calendar_last_day=8))
      for i,job in enumerate(jobs) for model in ('baseline','candidate')]
summary=summarize(rows,jobs)
report=dict(fabricated_CPU_only=True,game_started=False,optimizer_steps=0,test_split_touched=False,cases=results,
    schedule_pairs=len(jobs),map_count=summary['distinct_map_count'],confidence_interval=summary['confidence_interval'],
    passed=all(r['accepted']==r['expected_accept'] for r in results) and len(jobs)==8 and summary['distinct_map_count']==2 and summary['confidence_interval'] is None,
    note='Fabricated wins test summary accounting only and are not evaluation results.')
(out/'AUDIT.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
raise SystemExit(0 if report['passed'] else 1)
