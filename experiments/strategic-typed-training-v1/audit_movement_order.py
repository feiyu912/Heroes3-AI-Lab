"""Distinguish movement ordering from different recorded movement sets before choice changes."""
import collections,hashlib,json,re
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=Path('/root/heroes3-ai-lab/evaluations/typed-curriculum-paired-dev-02')
def prefix(path,cutoff):
    events=[];last=0
    for number,line in enumerate(path.read_text(errors='replace').splitlines(),1):
        if 'DirectorTypedEvent ' in line:
            e=json.JSONDecoder().raw_decode(line.split('DirectorTypedEvent ',1)[1])[0]
            if e['event']=='native_action_sent' and e.get('decision_id') is not None:last=e['decision_id']
        m=re.search(r': Hero (.*?) starts movement from \(([-\d ]+)\) to \(([-\d ]+)\)\.',line)
        if m and last<cutoff:events.append((last,*m.groups()))
    return events
answer=[]
for i,cutoff in [(3,18),(7,121)]:
    paths=[ROOT/f'pair-{i:02d}/{arm}/native/client.log' for arm in ('a','b')]
    a,b=[prefix(p,cutoff) for p in paths];ca,cb=map(collections.Counter,(a,b))
    # Hero labels are log labels, not unique object IDs; equality is scoped to
    # recorded movements and cannot certify unobserved economy or full state.
    answer.append(dict(pair=i,before_policy_decision=cutoff,counts=[len(a),len(b)],ordered_prefix_same=a==b,
        movement_multiset_same=ca==cb,only_baseline=list((ca-cb).items())[:5],only_candidate=list((cb-ca).items())[:5],
        raw_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}))
out=HERE/'movement-order-audit-01';out.mkdir(exist_ok=False)
report=dict(passed=True,pairs=answer,native_games=0,optimizer_steps=0,training_samples=0,
    limitation='Pair7 recorded movement multiset equality allows an ordering-only explanation for this prefix. It does not establish full hidden state/RNG equality or a causal win gain. Pair3 has genuinely different recorded movement sets.')
(out/'AUDIT.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
