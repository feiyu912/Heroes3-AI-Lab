"""Read-only earliest raw movement/request divergence; no model or engine changes."""
import hashlib,json,re
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=Path('/root/heroes3-ai-lab/evaluations')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(root):
    assert json.loads((root.parent/'audit/AUDIT.json').read_text())['whole_game_valid']
    proposals=[json.loads(x) for x in (root/'agent/typed-broker.jsonl').read_text().splitlines()]
    moves=[];last_decision=0;own_turn=None
    for number,line in enumerate((root/'client.log').read_text(errors='replace').splitlines(),1):
        if 'DirectorTypedEvent ' in line:
            event=json.JSONDecoder().raw_decode(line.split('DirectorTypedEvent ',1)[1])[0]
            if event['event']=='native_action_sent':
                last_decision=event.get('decision_id') or last_decision;own_turn=event.get('own_turn',own_turn)
        m=re.search(r': Hero (.*?) starts movement from \(([-\d ]+)\) to \(([-\d ]+)\)\.',line)
        if m:moves.append(dict(hero=m[1],origin=list(map(int,m[2].split())),target=list(map(int,m[3].split())),
                              log_line=number,last_owned_decision=last_decision,last_owned_turn=own_turn))
    assert moves and proposals
    return proposals,moves
def effect(p):
    q,r=p['request'],p['response'];c=q['candidates'][r['selected_index']]
    return (q['day'],q['own_turn'],q['hero'],r['op'],c.get('kind'),c.get('position'),c.get('next'))
def compare(left,right):
    a,ma=load(left);b,mb=load(right)
    rd=next((i for i,(x,y) in enumerate(zip(a,b)) if x['request']!=y['request']),None)
    cd=next((i for i,(x,y) in enumerate(zip(a,b)) if effect(x)!=effect(y)),None)
    key=lambda x:(x['hero'],x['origin'],x['target'])
    md=next((i for i,(x,y) in enumerate(zip(ma,mb)) if key(x)!=key(y)),None)
    report=dict(left=str(left),right=str(right),left_rows=len(a),right_rows=len(b),
        first_request_difference=None if rd is None else rd+1,first_choice_difference=None if cd is None else cd+1,
        first_movement_difference=None if md is None else md+1,
        raw_input_sha256={str(p):sha(p) for root in (left,right) for p in [root/'client.log',root/'agent/typed-broker.jsonl',root.parent/'audit/AUDIT.json']})
    if rd is not None:
        x,y=a[rd]['request'],b[rd]['request'];keys=[k for k in x if x[k]!=y.get(k)]
        report['request_differences']=dict(request_id=rd+1,day=x['day'],keys=keys,
            fields={k:[x[k],y.get(k)] for k in keys if k!='candidates'},
            candidate_counts=[len(x['candidates']),len(y['candidates'])],same_selected_effect=effect(a[rd])==effect(b[rd]))
    if md is not None:
        report['movement_context']={'left':ma[max(0,md-2):md+2],'right':mb[max(0,md-2):md+2]}
    return report
old=ROOT/'typed-curriculum-paired-dev-02/pair-03'
repeat=ROOT/'typed-curriculum-paired-dev-03/pair-03/a/native'
report=dict(passed=True,comparisons=[compare(old/'a/native',old/'b/native'),compare(old/'a/native',repeat)],
    additional_native_games=1,optimizer_steps=0,training_samples=0,
    limitation='Earliest observed server movement divergence does not by itself identify internal RNG, scheduling or pointer tie-breaking as the root cause. Original eight-pair endpoint unchanged.')
out=HERE/'native-variability-audit-01';out.mkdir(exist_ok=False)
(out/'AUDIT.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
