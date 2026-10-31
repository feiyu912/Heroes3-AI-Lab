import gzip
import json
from pathlib import Path
import numpy as np
from vcmi_gym.envs.v15.vcmi_env import Unit, Hex
from vcmi_gym.envs.v15.pyconnector import EDGE_TYPES

here=Path(__file__).resolve().parent
with gzip.open(here/'runs/smoke/bait-attacker.json.gz','rt') as f:
    data=json.load(f)
obs=data['initial_observation']
u=Unit.decode_one(np.asarray(obs['nodes']['Unit'][0],np.float32))
h=Hex.decode_one(np.asarray(obs['nodes']['Hex'][0],np.float32))
print('UNIT',u)
print('HEX',h)
print('RELATIONS',[e['relation'] for e in obs['edges']])
for key in [('Unit','ActsBefore','Unit'),('Unit','MeleeDmg','Unit'),('Unit','BecomesMeleeThreatAfter','Action')]:
    print(key,EDGE_TYPES[key])
