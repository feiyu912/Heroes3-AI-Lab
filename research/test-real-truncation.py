import json
from pathlib import Path
import numpy as np
from vector_env import VectorEnv
from masked_ppo import gae


def main():
    env = VectorEnv([dict(map='lab/balanced-00.vmap', seed=2026101421, role='attacker',
                          max_steps=1, worker_root='/root/heroes3-ai-lab/workers/truncation-contract')])
    try:
        state = env.states[0]['features']
        transition = env.step([int(state[3][0])])[0]
        assert transition['truncated'] and not transition['terminated']
        assert transition['reward'] == 0 and transition['outcome'] is None
        final = transition['final_features']
        reset = transition['features']
        assert final is not None
        final_value = float(final[1].sum())
        reset_value = float(reset[1].sum())
        assert abs(final_value - reset_value) > 1e-5, 'Fixture must distinguish final and reset states'
        adv, returns = gae([[0]], [[0.5]], [[final_value]], [[False]], [[True]], gamma=0.99)
        np.testing.assert_allclose(returns[0, 0], 0.99 * final_value, rtol=1e-5)
        output = dict(passed=True, terminated=False, truncated=True, reward=0,
                      final_state_value=final_value, reset_state_value=reset_value,
                      bootstrap_return=float(returns[0, 0]),
                      scope='Real one-step VCMI time-limit transition preserves final state separately from reset state')
        Path('/mnt/g/Heroes3-AI-Lab/research/real-truncation-contract.json').write_text(json.dumps(output, indent=2))
        print('Real truncation final-state contract passed', flush=True)
        env.close()
    except Exception:
        env.abort()
        raise


if __name__ == '__main__':
    main()
