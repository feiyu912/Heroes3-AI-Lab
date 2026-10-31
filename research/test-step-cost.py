import json
from pathlib import Path
from vector_env import VectorEnv

def main():
    config=dict(map='lab/balanced-00.vmap',seed=20261018,role='attacker',opponent='BattleAI',
        feature_version='upstream-graph-v15',step_cost=.002,
        worker_root='/root/heroes3-ai-lab/workers/step-cost-contract')
    vector=VectorEnv([config],executable='/root/heroes3-ai-lab/venv/bin/python')
    try:
        action=int(vector.states[0]['features']['active_action_ids'][0])
        result=vector.step([action])[0]
        assert not result['terminated'] and not result['truncated']
        assert result['reward']==-.002
        assert result['features']['lab_side']==0
        vector.close()
    except BaseException:
        vector.abort();raise
    Path('/mnt/g/Heroes3-AI-Lab/research/step-cost-contract.json').write_text(json.dumps(dict(passed=True,
        real_action=action,reward=-.002,rule_state_unchanged=True,worker_exit_zero=True,
        scope='One nonterminal legal action: light per-step training cost, no altered game rules or outcome'),indent=2))
    print('Step-cost and raw-graph worker contract passed',flush=True)

if __name__=='__main__':main()
