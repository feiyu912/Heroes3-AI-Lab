"""Recompute evidence from existing archives; never launches a game or learner."""
import gzip
import hashlib
import json
from pathlib import Path
import sys
import numpy as np

HERE = Path(__file__).resolve().parent
OLD = HERE.parent / 'human-tactics-events-v3'
sys.path.insert(0, str(OLD))
from visible_exchange import choose, decide


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def local(path):
    value = str(path).replace('\\', '/')
    if value.startswith('/mnt/g/'):
        # On WSL this is already absolute; on Windows translate only the shared drive.
        return Path(value) if sys.platform != 'win32' else Path('G:/' + value[len('/mnt/g/'):])
    return Path(value)


def unpack(row):
    return dict(nodes={k: np.asarray(v, dtype=np.float32) for k, v in row['nodes'].items()},
                edges={tuple(e['relation']):dict(index=np.asarray(e['index'], dtype=np.int64),
                                               attrs=np.asarray(e['attrs'], dtype=np.float32))
                       for e in row['edges']},
                active_action_ids=np.asarray(row['active_action_ids'], dtype=np.int64))


def main():
    delivery = json.loads((OLD / 'DELIVERY_AUDIT.json').read_text())
    rows = []
    replay = []
    pairs = {}
    for registered in delivery['rows']:
        summary_path = local(registered['path'])
        assert sha(summary_path) == registered['summary_sha256']
        summary = json.loads(summary_path.read_text())
        archive = local(summary['archive'])
        assert sha(archive) == summary['archive_sha256'] == registered['archive_sha256']
        with gzip.open(archive, 'rt') as f:
            raw = json.load(f)
        ts = raw['transitions']
        assert len(ts) == summary['steps'] and len(raw['batches']) == len(ts) + 1
        assert summary['terminated'] and not summary['truncated'] and summary['invalid_actions'] == 0
        ends = [e for e in raw['batches'][-1]['events'] if e['kind'] == 3]
        assert len(ends) == 1 and ends[0]['winner'] == summary['terminal_outcome']['winner']
        assert all(t['executed_action'] in t['legal_actions'] and t['action_window']['status'] == 'matched'
                   and not t['demonstration_gate']['eligible_for_bc'] for t in ts)
        rows.append(dict(path=str(summary_path), archive_sha256=sha(archive), steps=len(ts)))
        # Use the two used training fixtures only. Do not inspect locked dev/test.
        if summary_path.parent.parent.parent.name in ('curriculum-v1','curriculum-v2','curriculum-v3'):
            version = summary_path.parent.parent.parent.name
            key = (version, summary['scenario'], summary['role'], summary['seed'])
            side = str(int(summary['role'] == 'defender'))
            pairs.setdefault(key,{})[summary['policy']] = dict(
                main_loss=summary['terminal_outcome']['casualties'][side].get('6',0),
                win=int(summary['success']))
        if 'curriculum-v3' in str(summary_path) and summary['policy'] == 'teacher':
            for t in ts:
                obs = unpack(t['observation_before'])
                obs['teacher_action_id'] = t['executed_action']
                action, detail = choose(obs)
                changed = dict(obs, seed=123, battle_events=[{'forbidden':'ignored'}],
                               terminal_outcome={'winner':999}, quality='withdrawn')
                assert choose(changed) == (action, detail)
                assert action in t['legal_actions']
                replay.append(dict(file=str(summary_path), step=t['step_id'], action=action, **detail))
    metrics = {}
    for version in ('curriculum-v1','curriculum-v2','curriculum-v3'):
        ps = [p for k,p in pairs.items() if k[0] == version]
        assert len(ps) == 8 and all(set(p) == {'teacher','wait-bait'} for p in ps)
        metrics[version] = dict(pairs=len(ps), mean_main_loss_delta=sum(
            p['wait-bait']['main_loss']-p['teacher']['main_loss'] for p in ps)/len(ps),
            net_wins=sum(p['wait-bait']['win']-p['teacher']['win'] for p in ps))
    # Core contract: unknown/nonfinite estimates and non-melee baselines preserve teacher.
    for bad in (None, float('nan'), float('inf')):
        assert decide([1,2],1,{1:dict(actor=0,ordinary_melee=True,net_permille=bad),
                               2:dict(actor=0,ordinary_melee=True,net_permille=10)})[0] == 1
    result = dict(schema='visible-exchange-readonly-v1',passed=True,episodes=len(rows),
                  steps=sum(r['steps'] for r in rows),recomputed_paired=metrics,
                  replay_decisions=len(replay),replay_overrides=sum(r['overrode_teacher'] for r in replay),
                  real_new_games=0,bc_eligible=0,performance_improvement_proven=False,
                  leakage_perturbation_passed=True,rows=rows,replay=replay,
                  input_delivery_sha256=sha(OLD/'DELIVERY_AUDIT.json'),
                  policy_sha256=sha(HERE/'visible_exchange.py'))
    target = HERE/'READONLY_AUDIT.json'
    assert not target.exists(), 'Use a new output version; preserve old evidence'
    target.write_text(json.dumps(result, indent=2))
    print(json.dumps({k:v for k,v in result.items() if k not in ('rows','replay')}))


if __name__ == '__main__':
    main()
