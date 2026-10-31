"""Independent completed update4 DEV raw/CPU-policy audit; no game/GPU execution."""
import hashlib,json,os,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;RUN=HERE.parent;POLICY=RUN.parent/'strategic-learned-build-exploration-policy-v1'
LAB=Path('/root/heroes3-ai-lab');DEV=LAB/'evaluations/strategic-build-exploration-update4-dev-01'
sys.path[:0]=[str(RUN),str(POLICY)]
from pipeline_common import source_inputs,capsule_inputs,validate_native_epoch,validate_capsule
from broker import Broker
from model_io import load_model,digest_json
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_text())
def rows(path):return [json.loads(x) for x in Path(path).read_text().splitlines() if x]
def write(path,value):Path(path).write_text(json.dumps(value,indent=2)+'\n')
def main():
    outer=read(DEV/'PLAN.json');result=read(DEV/'RESULT.json');assert result['passed'] and len(result['pairs'])==8
    capsule=LAB/'evaluations/strategic-learned-economy-build-capsule-01';validate_capsule(capsule)
    models={arm:Broker('new-policy',Path(path)) for arm,path in outer['model_paths'].items()}
    assert models['b'].model_sha256=='24b8c3f3d5ddacd61e48bd87a526c1fd59b2a83eafbdacfe44bd5ddcfb5d3e6d'
    _,bundle,model_sha=load_model(Path(outer['model_paths']['b']),'cpu')
    assert bundle['training_updates']==4 and bundle['optimizer_steps_total']==504 and bundle['complete_update_boundary']
    assert bundle['protocol_sha256']==digest_json(bundle['protocol']) and all(sha(path)==h for path,h in bundle['protocol']['sources'].items())
    freeze={str(path):sha(path) for path in source_inputs()+capsule_inputs(capsule)+list((RUN/'continuation-dev-tools').glob('*.py'))+[RUN/'continuation-dev-tools/PLAN.md',DEV/'PLAN.json',DEV/'RESULT.json']+[Path(x) for x in outer['model_paths'].values()]}
    assert all(sha(path)==h for path,h in outer['input_sha256'].items())
    write(HERE/'INPUTS.json',freeze);cases=[];total=0;proposals_by_case={}
    for index,pair in enumerate(result['pairs']):
        assert pair['job']['seed']==2026103300+index
        for arm in ('a','b'):
            case=DEV/f'pair-{index:02d}'/arm;n=case/'native';dest=HERE/'raw-reaudit'/f'{index:02d}-{arm}';dest.parent.mkdir(exist_ok=True)
            proc=subprocess.run([sys.executable,str(RUN/'audit_game_v6.py'),str(n),str(dest)],capture_output=True,text=True,env=dict(os.environ,CUDA_VISIBLE_DEVICES=''))
            if proc.returncode:
                (HERE/f'FAIL-{index:02d}-{arm}.log').write_text(proc.stdout+'\n'+proc.stderr);raise ValueError(str(case))
            audit=read(dest/'AUDIT.json');assert audit==read(case/'raw-audit/AUDIT.json')
            plan=read(n/'PLAN.json');validate_native_epoch(audit,plan,read(n/'EXECUTION.json'))
            assert all(sha(path)==h for path,h in plan['hashes'].items()) and all(sha(n/name)==h for name,h in audit['raw_sha256'].items())
            proposals=rows(n/'agent/typed-broker.jsonl');events=rows(dest/'events.jsonl');sent={e['decision_id']:e for e in events if e['event']=='native_action_sent' and e['decision_id'] is not None}
            assert len(sent)==len(proposals)==audit['counts']['new_policy_decisions']
            assert len({e['native_request_id'] for e in sent.values()})==len(sent)
            for p in proposals:
                q=p['request'];r=p['response'];raw=(n/f"agent/request-{q['request_id']:08d}.json").read_bytes()
                assert json.loads(raw)==q and sha(n/f"agent/request-{q['request_id']:08d}.json")==r['request_sha256']
                assert p==models[arm].propose(raw,q['request_id'])
                assert sent[q['request_id']]['candidate']==q['candidates'][r['selected_index']]
            win=audit['winner']==('red' if plan['owned_player']==0 else 'blue');assert win is pair['arms'][arm]['win'] and audit['counts']==pair['arms'][arm]['counts']
            cases.append(dict(pair=index,arm=arm,case=str(case),win=win,counts=audit['counts'],decisions=len(proposals),model_sha256=models[arm].model_sha256,raw_audit_exact=True,all_cpu_proposals_exact=True))
            proposals_by_case[index,arm]=proposals;total+=len(proposals)
            print(json.dumps(dict(completed=len(cases),total=16,pair=index,arm=arm,choices=len(proposals))),flush=True)
    assert sum(c['win'] for c in cases if c['arm']=='a')==sum(c['win'] for c in cases if c['arm']=='b')==4
    assert sum(c['counts']['policy_builds'] for c in cases if c['arm']=='a')==67 and sum(c['counts']['policy_builds'] for c in cases if c['arm']=='b')==89
    assert all(sha(path)==h for path,h in freeze.items())
    pairs=[]
    for i in range(8):
        a,b=proposals_by_case[i,'a'],proposals_by_case[i,'b'];prefix=0;different_action=None
        for x,y in zip(a,b):
            if x['request']!=y['request']:break
            prefix+=1
            if different_action is None and x['response']['selected_index']!=y['response']['selected_index']:different_action=prefix
        pairs.append(dict(pair=i,initial_request_semantics_equal=a[0]['request']==b[0]['request'],equal_request_prefix=prefix,first_different_action_on_equal_request=different_action,a_decisions=len(a),b_decisions=len(b)))
    report=dict(passed=True,raw_audits_actually_rerun=16,full_cpu_proposals_actually_recomputed=total,all_source_capsule_raw_hashes_unchanged=True,cases=cases,pairs=pairs,
        wins=dict(initial=4,update4=4),builds=dict(initial=67,update4=89),checkpoint=dict(sha256=model_sha,training_updates=4,optimizer_steps_metadata_cpu_validated=504,protocol_sha256=bundle['protocol_sha256'],protocol_sources_match=True),
        gpu_optimizer_restore_rerun=False,source_scope='Checkpoint original protocol verified as saved; continuation outer controller is separate and not retroactively asserted to be in checkpoint protocol.',new_native_runs=0,new_gpu_runs=0,new_optimizer_steps=0)
    write(HERE/'DEV_REVIEW.json',report)
    print(json.dumps({k:v for k,v in report.items() if k not in ('cases','pairs')},indent=2))
if __name__=='__main__':main()
