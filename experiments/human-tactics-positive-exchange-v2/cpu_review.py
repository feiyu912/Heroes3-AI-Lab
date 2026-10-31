"""CPU-only counterexamples and truthful archived graph replay; no env creation."""
import argparse
import copy
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import numpy as np
from visible_exchange import choose, decide
from event_audit import action_window

HERE = Path(__file__).resolve().parent
OLD = HERE.parent/'human-tactics-visible-exchange-v1-pilot02'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def unpack(row):
    return dict(nodes={k: np.asarray(v, dtype=np.float32) for k,v in row['nodes'].items()},
        edges={tuple(e['relation']): dict(index=np.asarray(e['index'],dtype=np.int64),
            attrs=np.asarray(e['attrs'],dtype=np.float32)) for e in row['edges']},
        active_action_ids=np.asarray(row['active_action_ids'],dtype=np.int64))


def tests():
    results=[]
    def check(name, base_score, alt_score, expected, **changes):
        facts={0:dict(actor=3,ordinary_melee=True,net_permille=base_score),
               1:dict(actor=3,ordinary_melee=True,net_permille=alt_score)}
        facts[1].update(changes)
        before=copy.deepcopy(facts)
        selected,_=decide([0,1],0,facts)
        assert selected==expected, name
        assert repr(facts)==repr(before),name+' mutated input'
        results.append(name)
    for name,b,a,e in [('negative_to_zero',-6,0,0),('negative_to_negative',-6,-2,0),
        ('negative_to_positive',-6,.1,1),('positive_gain',0,5,1),
        ('exact_margin',1,2,0),('above_margin',1,2.001,1),
        ('regression',5,1,0),('equal',5,5,0),('unknown_base',None,5,0),
        ('nan_base',float('nan'),5,0),('infinite_base',float('inf'),5,0),
        ('nan_candidate',0,float('nan'),0),('infinite_candidate',0,float('inf'),0),
        ('unknown_candidate',0,None,0),('boolean_candidate',-5,True,0)]:
        check(name,b,a,e)
    check('different_actor',0,5,0,actor=8)
    check('missing_actor',0,5,0,actor=None)
    check('special_or_nonmelee',0,5,0,ordinary_melee=False)
    for malformed in ('duplicate','illegal_baseline','missing_facts','extra_facts'):
        legal=[0,1];base=0;facts={a:dict(actor=1,ordinary_melee=True,net_permille=a*5) for a in legal}
        if malformed=='duplicate':legal=[0,0,1]
        if malformed=='illegal_baseline':base=4
        if malformed=='missing_facts':del facts[1]
        if malformed=='extra_facts':facts[2]=facts[1]
        try:decide(legal,base,facts)
        except ValueError:pass
        else:raise AssertionError(malformed)
        results.append('reject_'+malformed)
    facts={a:dict(actor=1,ordinary_melee=True,net_permille=0 if a==0 else 5) for a in (0,1,2)}
    assert decide([2,0,1],0,facts)[0]==decide([0,1,2],0,facts)[0]==1
    results.append('order_invariant_tie')
    facts[0]['ordinary_melee']=False
    assert decide([0,1,2],0,facts)[0]==0
    results.append('preserve_teacher_nonmelee')
    return results


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--output',required=True)
    args=ap.parse_args()
    output=Path(args.output)
    assert not output.exists()
    spec=importlib.util.spec_from_file_location('old_exchange',OLD/'visible_exchange.py')
    old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
    checks=tests();rows=[];decisions=0;new_overrides=0;changes=[];raw_hashes={}
    frozen_inputs={}
    for path in sorted((OLD/'runs/train').glob('*.json.gz')):
        raw_hashes[str(path)]=sha(path)
        summary_path=path.with_suffix('')
        summary=json.loads(summary_path.read_text())
        raw_hashes[str(summary_path)]=sha(summary_path)
        for p,value in summary['frozen_artifacts'].items():
            if p in frozen_inputs:assert frozen_inputs[p]==value
            frozen_inputs[p]=value
        assert raw_hashes[str(path)]==summary['archive_sha256']
        with gzip.open(path,'rt') as f:d=json.load(f)
        assert summary['terminated'] and not summary['truncated']
        end=[e for e in d['batches'][-1]['events'] if e['kind']==3]
        assert len(end)==1 and end[0]['winner']==summary['terminal_outcome']['winner']
        side=int(summary['role']=='defender')
        for t in d['transitions']:
            events=d['batches'][t['post_batch_id']]['events'];w=t['action_window']
            assert w==action_window(events,side,t['known_actor_id_before'],w['native_action_type'])
            assert w['status']=='matched'
            baseline=t['quality'].get('teacher_action',t['executed_action'])
            obs=unpack(t['observation_before']);obs['teacher_action_id']=baseline
            before=copy.deepcopy(t['observation_before'])
            a,q=choose(obs);old_a,old_q=old.choose(obs)
            assert a in t['legal_actions']
            assert t['observation_before']==before
            # Deliberately poisoned withheld fields cannot affect selection.
            poisoned=dict(obs,seed=-999,battle_events=object(),terminal_outcome=object(),
                          quality='WITHDRAWN_EXPERT',future_rng=object(),remaining_retaliations=999)
            assert choose(poisoned)==(a,q)
            # np graph arrays must also be unchanged by either selector.
            assert all(np.array_equal(obs['nodes'][k],np.asarray(v,dtype=np.float32),equal_nan=True)
                       for k,v in before['nodes'].items())
            assert all(np.array_equal(obs['edges'][tuple(e['relation'])][field],
                       np.asarray(e[field],dtype=np.int64 if field=='index' else np.float32),equal_nan=True)
                       for e in before['edges'] for field in ('index','attrs'))
            if summary['policy']=='visible-exchange':
                assert old_a==t['executed_action'] and old_q==t['quality']
            new_overrides+=int(q['overrode_teacher']);decisions+=1
            if a!=old_a:changes.append(dict(archive=path.name,step=t['step_id'],old=old_a,new=a))
            if summary['policy']=='visible-exchange' and old_q['overrode_teacher']:
                rows.append(dict(archive=path.name,archive_sha256=raw_hashes[str(path)],
                    step=t['step_id'],baseline=baseline,executed=old_a,new_replay=a,
                    before_estimate=old_q['baseline_estimate'],after_estimate=old_q['selected_estimate'],
                    strict_window=w,strict_events=events[w['start']:w['finish']+1],
                    terminal=summary['terminal_outcome']))
    assert decisions==357 and len(rows)==4
    assert all(sha(p)==value for p,value in frozen_inputs.items())
    report=dict(schema='positive-exchange-v2-cpu-review-v1',passed=True,
        synthetic_counterexample_tests=checks,synthetic_count=len(checks),
        archived_native_games_read=16,archived_decisions_replayed=decisions,
        old_actual_overrides=rows,new_policy_overrides_on_archived_states=new_overrides,
        new_vs_old_archived_state_changes=changes,raw_sha256=raw_hashes,
        historical_frozen_inputs_verified=frozen_inputs,
        withheld_field_poisoning_and_graph_immutability=True,
        policy_sha256=sha(HERE/'visible_exchange.py'),new_native_games=0,
        optimizer_steps=0,bc_eligible=False,
        limitation='Replayed states include old-policy descendants; no new trajectory outcomes inferred.')
    output.write_text(json.dumps(report,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k not in
        ('old_actual_overrides','raw_sha256','synthetic_counterexample_tests','new_vs_old_archived_state_changes')},indent=2))


if __name__=='__main__':main()
