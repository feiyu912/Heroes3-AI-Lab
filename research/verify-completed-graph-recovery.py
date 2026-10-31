"""Audit the actual completed update112->128 CUDA recovery, without new training."""
import hashlib
import json
from pathlib import Path
import torch
from lab_io import atomic_json


def main():
    torch.set_num_threads(1)
    research=Path(__file__).resolve().parent
    report=json.loads((research/'v5-diverse-last.json').read_text())
    assert report['completed'] and report['all_workers_exit_zero'] and report['CUDA_training']
    assert report['resumed_from_updates']==112
    assert [record['update'] for record in report['records']]==list(range(113,129))
    assert all(record['truncations']==0 and record['metrics']['maximum_recompute_logp_error']==0.
               and record['metrics']['recompute_batch_size']==24 for record in report['records'])
    source=Path(report['config']['checkpoint'])
    target=Path(report['checkpoint'])
    before=torch.load(source,map_location='cpu',weights_only=True)
    after=torch.load(target,map_location='cpu',weights_only=True)
    assert before['completed_updates']==112 and after['completed_updates']==128
    assert after['environment_steps']-before['environment_steps']==16*24*32
    first=before['optimizer_state_dict'];last=after['optimizer_state_dict']
    assert first['param_groups']==last['param_groups']
    assert set(first['state'])==set(last['state'])
    increments=[float(last['state'][key]['step']-first['state'][key]['step']) for key in first['state']]
    assert min(increments)>0
    assert all(torch.isfinite(value).all() for role in after['models']
               for value in after['models'][role]['weights'].values())
    assert any(not torch.equal(before['models'][role]['weights'][name],value)
               for role in after['models'] for name,value in after['models'][role]['weights'].items())
    assert len(before['cuda_rng_states'])==len(after['cuda_rng_states'])>0
    assert any(not torch.equal(a,b) for a,b in zip(before['cuda_rng_states'],after['cuda_rng_states']))
    checksum=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()
    recovery=research.parent/'models/goal-v5-recovery'
    manifests=[json.loads(path.read_text()) for path in recovery.glob('*.json') if path.name!='latest.json']
    saved=next(item for item in manifests if item['source_checkpoint']==str(source))
    assert saved['sha256']==checksum(source)==checksum(saved['backup_checkpoint'])
    atomic_json(research/'completed-graph-recovery-contract.json',dict(
        passed=True,source_checkpoint=str(source),source_sha256=checksum(source),
        completed_checkpoint=str(target),completed_sha256=checksum(target),workers=24,
        optimizer_parameter_groups_preserved=True,optimizer_step_increments=[min(increments),max(increments)],
        resumed_updates=16,new_environment_steps=16*24*32,all_workers_exit_zero=True,
        CUDA_training=True,all_recompute_errors_zero=True,checkpoint_history=report['checkpoint_history'],
        scope='Actual completed CUDA continuation with preserved optimizer and RNG payloads. New games start on resume; not an exact replay of an interrupted in-battle simulator state.'))
    print('Completed 16-update CUDA recovery verified; optimizer increments',min(increments),max(increments),flush=True)


if __name__=='__main__':main()
