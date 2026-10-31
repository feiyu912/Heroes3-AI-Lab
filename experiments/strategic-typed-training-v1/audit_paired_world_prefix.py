"""Inspect all movement prefixes, including hidden opponent activity, before policy divergence."""
import hashlib,json,re
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=Path('/root/heroes3-ai-lab/evaluations/typed-curriculum-paired-dev-02')
def rows(p):return [json.loads(x) for x in p.read_text().splitlines()]
def movements(root):
    result=[];last=0
    for number,line in enumerate((root/'client.log').read_text(errors='replace').splitlines(),1):
        if 'DirectorTypedEvent ' in line:
            e=json.JSONDecoder().raw_decode(line.split('DirectorTypedEvent ',1)[1])[0]
            if e['event']=='native_action_sent' and e.get('decision_id') is not None:last=e['decision_id']
        m=re.search(r': Hero (.*?) starts movement from \(([-\d ]+)\) to \(([-\d ]+)\)\.',line)
        if m:result.append({'movement':list(m.groups()),'line':number,'last_policy_decision':last})
    return result
def effect(p):
    q,r=p['request'],p['response'];c=q['candidates'][r['selected_index']]
    return [q['day'],q['own_turn'],q['hero'],r['op'],c.get('kind'),c.get('position'),c.get('next')]
answer=[]
for i in range(8):
    roots=[ROOT/f'pair-{i:02d}/{arm}/native' for arm in ('a','b')]
    p=[rows(r/'agent/typed-broker.jsonl') for r in roots];m=[movements(r) for r in roots]
    cd=next((j+1 for j,(a,b) in enumerate(zip(*p)) if effect(a)!=effect(b)),None)
    md=next((j for j,(a,b) in enumerate(zip(*m)) if a['movement']!=b['movement']),None)
    entry=dict(pair=i,first_choice_difference=cd,first_movement_difference=None if md is None else md+1,
        input_sha256={str(r/'client.log'):hashlib.sha256((r/'client.log').read_bytes()).hexdigest() for r in roots})
    if md is not None:
        a,b=m[0][md],m[1][md];entry.update(first_movement_context=[a,b],
            movement_diverged_before_first_choice=cd is None or max(a['last_policy_decision'],b['last_policy_decision'])<cd)
    else:entry['movement_diverged_before_first_choice']=False
    answer.append(entry)
out=HERE/'paired-world-prefix-audit-01';out.mkdir(exist_ok=False)
report=dict(passed=True,pairs=answer,native_games=0,optimizer_steps=0,training_samples=0,
    limitation='A different server movement prefix can be harmless hero ordering or a substantive world difference. No same-visible-request assertion proves all hidden history is controlled. No result is discarded.')
(out/'AUDIT.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
