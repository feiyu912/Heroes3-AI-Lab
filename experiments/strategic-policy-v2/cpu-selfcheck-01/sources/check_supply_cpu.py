"""Pure CPU policy checks plus explicitly reconstructed archive fixtures.

Does not launch games or import Torch. Old native v2 requests stay v2 and must
fallback. Enriched fixtures below are NOT claimed to be native v3 observations.
"""
import copy
import hashlib
import json
from pathlib import Path
from supply_policy import choose,VERSION

HERE=Path(__file__).resolve().parent
EVIDENCE=HERE.parent/'strategic-nk-failure-audit-20261018'
OUT=HERE/'supply-cpu-audit-01'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def synthetic():
    base=dict(schema='strategy-candidates-v3',own_army_value=1000,from_pos=[10,10,0],
        own_towns=[dict(position=[12,10,0],army_value=1000)],visible_threats=[],
        candidates=[dict(kind=5,position=[8,10,0],next=[9,10,0],path_cost=.2),
                    dict(kind=4,position=[12,10,0],next=[11,10,0],path_cost=.2)])
    base['from']=base.pop('from_pos')
    cases=[]
    def check(name,r,expected):
        before=copy.deepcopy(r)
        actual,reason=choose(r,0)
        assert actual==expected and 0<=actual<len(r['candidates']),name
        assert r==before,name+' mutated input'
        cases.append(dict(name=name,selected=actual,reason=reason))
    check('valuable_nearby_supply',base,1)
    r=copy.deepcopy(base);r['own_towns'][0]['army_value']=10;check('tiny_supply_stays',r,0)
    r=copy.deepcopy(base);r['candidates'][1]['path_cost']=10;check('far_supply_stays',r,0)
    r=copy.deepcopy(base);r['own_towns'][0]['position']=[13,10,0];check('unknown_town_stays',r,0)
    r=copy.deepcopy(base);r['schema']='strategy-candidates-v2';check('old_schema_stays',r,0)
    r=copy.deepcopy(base);del r['visible_threats'];check('missing_threats_stays',r,0)
    r=copy.deepcopy(base);r['visible_threats']=[dict(position=[11,10,0],approx_army_value=4000)];check('approaching_strong_threat_stays',r,0)
    r=copy.deepcopy(base);r['own_towns'][0]['position']=[8,10,0];r['own_towns'][0]['army_value']=300
    r['candidates'][1].update(position=[8,10,0],next=[9,10,0],path_cost=.3)
    r['candidates'][0]['next']=[11,10,0];check('low_gain_without_threat_stays',r,0)
    r['visible_threats']=[dict(position=[11,10,0],approx_army_value=4000)];check('safer_supply_under_visible_pressure',r,1)
    r=copy.deepcopy(base);r.update(seed='forbidden',map='forbidden',player=7,
        hidden_state={'army':999},terminal_outcome={'winner':1},battle_events=[{'kind':3}],quality='withdrawn')
    assert choose(r,0)==choose(base,0);check('irrelevant_fields_ignored',r,1)
    r=copy.deepcopy(base);r['own_towns'][0]['army_value']=float('inf')
    assert choose(r,0)[0]==0;cases.append(dict(name='nonfinite_town_stays',selected=0))
    r=copy.deepcopy(base);r['own_army_value']=0;check('zero_own_unknown_stays',r,0)
    r=copy.deepcopy(base);r['own_towns']*=2;check('duplicate_town_ambiguous_stays',r,0)
    r=copy.deepcopy(base);r['candidates'][1]['kind']=True;check('boolean_kind_not_supply',r,0)
    r=copy.deepcopy(base);r['own_towns'][0]['position'][2]=1;check('other_map_level_stays',r,0)
    for invalid in (-1,2,False):
        try:choose(base,invalid)
        except ValueError:pass
        else:raise AssertionError('invalid baseline accepted')
    assert choose(base,1)[0]==1
    return cases


def main():
    assert not OUT.exists(),'Preserve existing CPU audit'
    cases=synthetic()
    audit=json.loads((EVIDENCE/'AUDIT.json').read_text())
    details=json.loads((EVIDENCE/'DETAILS.json').read_text())
    rows=[];old=0;reconstructed=0;changes=0;native_strength_crosschecks=0
    for ep,de in zip(audit['episodes'],details['episodes']):
        trace=Path(ep['native']['run_dir'])/'strategy-trace.jsonl'
        assert sha(trace)==ep['evidence'][str(trace)]
        states=[(i,json.loads(x))for i,x in enumerate(trace.read_text().splitlines(),1)]
        moving=[(i,s)for i,s in states if s['event']=='before_move']
        decisions=[json.loads(x)for x in (trace.parent/'strategy-decisions.jsonl').read_text().splitlines()]
        assert len(moving)==len(decisions)==len(de['request_manifest'])
        # Solve visible own-army strength coefficients from two archived own
        # descriptors: 20a+10b=2860, 34a+19b=5114. Not a gameplay assumption.
        coefficients={0:80.0,2:126.0}
        # Independently crosscheck every matching own army before using these
        # coefficients to reconstruct an own-town count vector's value.
        for (line,s),d,manifest in zip(moving,decisions,de['request_manifest']):
            p=Path(manifest['path']);assert sha(p)==manifest['sha256']
            request=json.loads(p.read_text());baseline=d['selected_candidate']
            assert request['schema']=='strategy-candidates-v2'
            assert choose(request,baseline)[0]==baseline
            old+=1
            hero=next((h for h in s['heroes'] if h['id']==request['hero']),None)
            if hero is None or any(c not in coefficients for c,n in hero['army']):continue
            assert sum(coefficients[c]*n for c,n in hero['army'])==request['own_army_value']
            native_strength_crosschecks+=1
            supplies=[c for c in request['candidates']if c['kind']==4]
            if len(supplies)!=1 or len(s['towns'])!=1:continue
            army=s['towns'][0]['army']
            if any(c not in coefficients for c,n in army):continue
            fixture=copy.deepcopy(request)
            fixture.update(schema='strategy-candidates-v3',
                own_towns=[dict(position=supplies[0]['position'],army_value=sum(coefficients[c]*n for c,n in army))],
                visible_threats=[])
            selected,reason=choose(fixture,baseline)
            assert 0<=selected<len(request['candidates'])
            assert selected==baseline or request['candidates'][selected]['kind']==4
            reconstructed+=1;changes+=selected!=baseline
            rows.append(dict(origin='RECONSTRUCTED_CPU_FIXTURE_NOT_NATIVE_V3',
                threat_assumption='No threats supplied for this fixture; not an assertion that the original game had none',
                seed=ep['config']['seed'],request_path=str(p),request_sha256=sha(p),trace=str(trace),trace_sha256=sha(trace),
                trace_line=line,own_army_strength_recalculation_matched=True,
                candidate_town_position_source='unique original kind4 candidate paired with the only own town in native pre-move state',
                own_town_army_counts=army,fixture=fixture,baseline=baseline,selected=selected,reason=reason))
    assert old==706
    OUT.mkdir()
    result=dict(schema='supply-aware-cpu-check-v1',passed=True,policy_version=VERSION,policy_sha256=sha(HERE/'supply_policy.py'),
        synthetic_cases=cases,invalid_baseline_rejection_passed=True,input_unchanged=True,
        old_native_v2_requests=old,old_v2_fallbacks=old,native_own_strength_crosschecks=native_strength_crosschecks,
        reconstructed_public_state_fixtures=reconstructed,reconstructed_fixtures_changing_choice=changes,
        reconstructed_rows=rows,real_native_v3_games=0,training_updates=0,bc_eligible=0,
        ability_improvement_proven=False,source_audit_sha256=sha(EVIDENCE/'AUDIT.json'))
    (OUT/'CPU_AUDIT.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k not in ('reconstructed_rows','synthetic_cases')}))


if __name__=='__main__':main()
