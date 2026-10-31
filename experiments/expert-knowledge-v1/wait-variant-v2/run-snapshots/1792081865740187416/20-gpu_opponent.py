"""Serve a fixed neural opponent centrally, using the engine's dual-env API.

The battle rules are unchanged. Only the location of opponent neural inference
changes; no outcomes or teacher actions are passed to the learning policy.
"""
import threading
import traceback
import time
from multiprocessing.connection import wait
import json
from pathlib import Path


def start_opponent(main_env, connection):
    from vcmi_gym.envs.v15.vcmi_env import VcmiEnv

    def loop():
        try:
            other = VcmiEnv(opponent='OTHER_ENV', main_env=main_env,
                vcmienv_loglevel='WARN', vcmienv_logtag='fixed-opponent',
                user_timeout=90, vcmi_timeout=90, boot_timeout=90)
            # connect_as already returns the initial state. VcmiEnv.connect()
            # additionally sends ACTION_RESET, which can abort the other side's
            # just-started battle in a two-player bootstrap.
            obs = other.filter_obs(other.connector.connect_as(other.role))
            other._reset_vars(obs)
            side = 1-int(main_env.role == 'defender')
            while True:
                connection.send(dict(nodes=obs['nodes'], edges=obs['edges'],
                    active_action_ids=obs['active_action_ids'], lab_side=side))
                action = connection.recv()
                assert action in obs['active_action_ids'], 'Invalid opponent action'
                obs, _, terminated, truncated, _ = other.step(int(action))
                if terminated or truncated:
                    obs, _ = other.reset()
        except BaseException:
            try: connection.send(dict(error=traceback.format_exc()))
            except (OSError, BrokenPipeError, EOFError): pass

    thread = threading.Thread(target=loop, name='fixed-opponent', daemon=True)
    thread.start()
    obs=main_env.filter_obs(main_env.connector.connect_as(main_env.role))
    main_env._reset_vars(obs)
    return thread


class BatchedOpponent:
    def __init__(self, pair, graph, device='cuda'):
        self.pair, self.graph, self.device = pair, graph, device
        self.requests = self.batches = 0
        self.seconds = 0.0
        self.parameter_versions=tuple(p._version for p in pair.parameters())

    def assert_unchanged(self):
        assert self.parameter_versions==tuple(p._version for p in self.pair.parameters()),'Fixed opponent was modified'

    def __call__(self, observations):
        import torch
        tick = time.perf_counter()
        with torch.inference_mode():
            samples = self.pair.encode_features(observations)
            logits, _ = self.pair(*self.graph.head_collate(samples, self.device))
            indices = logits.argmax(-1).tolist()
        self.requests += len(observations); self.batches += 1
        self.seconds += time.perf_counter()-tick
        return [int(s[2][a]) for s,a in zip(samples,indices)]


def configure_training(args,graph,learner):
    """Enable a fixed GPU peer only after contracts and full-capacity benchmarks."""
    r=Path(__file__).parent
    decision=r/'central-opponent-throughput.json'
    requested=list(args.opponents)
    automatic=False
    if decision.exists():
        choice=json.loads(decision.read_text())
        automatic=choice.get('completed') and choice.get('use_central_gpu') and Path(args.output).name.startswith(('v5-diverse-','v5-full-graph-capacity'))
    if automatic:args.opponents=['MMAI_GPU' if p=='MMAI_MODEL' else p for p in args.opponents]
    if 'MMAI_GPU' not in args.opponents:return None
    if getattr(args,'deterministic_cuda',False):
        deterministic=json.loads((r/'central-opponent-cuda-deterministic-contract.json').read_text())
        assert deterministic['passed'] and deterministic['observation_hash_version']==2
    for name in ['central-opponent-contract.json','central-opponent-cuda-contract.json']:
        contract=json.loads((r/name).read_text())
        assert contract['passed'] and contract.get('observation_hash_version')==2,'Complete graph peer contract missing'
    peer=graph.RecoveredPair('/root/heroes3-ai-lab/models/recovered-v15/initial-pair.pt').cuda().eval()
    peer.requires_grad_(False)
    assert not ({p.data_ptr() for p in peer.parameters()} & {p.data_ptr() for p in learner.parameters()})
    args.requested_opponents=requested
    args.fixed_opponent_inference='central-cuda'
    args.fixed_opponent_checkpoint='/root/heroes3-ai-lab/models/recovered-v15/initial-pair.pt'
    return BatchedOpponent(peer,graph,'cuda')


class OpponentVector:
    """Same synchronous learner API, servicing opponent requests while waiting."""
    def __init__(self, configs, executable, opponent):
        import multiprocessing as mp
        from pathlib import Path
        from vector_env import environment_worker
        mp.set_executable(executable)
        context = mp.get_context('spawn')
        self.processes, self.connections, self.opponents = [], [], []
        self.opponent = opponent
        try:
            for original in configs:
                mem = {k:int(v.strip().split()[0]) for k,v in
                    (line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines())}
                assert mem['MemAvailable'] > 2560*1024, 'Worker boot needs 2.5 GiB reserve'
                assert mem['SwapTotal']-mem['SwapFree'] < 256*1024
                parent, child = context.Pipe()
                config = dict(original)
                if config.get('opponent') == 'MMAI_GPU':
                    op_parent, op_child = context.Pipe()
                    config['opponent_connection'] = op_child
                else:
                    op_parent = op_child = None
                process = context.Process(target=environment_worker,args=(child,config))
                process.start(); child.close()
                if op_child: op_child.close()
                self.processes.append(process); self.connections.append(parent)
                self.opponents.append(op_parent)
                # Serial boot still services the opposing player, which can act first.
                state = self._collect([len(self.connections)-1])[0]
                if not hasattr(self,'states'): self.states=[]
                self.states.append(state)
        except BaseException:
            self.abort(); raise

    def _collect(self, indices):
        pending = {self.connections[i]:i for i in indices}
        states = {}; deadline = time.monotonic()+90
        opponent_pipes = [c for c in self.opponents if c is not None]
        while pending:
            remaining = deadline-time.monotonic()
            if remaining <= 0: raise TimeoutError('Dual-env response timeout')
            ready = wait([*pending,*opponent_pipes],timeout=remaining)
            observations, pipes = [], []
            for connection in ready:
                response = connection.recv()
                if 'error' in response: raise RuntimeError(response['error'])
                if connection in pending:
                    states[pending.pop(connection)] = response
                else:
                    observations.append(response); pipes.append(connection)
            if observations:
                for connection,action in zip(pipes,self.opponent(observations)):
                    connection.send(action)
        return [states[i] for i in indices]

    def step(self,actions):
        assert len(actions)==len(self.connections)
        for connection,action in zip(self.connections,actions):connection.send(('step',int(action)))
        self.states=self._collect(list(range(len(self.connections))))
        return self.states

    def close(self):
        for connection in self.connections:connection.send(('close',None))
        # Closing native VCMI terminates its process, including the daemon player.
        for i,connection in enumerate(self.connections):
            assert connection.poll(30) and connection.recv()['closing']
            self.processes[i].join(timeout=30)
            assert self.processes[i].exitcode==0
        for c in [*self.connections,*self.opponents]:
            if c is not None:c.close()

    def abort(self):
        for p in self.processes:
            if p.is_alive():p.terminate()
        for p in self.processes:
            p.join(timeout=5)
            if p.is_alive():p.kill();p.join()
        for c in [*self.connections,*self.opponents]:
            if c is not None:c.close()
