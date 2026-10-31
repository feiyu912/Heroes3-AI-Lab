#!/usr/bin/env python3
"""Dump per-decision Unit node flags with creature-identifying attributes."""
import gzip
import json
import sys
from pathlib import Path
import numpy as np
from vcmi_gym.envs.v15.vcmi_env import Unit

path = Path(sys.argv[1])
with gzip.open(path, 'rt') as f:
    data = json.load(f)

for di, d in enumerate(data['decisions'][:6]):
    arr = np.asarray(d['observation']['nodes']['Unit'], dtype=np.float32)
    print(f'--- decision {di} ({arr.shape[0]} units) ---')
    for i in range(arr.shape[0]):
        u = Unit.decode_one(arr[i])
        print(f'  node {i:2d}: value={u.VALUE_REL:7.1f} enemy={int(u.IS_ENEMY)} '
              f'breath={int(u.HAS_TWO_HEX_ATTACK_BREATH)} cloud={int(u.HAS_DEATH_CLOUD)} '
              f'nonliving={int(u.HAS_NON_LIVING)} warmachine={int(u.IS_WAR_MACHINE)} '
              f'flying={int(u.HAS_FLYING)}')

# also the packed unit composition of the scenario
sc = data['episode']['scenario']
print('scenario:', sc)
