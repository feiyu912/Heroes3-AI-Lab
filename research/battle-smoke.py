import argparse
import hashlib
import json
from pathlib import Path
import time
import uuid

import numpy as np
from vcmi_gym.envs.v15.vcmi_env import VcmiEnv, Action, Player, Global, ACTION_TYPES


def digest_observation(obs):
    digest = hashlib.sha256()
    for name, array in sorted(obs['nodes'].items()):
        digest.update(name.encode())
        digest.update(np.asarray(array).tobytes())
    for name, values in sorted(obs['edges'].items()):
        digest.update(str(name).encode())
        for field, array in sorted(values.items()):
            digest.update(field.encode())
            digest.update(np.asarray(array).tobytes())
    digest.update(np.asarray(obs['active_action_ids']).tobytes())
    return digest.hexdigest()


def choose_action(obs):
    ids = sorted(int(i) for i in obs['active_action_ids'])
    assert ids, 'No active actions in a nonterminal state'
    priority = {ACTION_TYPES[name]: value for value, name in
                enumerate(['SHOOT', 'AMOVE', 'MOVE', 'DEFEND', 'WAIT'])}
    decoded = Action.decode_many(obs['nodes']['Action'][ids])
    return min(zip(ids, decoded), key=lambda item: (priority[item[1].ACTION_TYPE], item[0]))[0]


def player_values(obs):
    return {int(p.BATTLE_SIDE): int(p.ARMY_VALUE_NOW_REL0)
            for p in Player.decode_many(obs['nodes']['Player'])}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--role', choices=['attacker', 'defender'], default='attacker')
    parser.add_argument('--seed', type=int, default=20261013)
    parser.add_argument('--episodes', type=int, default=2)
    parser.add_argument('--output', required=True)
    parser.add_argument('--run-id', default=None)
    args = parser.parse_args()
    start = time.monotonic()
    env = VcmiEnv(mapname='lab/smoke.vmap', seed=args.seed, role=args.role,
                  opponent='BattleAI', max_steps=200, render_mode='ansi',
                  random_heroes=0, random_obstacles=0, town_chance=0,
                  warmachine_chance=0, random_armies=False, mana_min=0, mana_max=0,
                  user_timeout=30, vcmi_timeout=30, boot_timeout=60,
                  vcmi_loglevel_global='warn', vcmi_loglevel_ai='error')
    boot_seconds = time.monotonic() - start
    results = []
    try:
        for episode in range(args.episodes):
            obs, reset_info = env.reset()
            initial_values = player_values(obs)
            trace = [digest_observation(obs)]
            actions = []
            rewards = []
            term = trunc = False
            while not (term or trunc):
                action = choose_action(obs)
                assert action in obs['active_action_ids']
                obs, reward, term, trunc, info = env.step(action)
                assert np.isfinite(reward)
                assert all(np.all(np.isfinite(v)) for v in obs['nodes'].values())
                actions.append(action)
                rewards.append(float(reward))
                trace.append(digest_observation(obs))
            assert term and not trunc, 'Smoke battle did not reach a real terminal state'
            final_values = player_values(obs)
            winner = int(Global.decode_one(obs['nodes']['Global'][0]).BATTLE_WINNER)
            outcome = obs['terminal_outcome']
            assert outcome is not None, 'Missing authoritative BattleResult'
            assert outcome['winner'] == winner
            assert outcome['result_type'] == 0, 'Expected normal combat, not retreat/reset'
            initial_counts = {side: sum(army.values()) for side, army in enumerate(outcome['initial_armies'])}
            assert initial_counts == {0: 20, 1: 10}
            casualties = {side: sum(outcome['casualties'][side].values()) for side in initial_counts}
            remaining = {side: initial_counts[side] - casualties[side] for side in initial_counts}
            assert all(0 <= casualties[s] <= initial_counts[s] for s in initial_counts)
            assert remaining[1 - winner] == 0, 'Losing army must be fully lost in this normal no-magic fixture'
            result = dict(episode=episode, steps=len(actions), winner=winner,
                          terminated=bool(term), truncated=bool(trunc),
                          initial_value_permille=initial_values, final_value_permille=final_values,
                          loss_value_permille={side: initial_values[side] - final_values[side]
                                               for side in initial_values},
                          terminal_info=info, actions=actions,
                          server_casualties=outcome['casualties'],
                          permanent_loss_counts=casualties,
                          permanent_remaining_counts=remaining,
                          reward_sum=sum(rewards), initial_observation_sha256=trace[0],
                          trajectory_sha256=hashlib.sha256(''.join(trace).encode()).hexdigest())
            results.append(result)
            print(json.dumps(result), flush=True)
        output = dict(run_id=args.run_id or str(uuid.uuid4()), completed=True,
                      seed=args.seed, role=args.role, opponent='BattleAI', map='lab/smoke.vmap',
                      schema=15, boot_seconds=boot_seconds, elapsed_seconds=time.monotonic()-start,
                      policy='deterministic attack-priority legal-action diagnostic',
                      note='Permanent loss counts come from server BattleResult for this normal no-magic fixture; schema army values retained for comparison.',
                      episodes=results)
        Path(args.output).write_text(json.dumps(output, indent=2))
    finally:
        print('Beginning environment shutdown', flush=True)
        env.close()
        print('Environment close returned', flush=True)


if __name__ == '__main__':
    main()
