"""Shared fixed-rule v15 environment settings for lab experiments."""
from vcmi_gym.envs.v15.vcmi_env import VcmiEnv


def make_env(mapname, seed, role, opponent='BattleAI', max_steps=400, opponent_model=None, timeout=60):
    return VcmiEnv(mapname=mapname, seed=seed, role=role, opponent=opponent,
                   opponent_model=opponent_model, max_steps=max_steps, render_mode='ansi', random_heroes=0,
                   random_obstacles=0, town_chance=0, warmachine_chance=0,
                   random_armies=False, mana_min=0, mana_max=0,
                   user_timeout=timeout, vcmi_timeout=timeout, boot_timeout=timeout,
                   vcmi_loglevel_global='error', vcmi_loglevel_ai='error')
