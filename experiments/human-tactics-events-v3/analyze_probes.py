"""Controlled same-round subject-level evidence, not aggregate count inference."""
import gzip
import json
from pathlib import Path
from events_provenance import digest


def read(path):
    record=json.loads(path.read_text())
    assert digest(record['archive'])==record['archive_sha256']
    with gzip.open(record['archive'],'rt') as f:
        return json.load(f)


def analyze(data):
    by_round={}
    unknown=[]
    for b in data['batches']:
        if b['round_before'] is None or b['round_before']!=b['round_after']:
            unknown.append(b['batch_id'])
            continue
        rnd=b['round_before']
        for i,e in enumerate(b['events']):
            if e['kind']!=2 or e.get('attacker_side')!=0 or e.get('attack_flags',0)&(1|2|64):
                continue
            for target in e['targets']:
                if target.get('defender_side')!=1 or target.get('flags',0)&(2|16):
                    continue
                subject=target['defender_id']
                # Our step's action window is strict, so only the selected unit's
                # primary attack is eligible. All probe attackers are pikemen.
                t=data['transitions'][b['caused_by_step']]
                win=t['action_window']
                if win['status']!='matched' or i not in win['attack_indices']:
                    continue
                counters=[j for j in win['counter_indices']
                          if b['events'][j].get('attacker_id')==subject
                          and any(x.get('defender_id')==e['attacker_id']
                                  for x in b['events'][j].get('targets',[]))]
                row=dict(batch_id=b['batch_id'],event_index=i,round=rnd,subject_id=subject,
                         attacker_id=e['attacker_id'],counter_event_indices=counters,
                         subject_killed=bool(target['flags']&1),damage=target['damage'],killed_count=target['killed'])
                by_round.setdefault((rnd,subject),[]).append(row)
    sequences=[]
    for (rnd,subject), rows in sorted(by_round.items()):
        if len(rows)<2:
            continue
        prior_counter=False
        after_spent=[]
        for r in rows:
            if prior_counter and not r['counter_event_indices'] and not r['subject_killed']:
                after_spent.append(r)
            prior_counter=prior_counter or bool(r['counter_event_indices'])
        sequences.append(dict(round=rnd,subject_id=subject,attacks=rows,
                              counters=sum(len(r['counter_event_indices']) for r in rows),
                              survived_no_counter_after_prior_counter=after_spent))
    return dict(sequences=sequences,unknown_round_batches=unknown,
                explanation='Only same-round strict own-action primary pikeman melee; subject is the single enemy stack')


def main():
    here=Path(__file__).resolve().parent
    results={}
    for i,kind in [(0,'swordsman_default_one'),(1,'royal_griffin_unlimited')]:
        data=read(here/'runs/probes'/f'probe-{i}.json')
        results[kind]=analyze(data)
    regular=results['swordsman_default_one']['sequences']
    unlimited=results['royal_griffin_unlimited']['sequences']
    finite_examples=[s for s in regular if s['survived_no_counter_after_prior_counter']]
    unlimited_examples=[s for s in unlimited if s['counters']>=2]
    results.update(finite_observed=bool(finite_examples),unlimited_control_observed=bool(unlimited_examples),
                   expert_certified=False,bc_eligible=False)
    (here/'RETALIATION_PROBE_RESULTS.json').write_text(json.dumps(results,indent=2))
    print(json.dumps(dict(finite_observed=bool(finite_examples),unlimited_control_observed=bool(unlimited_examples),
                          finite_sequences=len(finite_examples),unlimited_sequences=len(unlimited_examples))))


if __name__=='__main__':
    main()
