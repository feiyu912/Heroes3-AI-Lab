"""CPU-only paired raw-prefix and stability review, with explicit EOF handling.

Sequence equality covers the recorded projection only, never the complete world.
Existing native/runner reports and source files are read-only inputs.
"""
import argparse
from collections import Counter
import json
import re
from pathlib import Path
from audit_replan_v2 import require, sha

HERE = Path(__file__).resolve().parent
ANSI = re.compile(r'\x1b\[[0-9;]*m')
MOVEMENT = re.compile(r': Hero (.*?) starts movement from \(([-\d ]+)\) to \(([-\d ]+)\)\.')


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def canonical_sha(value):
    import hashlib
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def first_difference(left, right):
    """Return a 1-based difference, including a missing tail on either side."""
    for index in range(max(len(left),len(right))):
        a = left[index] if index < len(left) else None
        b = right[index] if index < len(right) else None
        if index >= len(left) or index >= len(right) or a != b:
            return dict(index=index+1,off_eof=index>=len(left),once_eof=index>=len(right),off=a,once=b)
    return None


def policy_action(proposal):
    q, r = proposal['request'],proposal['response']
    choice = q['candidates'][r['selected_index']]
    result = {key:q[key] for key in ('day','own_turn','player','hero','from')}
    result['op'] = r['op']
    if r['op'] == 'move':
        result.update({key:choice[key] for key in ('kind','position','next')})
    return result


def parse_log(raw):
    moves, releases, sent, budget_lines = [], [], {}, []
    for number,line in enumerate(raw.splitlines(),1):
        line = ANSI.sub('',line)
        if 'starts movement' in line:
            match = MOVEMENT.search(line)
            require(match is not None,'Unparsed server movement line '+str(number))
            name,start,end = match.groups()
            coords = lambda text:[int(item) for item in text.split()]
            moves.append(dict(line=number,hero_log_name=name,start=coords(start),end=coords(end)))
        if 'DirectorThreatReplan {' in line:
            event = json.JSONDecoder().raw_decode(line.split('DirectorThreatReplan ',1)[1])[0]
            releases.append(dict(line=number,event=event))
        if 'DirectorTypedEvent ' in line:
            event = json.JSONDecoder().raw_decode(line.split('DirectorTypedEvent ',1)[1])[0]
            if event['event']=='native_action_sent' and event.get('decision_id') is not None:
                identity = event['decision_id']
                require(identity not in sent,'Duplicate real policy native send')
                sent[identity] = number
        if 'DirectorAI: move budget for this turn exhausted (' in line:
            budget_lines.append(dict(line=number,text=line))
    return dict(movements=moves,releases=releases,sent=sent,budget_lines=budget_lines)


def movement_projection(events):
    return [{k:event[k] for k in ('hero_log_name','start','end')} for event in events]


def movement_comparison(off,once):
    difference = first_difference(movement_projection(off),movement_projection(once))
    if difference is not None:
        index = difference['index']-1
        difference['off_line'] = off[index]['line'] if index < len(off) else None
        difference['once_line'] = once[index]['line'] if index < len(once) else None
    return dict(off_count=len(off),once_count=len(once),first_difference=difference,
                recorded_order_exact=difference is None,
                off_projection_sha256=canonical_sha(movement_projection(off)),
                once_projection_sha256=canonical_sha(movement_projection(once)))


def stability(proposals,typed,parsed,cap):
    previous = {}
    goal_changes, reversals = [], []
    move_counts = Counter()
    for p in proposals:
        q,r = p['request'],p['response']
        if r['op'] != 'move':
            continue
        current = policy_action(p)
        key = q['hero'],q['own_turn']
        move_counts[q['own_turn']] += 1
        old = previous.get(key)
        if old is not None:
            before,now = old['action'],current
            old_goal = before['position'],before['kind']
            if (now['position'],now['kind']) != old_goal:
                goal_changes.append(dict(decision_id=q['request_id'],previous_decision_id=old['decision_id'],
                    day=q['day'],own_turn=q['own_turn'],hero=q['hero'],old_goal=before['position'],new_goal=now['position'],
                    previous_goal_reached=q['from']==before['position'],
                    previous_goal_still_candidate=any(c['op']=='move' and (c['position'],c['kind'])==old_goal for c in q['candidates'])))
            if before['from']!=before['next'] and now['from']==before['next'] and now['next']==before['from']:
                reversals.append(dict(decision_id=q['request_id'],previous_decision_id=old['decision_id'],
                    day=q['day'],own_turn=q['own_turn'],hero=q['hero'],previous_from=before['from'],
                    previous_next=before['next'],next=now['next']))
        previous[key] = dict(decision_id=q['request_id'],action=current)
    automatic = [event for event in typed if event['event']=='native_action_sent' and event.get('decision_id') is None]
    reasons = Counter(event.get('automatic_reason') for event in automatic)
    cap_sends = [event for event in automatic if event.get('automatic_reason')=='native_move_budget']
    require(all(count<=cap for count in move_counts.values()),'Policy movement count exceeds native per-turn cap')
    return dict(within_turn_goal_changes=len(goal_changes),goal_change_details=goal_changes,
                selected_immediate_step_reversals=len(reversals),selected_step_reversal_details=reversals,
                max_policy_moves_per_own_turn=max(move_counts.values(),default=0),native_move_cap=cap,
                own_turn_move_counts=dict(sorted(move_counts.items())),
                native_cap_log_count=len(parsed['budget_lines']),native_cap_log_events=parsed['budget_lines'],
                native_cap_end_turn_count=len(cap_sends),native_cap_end_turn_events=cap_sends,
                cap_log_and_end_turn_counts_agree=len(cap_sends)==len(parsed['budget_lines']),
                automatic_end_turn_reasons=dict(reasons),
                definitions='Goal switches compare consecutive selected moves for the same hero/own_turn. Reversals compare selected from/next coordinates, not a guarantee that a blocking visit displaced the hero.')


def check_source_inputs(report):
    require(report.get('passed') is True and report.get('fixture') is False and
            report.get('whole_game_execution_reaudited') is True,'Independent real execution audit required')
    require(all(sha(Path(path))==expected for path,expected in report['input_sha256'].items()),
            'Original input/source changed since independent execution audit')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('pairs',type=Path)
    parser.add_argument('execution_review',type=Path)
    parser.add_argument('out',type=Path)
    args = parser.parse_args()
    require(not args.out.exists(),'Output directory must be fresh')
    original = args.pairs/'RESULT.json'
    result = json.loads(original.read_text())
    execution_summary_path = args.execution_review/'AUDIT.json'
    execution_summary = json.loads(execution_summary_path.read_text())
    require(result['passed'] is True and len(result['pairs'])==8,'Completed 8-pair diagnostic required')
    require(execution_summary['passed'] is True and execution_summary['native_games_reaudited']==16,
            'Completed 16-arm independent execution review required')
    require(sha(original)==execution_summary['original_result_sha256'],'Original paired result changed')
    expected_arms = {(x['pair'],x['arm']):x for x in execution_summary['arms']}
    input_paths = [Path(__file__),original,args.pairs/'PLAN.json',execution_summary_path]
    pairs = []
    for original_pair in result['pairs']:
        pair_number = original_pair['pair']
        arms = {}
        for arm in ('a','b'):
            root = args.pairs/f'pair-{pair_number:02d}'/arm/'native'
            review_path = args.execution_review/f'pair-{pair_number:02d}'/arm/'AUDIT.json'
            require(sha(review_path)==expected_arms[pair_number,arm]['audit_sha256'],'Independent arm report changed')
            review = json.loads(review_path.read_text())
            check_source_inputs(review)
            plan = json.loads((root/'PLAN.json').read_text())
            job = original_pair['job']
            require((plan['seed'],plan['map'],plan['opponent'],plan['owned_player'])==
                    (job['seed'],job['map'],job['opponent'],job['player']),'Native job differs from paired schedule')
            require(plan['threat_replan']==('off' if arm=='a' else 'once'),'Arm mode mismatch')
            proposals = rows(root/'agent/typed-broker.jsonl')
            typed = rows(root/'typed.jsonl')
            parsed = parse_log((root/'client.log').read_text(errors='replace'))
            require([event['event']['decision_id'] for event in parsed['releases']]==
                    [event['decision_id'] for event in review['details']],'Release order differs from verified execution review')
            cap_header = Path(plan['capsule'])/'source-snapshot/AI/DirectorAI/CDirectorAI.h'
            cap_match = re.search(r'MAX_MOVES_PER_TURN\s*=\s*(\d+)',cap_header.read_text())
            require(cap_match is not None,'Compiled capsule move cap missing')
            arm_stability = stability(proposals,typed,parsed,int(cap_match[1]))
            arms[arm] = dict(proposals=proposals,typed=typed,parsed=parsed,stability=arm_stability,
                             execution_audit=review,root=root)
            input_paths += [review_path,cap_header,root/'PLAN.json',root/'client.log',root/'agent/typed-broker.jsonl',root/'typed.jsonl']
        off,once = arms['a'],arms['b']
        requests = [[p['request'] for p in arm['proposals']] for arm in (off,once)]
        actions = [[policy_action(p) for p in arm['proposals']] for arm in (off,once)]
        request_difference = first_difference(*requests)
        # Compact reporting avoids duplicating hundreds of full candidate rows.
        if request_difference is not None:
            for name in ('off','once'):
                value = request_difference[name]
                request_difference[name] = None if value is None else dict(
                    request_id=value['request_id'],day=value['day'],own_turn=value['own_turn'],
                    hero=value['hero'],candidate_count=len(value['candidates']),projection_sha256=canonical_sha(value))
        observations = [[{k:v for k,v in q.items() if k!='candidates'} for q in sequence] for sequence in requests]
        observation_difference = first_difference(*observations)
        choice_difference = first_difference(*actions)
        full_movements = movement_comparison(off['parsed']['movements'],once['parsed']['movements'])
        releases = once['parsed']['releases']
        first_release = releases[0] if releases else None
        prefix = None
        if first_release is not None:
            identity = first_release['event']['decision_id']
            require(identity in off['parsed']['sent'],'No corresponding off-arm native action anchor')
            off_cut,once_cut = off['parsed']['sent'][identity],first_release['line']
            off_prefix = [e for e in off['parsed']['movements'] if e['line']<off_cut]
            once_prefix = [e for e in once['parsed']['movements'] if e['line']<once_cut]
            prefix = movement_comparison(off_prefix,once_prefix)
            prefix.update(off_anchor_line=off_cut,once_release_line=once_cut,decision_id=identity,
                          off_anchor='Before native_action_sent for the corresponding decision ID',
                          once_anchor='Strictly before the first actual bounded_threat_replan log line',
                          limitation='Complete recorded server movement prefixes at these anchors; logging/ordering differences alone are not a complete-world divergence proof.')
        pair = dict(pair=pair_number,job=original_pair['job'],
                    request_counts={'off':len(requests[0]),'once':len(requests[1])},
                    first_request_difference=request_difference,first_non_candidate_observation_difference=observation_difference,
                    first_semantic_policy_choice_difference=choice_difference,semantic_policy_actions_all_identical=choice_difference is None,
                    first_release=first_release,
                    all_server_movement_comparison=full_movements,pre_first_release_movement_prefix=prefix,
                    stability={'off':off['stability'],'once':once['stability']},
                    original_runner_diagnostics={k:original_pair.get(k) for k in
                        ('first_request_difference','first_movement_difference','movement_order_difference_before_release',
                         'observed_request_difference_before_release')},
                    ability_improvement_claim=False)
        pairs.append(pair)
    hashes = {str(path):sha(path) for path in input_paths}
    require(sha(original)==execution_summary['original_result_sha256'],'Original result changed during review')
    require(all(sha(Path(path))==expected for path,expected in hashes.items()),'Review input changed during audit')
    summary = dict(passed=True,pairs=pairs,fixture=False,new_native_games=0,optimizer_steps=0,training_samples=0,
                   all_eight_semantic_policy_sequences_identical=all(p['semantic_policy_actions_all_identical'] for p in pairs),
                   full_movement_order_difference_pairs=[p['pair'] for p in pairs if not p['all_server_movement_comparison']['recorded_order_exact']],
                   pre_release_movement_prefix_difference_pairs=[p['pair'] for p in pairs if p['pre_first_release_movement_prefix'] is not None and not p['pre_first_release_movement_prefix']['recorded_order_exact']],
                   total_cap_end_turn_events=sum(s['native_cap_end_turn_count'] for p in pairs for s in p['stability'].values()),
                   input_sha256=hashes,finaltest_touched=False,ability_improvement_claim=False,
                   limitation='Recorded requests, selected policy actions, server movement order and cap/stability projections only. No complete-world determinism, safe retreat, expert behavior or causal superiority certification.')
    args.out.mkdir(parents=True,exist_ok=False)
    (args.out/'AUDIT.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps({k:v for k,v in summary.items() if k not in ('pairs','input_sha256')},indent=2))


if __name__=='__main__':
    main()
