"""One isolated VCMI instance per process; parent owns batched policy inference."""
import copy
import importlib.util
import multiprocessing as mp
import os
from pathlib import Path
import subprocess
import sys
import traceback


def environment_worker(connection, config):
    worker_root = config['worker_root']
    try:
        subprocess.run([sys.executable, '/mnt/g/Heroes3-AI-Lab/research/prepare-worker.py', worker_root],
                       check=True, stdout=subprocess.DEVNULL)
        os.environ['XDG_DATA_HOME'] = worker_root + '/data'
        os.environ['LAB_BATTLEAI_TEACHER'] = '0'
        os.environ['LAB_RANDOM_POLICY_SEED'] = str(config['seed'] + 100000)
        from battle_features import features, linked_features
        if config.get('feature_version') == 'lab-candidates-v2-linked':
            features = linked_features
        elif config.get('feature_version') == 'upstream-graph-v15':
            def features(obs):
                return dict(nodes=obs['nodes'],edges=obs['edges'],active_action_ids=obs['active_action_ids'],
                            lab_side=int(config['role']=='defender'))
        spec = importlib.util.spec_from_file_location('lab_env', Path('/mnt/g/Heroes3-AI-Lab/research/lab-env.py'))
        lab = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(lab)
        if config.get('initial_reset_once') and config.get('opponent')!='MMAI_GPU':
            # Native VcmiEnv.__init__ resets immediately after connect. For the
            # bridge comparison, start both modes from the same first battle:
            # initialize Python bookkeeping from connect's initial observation
            # instead of sending an extra engine ACTION_RESET.
            from vcmi_gym.envs.v15.pyconnector import PyConnector
            original_connect=PyConnector.connect_as;original_reset=PyConnector.reset
            def remember_initial(connector,role):
                observation=original_connect(connector,role)
                connector._lab_initial_observation=observation
                return observation
            def use_initial_once(connector):
                if '_lab_initial_observation' in connector.__dict__:
                    return connector.__dict__.pop('_lab_initial_observation')
                return original_reset(connector)
            PyConnector.connect_as=remember_initial;PyConnector.reset=use_initial_once
        env = lab.make_env(config['map'], config['seed'], config['role'], opponent='OTHER_ENV' if config.get('opponent')=='MMAI_GPU' else config.get('opponent', 'BattleAI'),
                           max_steps=config.get('max_steps', 400), opponent_model=config.get('opponent_model'),timeout=config.get('timeout',600))
        if config.get('opponent')=='MMAI_GPU':
            from gpu_opponent import start_opponent
            start_opponent(env,config['opponent_connection'])
        if config.get('opponent')=='MMAI_GPU' or config.get('initial_reset_once'):
            obs=env.obs
        else:
            obs, _ = env.reset()
        episode_steps = 0
        connection.send(dict(features=features(obs), pid=os.getpid(), torch_imported='torch' in sys.modules))
        while True:
            command, action = connection.recv()
            if command == 'close':
                connection.send(dict(closing=True))
                if config.get('opponent')=='MMAI_GPU':
                    # Two player threads may be blocked inside native reset.
                    # The isolated simulator process owns no training weights;
                    # exit at the parent's acknowledged boundary, avoiding
                    # racing two native shutdown paths against each other.
                    os._exit(0)
                env.close()
                return
            if command != 'step':
                raise ValueError(command)
            if action not in obs['active_action_ids']:
                raise ValueError(f'Illegal requested action {action}')
            obs, _, term, trunc, info = env.step(action)
            episode_steps += 1
            # v15 accepts max_steps but only checks its round limit.
            step_limit = not term and episode_steps >= config.get('max_steps', 400)
            if step_limit:
                trunc = True
            native_step_return=copy.deepcopy(dict(obs=obs,reward=_,terminated=bool(term),truncated=bool(trunc),info=info))
            outcome = obs.get('terminal_outcome') if term else None
            if term and (not outcome or outcome['result_type'] != 0):
                raise RuntimeError(f'Unexpected battle termination: {outcome}')
            reward = 0.0
            if term:
                reward = 1.0 if outcome['winner'] == int(config['role'] == 'defender') else -1.0
                shaping = config.get('loss_shaping', 0.0)
                if shaping:
                    side = int(config['role'] == 'defender')
                    ratios = [sum(outcome['casualties'][s].values()) / max(1, sum(outcome['initial_armies'][s].values())) for s in [0, 1]]
                    reward += shaping * (ratios[1-side] - ratios[side])
            reward -= config.get('step_cost', 0.0)
            final_features = features(obs) if trunc and not term else None
            if term or trunc:
                obs, _ = env.reset()
                episode_steps = 0
            connection.send(dict(features=features(obs), reward=reward, terminated=bool(term),
                                 truncated=bool(trunc), final_features=final_features,
                                 truncation_reason=('step_limit' if step_limit else 'engine_round_limit') if trunc and not term else None,
                                 outcome=outcome,native_step_return=native_step_return))
    except Exception:
        connection.send(dict(error=traceback.format_exc()))
        raise


class VectorEnv:
    def __init__(self, configs, executable=None):
        if executable:
            mp.set_executable(executable)
        context = mp.get_context('spawn')
        self.processes, self.connections = [], []
        staged = os.environ.get('LAB_STAGED_BOOT') == '1'
        self.states = []
        try:
            for config in configs:
                if staged:
                    mem = {k: int(v.strip().split()[0]) for k,v in
                           (line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines())}
                    assert mem['MemAvailable'] > 2560 * 1024, 'Staged boot stopped: less than 2.5 GiB available before next worker'
                    assert mem['SwapTotal']-mem['SwapFree'] < 256 * 1024, 'Staged boot stopped: swapping detected'
                parent, child = context.Pipe()
                process = context.Process(target=environment_worker, args=(child, config))
                process.start()
                child.close()
                self.processes.append(process)
                self.connections.append(parent)
                if staged:
                    self.states.append(self._receive(parent))
            if not staged:
                self.states = [self._receive(c) for c in self.connections]
        except Exception:
            self.abort()
            raise

    @staticmethod
    def _receive(connection):
        if not connection.poll(90):
            raise TimeoutError('Environment response timeout')
        response = connection.recv()
        if 'error' in response:
            raise RuntimeError(response['error'])
        return response

    def step(self, actions):
        assert len(actions) == len(self.connections)
        for connection, action in zip(self.connections, actions):
            connection.send(('step', int(action)))
        self.states = [self._receive(c) for c in self.connections]
        return self.states

    def close(self):
        for c in self.connections:
            c.send(('close', None))
        for c in self.connections:
            assert self._receive(c)['closing']
        for p in self.processes:
            p.join(timeout=30)
            assert p.exitcode == 0, f'Worker exit code {p.exitcode}'
        for c in self.connections:
            c.close()

    def abort(self):
        for p in self.processes:
            if p.is_alive():
                p.terminate()
        for p in self.processes:
            p.join(timeout=5)
            if p.is_alive():
                p.kill()
                p.join()
        for c in self.connections:
            c.close()
