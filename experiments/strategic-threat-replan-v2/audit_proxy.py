"""Replay frozen model and scripted decisions; require already reaudited real execution."""
import argparse,hashlib,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'strategic-typed-training-v1'))
from clearance_broker import Broker
from clearance_proxy import choose
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def audit(root,proof_path,out):
    proof=json.loads(proof_path.read_text());assert proof['passed'] and proof['whole_game_execution_reaudited'] and proof['fixture'] is False
    assert all(sha(Path(p))==h for p,h in proof['input_sha256'].items())
    plan=json.loads((root/'PLAN.json').read_text());enabled=plan['decision_policy']=='clearance';assert plan['threat_replan']=='once'
    ready=json.loads((root/'agent/broker-ready.json').read_text());assert ready['device']=='cpu' and ready['clearance_proxy_enabled']==enabled
    source=Path(plan['checkpoint']);baseline=Broker('new-policy',source)
    events=root/'strategy-trace.jsonl.replan.jsonl';releases={e['decision_id']:e for e in map(json.loads,events.read_text().splitlines())} if events.exists() else {}
    sent={e['decision_id']:e for e in map(json.loads,(root/'typed.jsonl').read_text().splitlines()) if e['event']=='native_action_sent' and e.get('decision_id') is not None}
    proposals=[json.loads(x) for x in (root/'agent/typed-broker.jsonl').read_text().splitlines()];overrides=[]
    for p in proposals:
        q=p['request'];n=q['request_id'];raw=(root/f'agent/request-{n:08d}.json').read_bytes();model=baseline.propose(raw,n);index=model['response']['selected_index']
        assert p['model_sha256']==model['model_sha256']==sha(source) and p['value']==model['value']
        assert p['model_recommended_index']==index and p['clearance_proxy_enabled']==enabled
        if enabled:expected=choose(q,index,releases.get(n))
        else:expected=dict(index=index,overridden=False,method='frozen_model_argmax',reason='proxy_disabled')
        assert p['proxy']==expected and p['response']['selected_index']==expected['index']
        if expected['overridden']:
            assert n in releases and n in sent and sent[n]['candidate']==q['candidates'][expected['index']] and sent[n]['request_sha256']==p['response']['request_sha256']
            assert sent[n]['op']=='move'
            overrides.append(dict(decision_id=n,day=q['day'],native_request_id=sent[n]['native_request_id'],
                request_sha256=p['response']['request_sha256'],model_candidate=q['candidates'][index],actual_candidate=q['candidates'][expected['index']],proxy=expected))
    assert all(sha(Path(p))==h for p,h in proof['input_sha256'].items())
    out.mkdir(parents=True,exist_ok=False)
    report=dict(passed=True,classification='scripted_evaluation_only',policy=plan['decision_policy'],proposals=len(proposals),
        frozen_model_recommendations_and_values_exact=True,overrides=len(overrides),details=overrides,
        native_execution_proof_sha256=sha(proof_path),input_sha256={str(p):sha(p) for p in [proof_path,source,root/'agent/typed-broker.jsonl',Path(__file__),HERE/'clearance_proxy.py',HERE/'clearance_broker.py']},
        optimizer_steps=0,training_samples=0,expert_labels=0,
        limitation='Real scripted actions and coordinate changes only. No safety, overall utility, human tactics or learning gain certification.')
    (out/'AUDIT.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k not in ('details','input_sha256')},indent=2));return report
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('proof',type=Path);p.add_argument('out',type=Path);a=p.parse_args();audit(a.root,a.proof,a.out)
