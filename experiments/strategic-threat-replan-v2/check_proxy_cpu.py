"""Replay actual frozen recommendations and exercise explicit scripted override rules, CPU only."""
import copy,hashlib,json
from pathlib import Path
from clearance_broker import Broker
from clearance_proxy import choose
HERE=Path(__file__).resolve().parent;ROOT=Path('/root/heroes3-ai-lab/evaluations/typed-bounded-replan-paired-01')
model=HERE.parent/'strategic-typed-training-v1/cuda-curriculum-ack-01/update-1.pt'
baseline=Broker('new-policy',model);checked=0;overrides=0
for i in range(8):
    root=ROOT/f'pair-{i:02d}/b/native';sidecar=root/'strategy-trace.jsonl.replan.jsonl'
    if not sidecar.exists():continue
    scripted=Broker('new-policy',model,agent_dir=root/'agent',proxy_enabled=True)
    old={x['request']['request_id']:x for x in map(json.loads,(root/'agent/typed-broker.jsonl').read_text().splitlines())}
    for e in map(json.loads,sidecar.read_text().splitlines()):
        n=e['decision_id'];raw=(root/f'agent/request-{n:08d}.json').read_bytes();q=json.loads(raw);snapshot=copy.deepcopy(q)
        a=baseline.propose(raw,n);b=scripted.propose(raw,n);assert a['response']['selected_index']==old[n]['response']['selected_index']
        index=a['response']['selected_index'];d=choose(q,index,e)
        assert b['model_recommended_index']==index and b['response']['selected_index']==d['index'] and b['proxy']==d
        assert q==snapshot and 0<=d['index']<len(q['candidates'])
        assert choose(q,index,None)['index']==index
        stop=next(j for j,c in enumerate(q['candidates']) if c['op']=='end_turn');assert choose(q,stop,e)['index']==stop
        empty=copy.deepcopy(q);empty['visible_threats']=[];assert not choose(empty,index,e)['overridden']
        weak=copy.deepcopy(q)
        for t in weak['visible_threats']:t['approx_army_value']=0
        assert not choose(weak,index,e)['overridden']
        if d['overridden']:
            assert d['selected_clearance']>max(d['origin_clearance'],d['baseline_clearance'])
            assert q['candidates'][d['index']]['kind'] not in (0,1);overrides+=1
        checked+=1
out=HERE/'proxy-cpu-check-01';out.mkdir(exist_ok=False)
report=dict(passed=True,real_archived_states=checked,scripted_overrides=overrides,model_recommendation_exact=True,
    input_immutability=True,absent_release_and_stop_and_absent_or_weak_threat_fallbacks=True,
    source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [HERE/'clearance_broker.py',HERE/'clearance_proxy.py']},
    native_games=0,optimizer_steps=0,training_samples=0,expert_labels=0)
(out/'AUDIT.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
