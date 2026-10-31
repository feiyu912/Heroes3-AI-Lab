"""Execute a source-backed WAIT/control reconstruction in the pinned real engine.

Lab-generated state, not a recovered human replay. The existing OTHER_ENV pipe
transports a CPU script despite its historical internal MMAI_GPU config label.
"""
import argparse
from collections import deque
import copy
import fcntl
import gzip
import hashlib
import json
import os
from pathlib import Path
import time
import zipfile
import numpy as np
from lab_io import atomic_json
from evaluation_provenance import digest
from battle_outcome_audit import audit
from gpu_opponent import OpponentVector
from vcmi_gym.envs.v15.vcmi_env import Action, Global, Unit, ACTION_TYPES

HERE = Path(__file__).resolve().parent
ROOT = Path('/root/heroes3-ai-lab')


def generate():
    cases = []
    for index in range(8):
        counts = (10+index, 80+index*7)
        for role in ['attacker','defender']:
            fast = [dict(type='core:dreadKnight',amount=counts[0])] + [{} for _ in range(6)]
            slow = [dict(type='core:walkingDead',amount=counts[1])] + [{} for _ in range(6)]
            armies = [fast,slow] if role=='attacker' else [slow,fast]
            name = f'lab/hallas-wait-{index}-{role}.vmap'
            path = ROOT/'data/vcmi/Maps'/name
            with zipfile.ZipFile(ROOT/'src/gym/maps/gym/ml-mini.vmap') as source, zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as target:
                for entry in source.namelist():
                    content = source.read(entry)
                    if entry=='objects.json':
                        objects = json.loads(content)
                        for obj in objects.values():
                            if obj.get('type')=='hero':
                                side = int(obj['options']['owner']!='red')
                                obj['options'].update(experience=0,primarySkills=dict(attack=0,defence=0,knowledge=0,spellpower=0),
                                    secondarySkills=[],spellBook=['preset'],army=armies[side])
                        content = json.dumps(objects).encode()
                    target.writestr(entry,content)
            cases.append(dict(id=f'hallas-wait-{index}-{role}', map=name, role=role, armies=armies,
                index=index, split='train' if index<4 else 'development' if index<6 else 'test',
                source_case='hallas-2001-wait-cross-round-action-window',sha256=digest(path),
                reconstruction='Lab counts/slots/heroes/seed; not extracted historical state',
                morale_control='Both stacks undead; no positive-morale extra turns expected, verify actual order'))
    atomic_json(HERE/'source-wait-scenarios.json',cases)
    return cases


def active(obs):
    units = Unit.decode_many(obs['nodes']['Unit'])
    actors = [index for index,unit in enumerate(units) if unit.IS_ACTIVE]
    assert len(actors)==1 and not units[actors[0]].IS_ENEMY
    return actors[0]


def greedy(obs):
    """Legal melee if possible; otherwise advance along graph hex adjacency."""
    legal = [int(value) for value in obs['active_action_ids']]
    types = {action:int(Action.decode_one(obs['nodes']['Action'][action]).ACTION_TYPE) for action in legal}
    attacks = [action for action in legal if types[action]==ACTION_TYPES['AMOVE']]
    if attacks:
        return min(attacks)
    units = Unit.decode_many(obs['nodes']['Unit'])
    enemy_hexes = [int(hex_) for unit,hex_ in obs['edges'][('Unit','Occupies','Hex')]['index'].T if units[int(unit)].IS_ENEMY]
    adjacent = {}
    for left,right in obs['edges'][('Hex','Adjacent','Hex')]['index'].T:
        adjacent.setdefault(int(left),[]).append(int(right))
    distances = {hex_:0 for hex_ in enemy_hexes}
    queue = deque(enemy_hexes)
    while queue:
        left=queue.popleft()
        for right in adjacent.get(left,[]):
            if right not in distances:
                distances[right]=distances[left]+1
                queue.append(right)
    ends = {}
    for action,hex_ in obs['edges'][('Action','EndsAt','Hex')]['index'].T:
        ends.setdefault(int(action),[]).append(int(hex_))
    moves = [action for action in legal if types[action]==ACTION_TYPES['MOVE']]
    if moves:
        return min(moves,key=lambda action:(min(distances.get(hex_,999) for hex_ in ends[action]),action))
    return next(action for action in legal if types[action]==ACTION_TYPES['DEFEND'])


class Opponent:
    def __init__(self):
        self.calls=[]
    def __call__(self, observations):
        actions=[]
        for obs in observations:
            action=greedy(obs)
            self.calls.append(dict(round=Global.decode_one(obs['nodes']['Global'][0]).BATTLE_ROUND,
                side=int(obs['lab_side']), action=action))
            actions.append(action)
        return actions


def serializable(obs):
    return dict(nodes={key:array.tolist() for key,array in obs['nodes'].items()},
        edges=[dict(relation=list(key),index=edge['index'].tolist(),attrs=edge['attrs'].tolist()) for key,edge in obs['edges'].items()],
        active_action_ids=[int(value) for value in obs['active_action_ids']])


def episode(case, wait):
    policy='wait-expert' if wait else 'no-wait-control'
    output=HERE/'wait-runs'/f'{case["id"]}-{policy}.json'
    output.parent.mkdir(parents=True,exist_ok=True)
    if output.exists():
        previous=json.loads(output.read_text())
        assert previous.get('completed'), previous
        return previous
    with Path('/root/heroes3-ai-lab/evaluations/.pool-lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        opponent=Opponent()
        source=HERE/'source_wait_case.json'
        hashes={str(path):digest(path) for path in [source,Path(__file__),ROOT/'data/vcmi/Maps'/case['map'],
            ROOT/'src/gym/vcmi/rel/bin/libmlclient.so',ROOT/'src/gym/vcmi/rel/bin/libvcmi.so']}
        config=dict(map=case['map'],role=case['role'],opponent='MMAI_GPU',
            seed=2026103001+case['index'],feature_version='upstream-graph-v15',step_cost=0,
            worker_root=f'/root/heroes3-ai-lab/workers/hallas-wait-{case["id"]}-{policy}',max_steps=200)
        vector=OpponentVector([config],'/root/heroes3-ai-lab/venv/bin/python',opponent)
        rows=[]
        try:
            for step in range(200):
                obs=vector.states[0]['features']
                legal=[int(value) for value in obs['active_action_ids']]
                chosen=greedy(obs)
                if wait and step==0:
                    chosen=next(action for action in legal if Action.decode_one(obs['nodes']['Action'][action]).ACTION_TYPE==ACTION_TYPES['WAIT'])
                assert chosen in legal
                row=dict(step=step,round=Global.decode_one(obs['nodes']['Global'][0]).BATTLE_ROUND,
                    action=chosen,action_type=int(Action.decode_one(obs['nodes']['Action'][chosen]).ACTION_TYPE),
                    opposing_actions_before=len(opponent.calls),observation=serializable(obs),
                    actor_side=int(case['role']=='defender'),tactic_id=case['source_case'],
                    battle_id=output.stem,scenario_seed=config['seed'],expert_version='hallas-wait-rule-v1')
                rows.append(row)
                transition=vector.step([chosen])[0]
                if transition['terminated'] or transition['truncated']:
                    break
            outcome=json.loads(json.dumps(transition['outcome'])) if transition.get('outcome') else None
            term=bool(transition['terminated']);trunc=bool(transition['truncated'])
            side=int(case['role']=='defender')
            normal=bool(term and not trunc and outcome and outcome['result_type']==0)
            window=bool(wait and len(rows)>=3 and rows[0]['action_type']==ACTION_TYPES['WAIT']
                and rows[1]['round']==rows[0]['round'] and rows[2]['round']==rows[1]['round']+1
                and rows[1]['opposing_actions_before']==rows[2]['opposing_actions_before']
                and rows[1]['opposing_actions_before']>rows[0]['opposing_actions_before'])
            report=dict(completed=True,case=case,role=case['role'],policy=policy,terminated=term,truncated=trunc,
                terminal_outcome=outcome,success=bool(normal and outcome['winner']==side),invalid_actions=0,
                cross_round_window_verified=window,permanent_units_lost=sum(outcome['casualties'][str(side)].values()) if normal else None,
                decisions=rows,opponent_actions=opponent.calls,source_hashes=hashes,
                inference_device='CPU scripted rules over existing dual-env transport; no neural GPU opponent',
                source_attribution='Reconstruction of Hallas waiting principle; lab-generated states and actions, not human replay')
            report['raw_outcome_audit']=audit([report])
            assert all(digest(path)==value for path,value in hashes.items())
            atomic_json(output,report)
            return report
        finally:
            vector.close()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--split',choices=['train','development','test'],default='train')
    args=parser.parse_args()
    cases=json.loads((HERE/'source-wait-scenarios.json').read_text()) if (HERE/'source-wait-scenarios.json').exists() else generate()
    results=[]
    for case in cases:
        if case['split']!=args.split:
            continue
        pair=[episode(case,wait) for wait in [True,False]]
        results.append(dict(case=case['id'],split=case['split'],wait_success=pair[0]['success'],control_success=pair[1]['success'],
            window_verified=pair[0]['cross_round_window_verified'],wait_loss=pair[0]['permanent_units_lost'],
            control_loss=pair[1]['permanent_units_lost'],
            benefit_verified=bool(pair[0]['cross_round_window_verified'] and pair[0]['success']
                and (not pair[1]['success'] or pair[0]['permanent_units_lost']<pair[1]['permanent_units_lost']))))
        atomic_json(HERE/f'wait-{args.split}-comparison.json',dict(results=results,source_claim_verified=all(row['window_verified'] for row in results),
            benefit_cases=sum(row['benefit_verified'] for row in results),final_human_replay_obtained=False))
        print(results[-1],flush=True)


if __name__=='__main__':
    main()
