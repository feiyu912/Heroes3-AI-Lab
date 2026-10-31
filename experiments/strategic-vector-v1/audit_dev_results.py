"""Recompute paired development evidence after completion; never launches games."""
import argparse
import json
from pathlib import Path

from evaluate_dev import verify_native_consumption,summarize,sha


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    if a.out.exists():raise ValueError('Refuse overwrite')
    plan=json.loads((a.run/'plan.json').read_text());result=json.loads((a.run/'results.json').read_text())
    assert result['status']=='completed' and result['scores_certified']
    hashes_ok=all(sha(Path(path))==value for path,value in plan['hashes'].items())
    rows=[];sequences={}
    for index,row in enumerate(result['rows']):
        assert row['valid'] and row['win']is not None
        expected=plan['hashes'][plan['models'][row['model']]]
        verified=verify_native_consumption(Path(row['agent_dir']),row['native'],expected)
        native=row['native'];run=Path(native['run_dir'])
        io_ok=sha(run/'client.log')==native['log_sha256'] and sha(run/'strategy-trace.jsonl')==native['strategy_trace_sha256'] and sha(run/'strategy-decisions.jsonl')==native['strategy_decisions_sha256']
        assert verified['decisions']==row['verification']['decisions'] and io_ok
        assert row['win']==(native['winner']==row['job']['role'])
        rows.append(dict(row=index,pair=row['pair_index'],model=row['model'],native_decisions=verified['decisions'],raw_hashes_verified=io_ok,
                         strict_native_event_gate=verified['native_event_audit']['valid'],terminal_ack_missing_after_execution=verified['native_event_audit']['terminal_ack_missing_after_execution']))
        agent=Path(row['agent_dir'])
        events=[json.loads(line)for line in(agent/'broker-trace.jsonl').open()]
        commits=[e for e in events if e.get('event')=='decision_committed']
        sequences[(row['pair_index'],row['model'])]=[(json.loads((agent/e['request_file']).read_text()),e['action'])for e in commits]
    recomputed=summarize(result['rows'],plan['jobs'])
    same_scores=all(result[key]==recomputed[key]for key in ('pairs','net_win_delta','by_opponent_role','discordant_pairs','distinct_map_count'))
    report=dict(source_plan_sha256=sha(a.run/'plan.json'),source_results_sha256=sha(a.run/'results.json'),
        frozen_inputs_match=hashes_ok,rows=rows,recomputed_scores_match=same_scores,
        native_decisions_rechecked=sum(row['native_decisions']for row in rows),
        pair_action_request_sequences_equal=[dict(pair=i,equal=sequences[(i,'baseline')]==sequences[(i,'candidate')])for i in range(len(plan['jobs']))],
        optimizer_steps=0,test_split_touched=False,development_maps_previously_seen=True,
        distinct_map_count=recomputed['distinct_map_count'],confidence_interval=None,
        net_win_delta=recomputed['net_win_delta'],discordant_pairs=recomputed['discordant_pairs'],
        interpretation='Independent of optimization on two historically seen development maps; not final test or a claim of general improvement.')
    report['passed']=hashes_ok and same_scores and len(rows)==2*len(plan['jobs']) and all(row['strict_native_event_gate']for row in rows)
    a.out.write_text(json.dumps(report,indent=2));print(json.dumps(dict(passed=report['passed'],games=len(rows),decisions=report['native_decisions_rechecked'],net_win_delta=report['net_win_delta'],discordant=report['discordant_pairs'])))
    return 0 if report['passed']else 1


if __name__=='__main__':raise SystemExit(main())
