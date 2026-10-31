import json
from pathlib import Path
import re
from inspect_failure import HERE,V2

run=V2/'supply-native-pilot-01'
execution=json.loads((run/'EXECUTION.json').read_text());failure=run/execution['failed_episode']
smoke=json.loads((failure/'smoke-result.json').read_text());root=Path(smoke['native_result']['run_dir'])
states=[json.loads(x)for x in (root/'strategy-trace.jsonl').read_text().splitlines()]
failindex=next(i for i,s in enumerate(states)if s['event']=='move_failed')
decision_number=sum(s['event']=='before_move' for s in states[:failindex])
decisions=[json.loads(x)for x in (root/'strategy-decisions.jsonl').read_text().splitlines()]
text=(root/'client.log').read_text(errors='replace').splitlines()
step_lines=[i for i,x in enumerate(text)if 'DirectorAI: step hero ' in x]
start=step_lines[decision_number-1]
end=next((i for i in range(start+1,len(text))if 'DirectorAI: no hero with movement points' in text[i]),min(start+120,len(text)))
context=[dict(line=i+1,text=re.sub(r'\x1b\[[0-9;]*m','',text[i]))for i in range(max(0,start-10),min(end+5,start+160))]
agent=Path(smoke['agent_dir']);request=agent/f'request-{decision_number:08d}.json'
result=dict(decision_number=decision_number,trace_failure_line=failindex+1,decision=decisions[decision_number-1],
            request=json.loads(request.read_text()),request_path=str(request),log_context=context)
out=HERE/'MOVEMENT_FAILURE.json';assert not out.exists();out.write_text(json.dumps(result,indent=2,ensure_ascii=False))
print(json.dumps(result,ensure_ascii=False))
