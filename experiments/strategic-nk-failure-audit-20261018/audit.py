"""Read only the four TRAIN losses in continuous-2, preserve source line references."""
import collections
import hashlib
import json
from pathlib import Path
import re

HERE=Path(__file__).resolve().parent
TRAIN=HERE.parent/'strategic-policy-v1/takeover-03/native-boundary-01/continuous-2/training.json'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def lines(path):
    return [(i,json.loads(line)) for i,line in enumerate(Path(path).read_text().splitlines(),1) if line.strip()]


def main():
    t=json.loads(TRAIN.read_text())
    episodes=[]
    for e in t['episodes']:
        if 'Nullkiller2' not in (e['config']['red'],e['config']['blue']):continue
        root=Path(e['native']['run_dir'])
        trace=root/'strategy-trace.jsonl'; dec=root/'strategy-decisions.jsonl'; target=root/'strategy-trace.jsonl.targets.jsonl';log=root/'client.log'
        assert sha(trace)==e['native']['strategy_trace_sha256'] and sha(dec)==e['native']['strategy_decisions_sha256']
        assert sha(log)==e['native']['log_sha256'] and sha(target)==e['native']['strategy_targets_sha256']
        states=lines(trace); decisions=lines(dec);targets=lines(target)
        event_counts=collections.Counter(s['event'] for _,s in states)
        daily=[]
        for line,s in states:
            if s['event'] in ('turn_start','turn_end','defeat'):
                daily.append(dict(line=line,**s))
        changes=[]
        previous=None
        for line,s in states:
            signature=(s['heroes'],s['towns'])
            if previous:
                pline,prev=previous
                army_before={h['id']:h['army'] for h in prev['heroes']}
                army_after={h['id']:h['army'] for h in s['heroes']}
                town_before={x['id']:x['army'] for x in prev['towns']}
                town_after={x['id']:x['army'] for x in s['towns']}
                if army_before!=army_after or town_before!=town_after:
                    changes.append(dict(previous_line=pline,line=line,previous=prev,current=s))
            previous=(line,s)
        selections=collections.Counter(d['candidates'][d['selected_candidate']]['kind'] for _,d in decisions)
        target_status=collections.Counter((r['kind'],r['status']) for _,r in targets)
        snapshots=[]
        for day in sorted({r['day'] for _,r in targets}):
            for kind in (0,1):
                items=[(i,r) for i,r in targets if r['day']==day and r['kind']==kind]
                if items:
                    i,r=items[0];snapshots.append(dict(line=i,**r))
        supply_choices=[dict(line=i,**d) for i,d in decisions if d['candidates'][d['selected_candidate']]['kind']==4]
        rawlog=log.read_text(errors='replace').splitlines()
        clean=lambda x:re.sub(r'\x1b\[[0-9;]*m','',x)
        patterns=('DirectorAI:','Town .*captur','town .*captur','Object removed','ObjectRemoved','Hero .*defeat','lost last town','seven days','7 days','背叛','溃败')
        logs=[dict(line=i,text=clean(x)) for i,x in enumerate(rawlog,1)
              if re.search('|'.join(patterns),x) and not re.search(r'DirectorAI: (path|move request|move reply|policy|explore|external|request|step)',x)]
        source=root/'source-snapshot/CDirectorAI.cpp'
        episodes.append(dict(config=e['config'],reward=e['reward'],native=e['native'],
            evidence={str(p):sha(p) for p in (trace,dec,target,log,source)},event_counts=dict(event_counts),
            selected_kind_counts=dict(selections),target_status_counts={str(k):v for k,v in target_status.items()},
            daily=daily,army_town_changes=changes,target_daily_first=snapshots,
            supply_choices=supply_choices,log_extract=logs))
    assert len(episodes)==4
    result=dict(schema='strategic-nk-failure-readonly-v1',training=str(TRAIN),training_sha256=sha(TRAIN),
        episodes=episodes,scope='Four train-map both-role Nullkiller2 losses; no test reads, no games, no training')
    target=HERE/'AUDIT.json'
    assert not target.exists()
    target.write_text(json.dumps(result,indent=2,ensure_ascii=False))
    for e in episodes:
        print(json.dumps(dict(seed=e['config']['seed'],events=e['event_counts'],selected=e['selected_kind_counts'],
            days=[dict(line=s['line'],day=s['day'],event=s['event'],gold=s['gold'],heroes=s['heroes'],
                       towns=[dict(id=x['id'],army=x['army']) for x in s['towns']]) for s in e['daily']],
            targets=e['target_daily_first']),ensure_ascii=False))


if __name__=='__main__':main()
