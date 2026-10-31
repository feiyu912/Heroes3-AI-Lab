import gzip
import hashlib
import json
from pathlib import Path
from events_provenance import digest


def load(path):
    with gzip.open(path,'rt') as f:return json.load(f)


def physical(data):
    return dict(batches=data['batches'],terminal_outcome=data['episode']['terminal_outcome'],
                transitions=[{k:t[k] for k in ('executed_action','observation_before','observation_after','action_window')}
                             for t in data['transitions']])


def fingerprint(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def main():
    here=Path(__file__).resolve().parent
    control=json.loads((here/'runs/control.json').read_text())
    changed=json.loads((here/'runs/intervention-wait.json').read_text())
    source=load(control['reference_archive'])
    base=load(control['archive']);branch=load(changed['archive'])
    assert fingerprint(physical(source))==fingerprint(physical(base))
    pivot=control['intervention_step']
    for data in (base,branch):
        assert all(t['expected_prefix_obs_sha256']==t['actual_prefix_obs_sha256']
                   for t in data['transitions'][:pivot+1])
        assert data['episode']['matched_prefix_decisions']==pivot+1
        assert data['episode']['terminated'] and not data['episode']['truncated']
        assert len([e for e in data['batches'][-1]['events'] if e['kind']==3])==1
    a,b=base['transitions'][pivot],branch['transitions'][pivot]
    assert a['observation_before']==b['observation_before'] and a['legal_actions']==b['legal_actions']
    assert a['executed_action']!=b['executed_action']
    assert a['action_window']['native_action_type']==8 and b['action_window']['native_action_type']==6
    assert a['observation_after']!=b['observation_after']
    side=str(int(control['role']=='defender'))
    result=dict(passed=True,new_games=2,pivot_step=pivot,matched_prefix_decisions=pivot+1,
                exact_control_full_physical_replay=True,same_pivot_graph_and_legal_set=True,
                control_action=a['executed_action'],intervened_action=b['executed_action'],
                native_control_type=8,native_intervened_type=6,next_observation_diverged=True,
                control_success=control['success'],branch_success=changed['success'],
                control_losses=control['terminal_outcome']['casualties'][side],
                branch_losses=changed['terminal_outcome']['casualties'][side],
                source_archive_sha256=digest(control['reference_archive']),
                control_archive_sha256=digest(control['archive']),branch_archive_sha256=digest(changed['archive']),
                fair_search_teacher=False,eligible_for_bc=False,
                limitation='Same-seed future outcomes are not deployable information; intervention changes RNG consumption')
    (here/'PROBE_RESULTS.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result))


if __name__=='__main__':main()
