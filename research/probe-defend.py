import importlib.util
import json
import os
from pathlib import Path
from vcmi_gym.envs.v15.vcmi_env import Action, ACTION_TYPES

os.environ['LAB_BATTLEAI_TEACHER'] = '1'
spec = importlib.util.spec_from_file_location('lab_env', Path(__file__).with_name('lab-env.py'))
lab = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lab)
env = lab.make_env('lab/balanced-00.vmap', 2026101407, 'attacker')
results = []
for episode in range(3):
    obs, _ = env.reset()
    ids = obs['active_action_ids']
    choices = [int(i) for i in ids if Action.decode_one(obs['nodes']['Action'][i]).ACTION_TYPE == ACTION_TYPES['DEFEND']]
    assert choices, 'DEFEND must be an exact legal action'
    obs, reward, term, trunc, info = env.step(choices[0])
    steps = 1
    while not (term or trunc):
        action = int(obs['teacher_action_id'])
        assert action in obs['active_action_ids']
        obs, _, term, trunc, info = env.step(action)
        steps += 1
    assert term and not trunc and obs['terminal_outcome']['result_type'] == 0
    results.append(dict(episode=episode, forced_defend_action=choices[0], steps=steps,
                        winner=obs['terminal_outcome']['winner']))
Path('/mnt/g/Heroes3-AI-Lab/research/defend-protocol-probe.json').write_text(json.dumps(dict(passed=True,
    scope='Protocol exercise: one forced legal DEFEND then real BattleAI actions; not teacher supervision', episodes=results), indent=2))
print('DEFEND execution and normal battle termination passed', flush=True)
env.close()
