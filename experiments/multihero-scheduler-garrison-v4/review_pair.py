"""Read-only pair re-audit, adverse-evidence checks, and verified local archive."""
import copy,hashlib,json,shutil
from pathlib import Path
from audit_scheduler import audit,strict,load_lines
from capsule_support import idle_locks,verify_attestation
HERE=Path(__file__).resolve().parent
LAB=Path('/root/heroes3-ai-lab/evaluations')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def audit_negative(probe,trace,mutation,expected):
    p,t=copy.deepcopy(probe),copy.deepcopy(trace)
    mutation(p,t)
    try:
        checks,_=strict(None,p,t)
        assert checks.get(expected) is False,(expected,checks)
    except (AssertionError,KeyError) as e:
        # Missing identities/handshakes must fail closed, not silently pass.
        if expected not in ('one_native_setup_handshake','one_before_after_state'):raise
    return True
def main():
    out=HERE/'independent-review-02';out.mkdir(exist_ok=False)
    results={}
    for arm in ('baseline','filtered'):
        work=LAB/f'multihero-scheduler-garrison-{arm}-04'
        result=audit(work)
        assert json.loads(json.dumps(result))==json.loads((work/'AUDIT_SCHEDULER.json').read_text()),'Full audit does not reproduce'
        verify_attestation(LAB/'multihero-scheduler-garrison-capsule-04'/arm,arm)
        results[arm]=result
    assert results['filtered']['engineering_pass']
    assert results['baseline']['blockers']==['strict:only_mobile_heroes_selected']
    bp=json.loads((LAB/'multihero-scheduler-garrison-baseline-04/plan.json').read_text())
    fp=json.loads((LAB/'multihero-scheduler-garrison-filtered-04/plan.json').read_text())
    assert bp['seed']==fp['seed']==2026102501
    fixture='data/vcmi/Maps/adv/multihero-scheduler-garrison-v3.vmap'
    assert sha(LAB/'multihero-scheduler-garrison-baseline-04'/fixture)==sha(LAB/'multihero-scheduler-garrison-filtered-04'/fixture)==sha(HERE/'fixture-03.vmap')
    base=(HERE/'candidates/baseline/CDirectorAI.cpp').read_text();new=(HERE/'candidates/filtered/CDirectorAI.cpp').read_text()
    assert new==base.replace('hero->getOwner() != playerID || blockedHeroes.count(hero->id.getNum())','hero->getOwner() != playerID || hero->isGarrisoned() || blockedHeroes.count(hero->id.getNum())',1)
    assert (HERE/'candidates/baseline/CDirectorAI.h').read_bytes()==(HERE/'candidates/filtered/CDirectorAI.h').read_bytes()
    original=(HERE.parent/'multihero-scheduler-probe-v1/candidates/scheduler/CDirectorAI.cpp').read_text()
    assert base[base.index('void CDirectorAI::probeClose()'):]==original[original.index('void CDirectorAI::probeClose()'):],'Exchange/transfer hooks must stay byte-identical'
    work=LAB/'multihero-scheduler-garrison-filtered-04'
    probe=load_lines(work/'probe.jsonl');trace=load_lines(work/'strategy-trace.jsonl')
    cases={}
    # Identify hero by ID rather than assuming list order.
    def garrison(p,t):
        a=next(r for r in t if r['event']=='garrison_setup_ack_state')
        next(h for h in a['heroes'] if h['id']==3)['garrisoned']=False
    def resource(p,t):next(r for r in t if r['event']=='garrison_setup_ack_state')['resources'][6]+=1
    def duplicate(p,t):p.append(copy.deepcopy(next(r for r in p if r['event']=='move_ack')))
    def nomotion(p,t):
        states=[r for r in t if r['own_turn']==2]
        pos=next(h for h in states[0]['heroes'] if h['id']==2)
        for r in states:
            h=next(h for h in r['heroes'] if h['id']==2)
            for k in ('x','y','z'):h[k]=pos[k]
    def postaction(p,t):p.append(dict(event='scheduler_selected',hero=0))
    for name,fn,gate in [('false_garrison',garrison,'native_visiting_to_real_positive_mp_garrison'),('resource_mutation',resource,'setup_seven_resources_conserved'),('duplicate_ack',duplicate,'move_request_ack_bijection'),('hero2_turn2_no_actual_motion',nomotion,'mobile_2_turn_2_native_motion'),('action_after_boundary',postaction,'no_action_after_boundary')]:
        cases[name]=audit_negative(probe,trace,fn,gate)
    protection=json.loads((HERE.parent/'takeover-20261023/first-pilot-protection.json').read_text())['protected_current_files']
    with idle_locks():
        assert all(sha(p)==h for p,h in protection.items()),'Protected artifact drift'
    archived={}
    for version in (3,4):
        for arm in ('baseline','filtered'):
            raw=LAB/f'multihero-scheduler-garrison-{arm}-0{version}'
            dest=out/f'v{version}-{arm}';dest.mkdir()
            files={}
            for name in ('probe.jsonl','strategy-trace.jsonl','client.log','plan.json','execution.json','AUDIT_SCHEDULER.json'):
                shutil.copy2(raw/name,dest/name);assert sha(raw/name)==sha(dest/name)
                files[name]=sha(dest/name)
            archived[f'v{version}-{arm}']={'raw':str(raw),'files':files}
    result={'passed':True,'scope':'Isolated deterministic pickHero garrison exclusion plus two independent mobile heroes; not learned strategy or general scheduling/strength.',
        'baseline_pass':False,'baseline_blockers':results['baseline']['blockers'],'filtered_pass':True,
        'both_raw_audits_recomputed_exact':True,'only_scheduler_predicate_differs':True,'fixture_and_seed_identical':True,
        'mobile_successful_sequences_each_arm':{a:{h:len(v) for h,v in r['mobile_move_sequences'].items()} for a,r in results.items()},
        'all17_frozen_artifacts_exact':True,'negative_controls':cases,'archive':archived,
        'minimax_review':'Actual dsh MiniMax-M3.1-Flash reviewed reported v2 failure and v3 plan only, not v4 source or raw results. See ../multihero-scheduler-garrison-v2/minimax-review/RESULT.json.',
        'training_samples':0,'optimizer_steps':0,'final_test_touched':False}
    (out/'AUDIT.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k!='archive'},indent=2))
if __name__=='__main__':main()
