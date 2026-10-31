"""Additional public-threat, reinforcement-opportunity and own-loss evidence."""
import collections
import hashlib
import json
from pathlib import Path
import re
from audit import HERE,TRAIN,sha,lines


def main():
    source=json.loads((HERE/'AUDIT.json').read_text())
    output=[]
    for ep in source['episodes']:
        native=ep['native'];root=Path(native['run_dir']);roll=Path(native['config']['agent_dir'])
        decisions=lines(root/'strategy-decisions.jsonl');states=lines(root/'strategy-trace.jsonl')
        requests=[];opportunities=[]
        for i,d in decisions:
            p=roll/f'request-{i:08d}.json';r=json.loads(p.read_text())
            assert r['hero']==d['hero'] and r['from']==d['from'] and r['candidates']==d['candidates']
            requests.append(dict(path=str(p),sha256=sha(p)))
            supplies=[dict(index=j,**c) for j,c in enumerate(r['candidates']) if c['kind']==4]
            if supplies:
                opportunities.append(dict(decision_line=i,request=str(p),request_sha256=sha(p),day=d['day'],
                    hero=d['hero'],from_pos=d['from'],own_army_value=r['own_army_value'],
                    selected=d['candidates'][d['selected_candidate']],supplies=supplies))
        ids={h['id'] for _,s in states for h in s['heroes']}
        removals=[];captures=[];battle_starts=[]
        texts=(root/'client.log').read_text(errors='replace').splitlines()
        for i,t in enumerate(texts,1):
            clean=re.sub(r'\x1b\[[0-9;]*m','',t)
            m=re.search(r'removing object id=(\d+);',clean)
            if m and int(m[1]) in ids:removals.append(dict(line=i,own_hero_id=int(m[1]),text=clean))
            if 'town' in clean.lower() and any(k in clean.lower() for k in ('capture','owner','conquer')):
                captures.append(dict(line=i,text=clean))
            if 'battle' in clean.lower() and any(k in clean.lower() for k in ('starts','started','between','attacker','defender')):
                battle_starts.append(dict(line=i,text=clean))
        lost=[]
        for j in range(1,len(states)):
            pi,p=states[j-1];i,s=states[j]
            disappeared={h['id'] for h in p['heroes']}-{h['id'] for h in s['heroes']}
            if disappeared:lost.append(dict(before_line=pi,line=i,day=s['day'],event=s['event'],ids=sorted(disappeared),before=p,after=s))
        r=json.loads(Path(requests[0]['path']).read_text())
        output.append(dict(seed=ep['config']['seed'],request_keys=list(r),candidate_keys=list(r['candidates'][0]),
            request_manifest=requests,supply_opportunities=opportunities,
            supply_opportunity_count=len(opportunities),supply_selected_count=sum(o['selected']['kind']==4 for o in opportunities),
            own_hero_disappearances=lost,own_hero_removal_logs=removals,
            town_ownership_log=captures,battle_context=battle_starts))
    target=HERE/'DETAILS.json';assert not target.exists()
    target.write_text(json.dumps(dict(schema='strategic-nk-failure-detail-v1',source_audit_sha256=sha(HERE/'AUDIT.json'),episodes=output),indent=2,ensure_ascii=False))
    for ep in output:
        print(json.dumps(dict(seed=ep['seed'],supply_opportunities=ep['supply_opportunity_count'],
            supply_selected=ep['supply_selected_count'],losses=[dict(day=x['day'],line=x['line'],ids=x['ids'])for x in ep['own_hero_disappearances']],
            removal_logs=ep['own_hero_removal_logs'],town_logs=ep['town_ownership_log'][:8]),ensure_ascii=False))


if __name__=='__main__':main()
