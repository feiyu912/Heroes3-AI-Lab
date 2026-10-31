"""Independent CPU reconstruction. Never imports the candidate decision code."""
import argparse
from collections import Counter
import gzip
import hashlib
import json
import math
from pathlib import Path
import numpy as np
from vcmi_gym.envs.v15.vcmi_env import Unit, Action, ACTION_TYPES
from vcmi_gym.envs.v15.pyconnector import EDGE_TYPES


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def select(graph, teacher):
    nodes={k:np.asarray(v,dtype=np.float32) for k,v in graph['nodes'].items()}
    edges={tuple(e['relation']):e for e in graph['edges']}
    legal=graph['active_action_ids']
    assert teacher in legal and len(legal)==len(set(legal))
    units=Unit.decode_many(nodes['Unit'])
    actor_edge=edges[('Action','By','Unit')]['index']
    actors=dict(zip(actor_edge[0],actor_edge[1]))
    target_relation=('Unit','IsMeleedBy','Action')
    target_edge=edges[target_relation]
    primary_size=EDGE_TYPES[target_relation]['attributes'][0]['size']
    targets={}
    for i,(unit,action) in enumerate(zip(*target_edge['index'])):
        is_primary=bool(np.argmax(target_edge['attrs'][i][:primary_size]))
        targets.setdefault(action,[]).append((unit,is_primary))
    scores={}
    relation=('Unit','MeleeDmg','Unit');edge=edges[relation]
    columns=EDGE_TYPES[relation]['attributes'];offset=0
    score_offset=None
    for col in columns:
        if col['name']=='ESTIMATED_NET_VALUE_REL_BF':
            assert col['encoding']=='LINNORM' and col['size']==1
            score_offset=offset;vmax=col['vmax']
        offset+=col['size']
    assert score_offset is not None
    for i,pair in enumerate(zip(*edge['index'])):
        scores[pair]=float(np.float32(edge['attrs'][i][score_offset]))*vmax
    facts={}
    for a in legal:
        u=actors[a];affected=targets.get(a,[])
        primary=[v for v,p in affected if p]
        ordinary=(int(Action.decode_one(nodes['Action'][a]).ACTION_TYPE)==ACTION_TYPES['AMOVE']
            and len(primary)==1 and len(affected)==1 and bool(units[primary[0]].IS_ENEMY)
            and not units[u].HAS_TWO_HEX_ATTACK_BREATH)
        facts[a]=(u,ordinary,scores.get((u,primary[0])) if primary else None)
    actor,ordinary,base=facts[teacher]
    selected=teacher
    if ordinary and base is not None and math.isfinite(base):
        candidates=[a for a,(u,o,s) in facts.items() if u==actor and o and s is not None
                    and math.isfinite(s) and s>0]
        if candidates:
            best=min(candidates,key=lambda a:(-facts[a][2],a))
            if facts[best][2]-base>1:selected=best
    return selected,facts


def window(events,side,known,kind):
    starts=[(i,e) for i,e in enumerate(events) if e['kind']==0 and e['side']==side]
    assert len(starts)==1
    start,e=starts[0];uid=e['stack_number']
    assert uid>=0 and (known is None or uid==known) and e['action_type']==kind
    finishes=[i for i in range(start+1,len(events)) if events[i]['kind']==1
        and events[i]['side']==side and events[i]['stack_number']==uid
        and events[i]['action_type']==kind]
    assert len(finishes)==1
    finish=finishes[0]
    assert not any(e['kind']==0 for e in events[start+1:finish])
    return start,finish


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--run',required=True)
    ap.add_argument('--output',required=True)
    args=ap.parse_args();run=Path(args.run);output=Path(args.output)
    assert not output.exists()
    # Refuse live/partial certification: execution aggregate and native audit must exist.
    assert (run/'PILOT_RESULTS.json').exists() and (run/'AUDIT.json').exists()
    protocol=json.loads((run/'runs/train/PROTOCOL.json').read_text())
    assert protocol['seeds']==[2026111801,2026111802]
    assert all(sha(p)==h for p,h in protocol['frozen'].items())
    files=sorted((run/'runs/train').glob('*.json.gz'));assert len(files)==16
    rows=[];groups={};frozen={};steps=overrides=0
    for path in files:
        summary=json.loads(path.with_suffix('').read_text())
        assert sha(path)==summary['archive_sha256']
        assert summary['completed'] and summary['terminated'] and not summary['truncated']
        assert summary['invalid_actions']==0 and summary['bc_eligible_decisions']==0
        frozen.update(summary['frozen_artifacts'])
        with gzip.open(path,'rt') as f:raw=json.load(f)
        assert len(raw['transitions'])==summary['steps'] and len(raw['batches'])==summary['steps']+1
        assert all(b['batch_id']==i for i,b in enumerate(raw['batches']))
        ending=[e for b in raw['batches'] for e in b['events'] if e['kind']==3]
        outcome=raw['episode']['terminal_outcome']
        assert outcome==summary['terminal_outcome'] and outcome['result_type']==0
        assert len(ending)==1 and ending[0]['winner']==outcome['winner']
        assert any(e['kind']==3 for e in raw['batches'][-1]['events'])
        side=int(summary['role']=='defender');won=int(outcome['winner']==side)
        assert summary['success']==bool(won)
        casualties=outcome['casualties'];initial=outcome['initial_armies']
        kills=Counter()
        for b in raw['batches']:
            for e in b['events']:
                if e['kind']==2:
                    for target in e['targets']:
                        assert target['killed']>=0
                        kills[target['defender_side']]+=target['killed']
        for s in (0,1):
            assert kills[s]==sum(casualties[str(s)].values()), 'event kills != permanent casualty total'
            assert all(0<=n<=initial[s][c] for c,n in casualties[str(s)].items())
        loser=1-outcome['winner'];winner=outcome['winner']
        assert casualties[str(loser)]==initial[loser]
        assert sum(initial[winner].values())>sum(casualties[str(winner)].values())
        episode_overrides=[]
        for t in raw['transitions']:
            graph=t['observation_before'];legal=graph['active_action_ids']
            assert legal==t['legal_actions'] and t['executed_action'] in legal
            assert t['pre_batch_id']==t['step_id'] and t['post_batch_id']==t['step_id']+1
            events=raw['batches'][t['post_batch_id']]['events']
            w=t['action_window'];start,finish=window(events,side,t['known_actor_id_before'],w['native_action_type'])
            assert (w['start'],w['finish'],w['status'])==(start,finish,'matched')
            if summary['policy']=='positive-exchange':
                teacher=t['quality']['teacher_action'];selected,facts=select(graph,teacher)
                assert selected==t['executed_action']
                assert t['quality']['overrode_teacher']==(selected!=teacher)
                assert t['quality']['eligible_for_bc'] is False and t['quality']['certified'] is False
                if selected!=teacher:
                    assert facts[selected][2]>0 and facts[selected][2]-facts[teacher][2]>1
                    episode_overrides.append(dict(step=t['step_id'],before=facts[teacher][2],after=facts[selected][2],
                        events=events[start:finish+1]))
            assert not t['demonstration_gate']['eligible_for_bc']
            steps+=1
        loss=casualties[str(side)]
        row=dict(archive=str(path),sha256=sha(path),scenario=summary['scenario'],role=summary['role'],
            seed=summary['seed'],policy=summary['policy'],won=won,main_loss=loss.get('6',0),
            total_loss=sum(loss.values()),overrides=episode_overrides)
        rows.append(row);overrides+=len(episode_overrides)
        groups.setdefault((row['scenario'],row['role'],row['seed']),{})[row['policy']]=(row,raw)
    assert len(groups)==8 and all(sha(p)==h for p,h in frozen.items())
    pairs=[]
    for key,p in groups.items():
        assert set(p)=={'teacher','positive-exchange'}
        b,br=p['teacher'];c,cr=p['positive-exchange']
        assert br['initial_observation']==cr['initial_observation']
        first_override=c['overrides'][0]['step'] if c['overrides'] else None
        cutoff=first_override if first_override is not None else min(len(br['transitions']),len(cr['transitions']))
        prefix_events_equal=br['batches'][:cutoff+1]==cr['batches'][:cutoff+1]
        prefix_actions_equal=all(br['transitions'][i]['executed_action']==cr['transitions'][i]['executed_action']
            for i in range(cutoff))
        prefix_graphs_equal=all(br['transitions'][i]['observation_before']==cr['transitions'][i]['observation_before']
            for i in range(min(cutoff+1,len(br['transitions']),len(cr['transitions']))))
        first_override_detail=None
        if first_override is not None:
            bt=br['transitions'][first_override];ct=cr['transitions'][first_override]
            first_override_detail=dict(step=first_override,
                baseline_executed=bt['executed_action'],candidate_executed=ct['executed_action'],
                candidate_teacher=ct['quality']['teacher_action'],
                baseline_facts=bt['selected_facts'],candidate_facts=ct['selected_facts'],
                baseline_events=br['batches'][bt['post_batch_id']]['events'][bt['action_window']['start']:bt['action_window']['finish']+1],
                candidate_events=cr['batches'][ct['post_batch_id']]['events'][ct['action_window']['start']:ct['action_window']['finish']+1])
        pairs.append(dict(scenario=key[0],role=key[1],seed=key[2],
            win_delta=c['won']-b['won'],main_delta=c['main_loss']-b['main_loss'],
            total_delta=c['total_loss']-b['total_loss'],overrides=len(c['overrides']),
            exact_event_prefix_before_first_override=prefix_events_equal,
            exact_action_prefix_before_first_override=prefix_actions_equal,
            exact_graph_prefix_through_first_override=prefix_graphs_equal,
            first_override=first_override_detail))
    main_delta=sum(p['main_delta'] for p in pairs);total_delta=sum(p['total_delta'] for p in pairs)
    map_deltas={s:sum(p['main_delta'] for p in pairs if p['scenario']==s) for s,_,_ in groups}
    cells={(p['scenario'],p['role']) for p in pairs if p['overrides']}
    gate=(len(cells)>=2 and all(p['win_delta']>=0 for p in pairs) and main_delta<0
          and total_delta<=0 and max(map_deltas.values())<=0)
    report=dict(passed=True,episodes=16,steps=steps,overrides=overrides,rows=rows,pairs=pairs,
        net_win_delta=sum(p['win_delta'] for p in pairs),main_casualty_delta=main_delta,
        total_casualty_delta=total_delta,map_main_deltas=map_deltas,gate_recomputed=gate,
        wins={m:sum(r['won'] for r in rows if r['policy']==m) for m in ('teacher','positive-exchange')},
        event_kills_match_terminal_permanent_totals=True,policy_core_independently_reimplemented=True,
        bc_eligible=False,independent_capability_test=False,
        limitation='Teacher fallback action is archived metadata, not independently recomputed native BattleAI; creature-specific casualties use native terminal fields. No full-world determinism claim.')
    output.write_text(json.dumps(report,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k not in ('rows','pairs')},indent=2))


if __name__=='__main__':main()
