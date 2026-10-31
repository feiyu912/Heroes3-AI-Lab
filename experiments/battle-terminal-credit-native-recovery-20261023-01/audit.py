"""Independent CPU raw P/S, actual native-return, target and checkpoint review."""
import argparse,hashlib,json,sys
from pathlib import Path
import numpy as np
import torch
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent.parent;sys.path[:0]=[str(ROOT/'research'),str(Path('/root/heroes3-ai-lab/src/gym'))]
import targets,restore_learner as restore
import full_graph_policy as graph
from observation_digest import update as digest_obs
def obs_hash(obs):h=hashlib.sha256();digest_obs(h,obs);return h.hexdigest()
def read(path):return json.loads(path.read_text())
def payload(path):return torch.load(path,map_location='cpu',weights_only=False)
def raw_check(path,count,loss,prior=None):
    b=payload(path);arr=b['arrays'];assert len(b['journal'])==2*count and len(b['raw']['samples'])==len(b['raw']['actions'])==count*16
    assert b['suffix_private_RNG']==(not loss) and restore.sha(b['behavior_checkpoint'])==b['behavior_checkpoint_sha256']
    all_files=[];terminals=0;wins=0
    for tick in range(count):
        pair=b['journal'][tick*2:tick*2+2]
        for item in pair:assert restore.sha(item['path'])==item['sha256'] and Path(item['path']).stat().st_size==item['bytes'];all_files.append(item['path'])
        d,r=[payload(item['path']) for item in pair];assert d['loss_membership']==loss and len(d['obs'])==len(r['responses'])==16
        if prior is not None:assert [obs_hash(x) for x in prior]==[obs_hash(x) for x in d['obs']]
        for slot,(obs,response) in enumerate(zip(d['obs'],r['responses'])):
            assert not response.get('CPU_fixture_only'),'Synthetic fixture cannot certify native qualification'
            row=tick*16+slot;ids=obs['active_action_ids'];action=int(d['actions'][slot]);native=d['native_actions'][slot];assert native==int(ids[action]) and 0<=action<len(ids)
            scores=d['logits'][slot];prob=d['probabilities'][slot];assert torch.isfinite(scores[:len(ids)]).all() and torch.allclose(torch.softmax(scores,-1),prob,atol=2e-6,rtol=0) and prob[action]>0
            assert b['raw']['actions'][row]==action and obs_hash(b['raw']['samples'][row])==obs_hash(obs)
            assert abs(float(torch.log_softmax(scores,-1)[action])-b['raw']['old_logp'][row])<2e-5
            real=response['native_step_return'];assert bool(real['terminated'])==response['terminated']
            assert response['terminated']==bool(arr['terminal'][tick,slot]) and response['truncated']==bool(arr['truncated'][tick,slot])
            if response['terminated']:
                assert response['outcome']==real['obs']['terminal_outcome'] and response['outcome']['result_type']==0
                expected=1. if response['outcome']['winner']==obs['lab_side'] else -1.;assert abs(response['reward']-expected)<1e-7;terminals+=1;wins+=expected>0
            else:assert response['reward']==0.
            nxt=0. if response['terminated'] else graph.potential(response['final_features'] if response['truncated'] else response['features'])
            shaped=response['reward']+.5*(nxt-graph.potential(obs));assert abs(shaped-float(arr['reward'][tick,slot]))<2e-6
            assert abs(float(d['values'][slot])-float(arr['value'][tick,slot]))<1e-7
        prior=[x['features'] for x in r['responses']]
    return b,prior,dict(terminals=terminals,wins=wins,rows=count*16),all_files
def main():
    p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True);a=p.parse_args();torch.set_num_threads(1);d=read(a.stage/'RESULT.json');assert d['passed'] and d['normal_workers_shutdown'];phases=sorted(a.stage.glob('phase-*'));checks=[]
    for folder in phases:
        phase=int(folder.name.split('-')[-1]);workers=read(folder/'WORKERS.json');registered=read(HERE/'REGISTERED_CURRICULUM.json')['phases'][phase]
        assert len(set(workers['worker_PIDs']))==16 and all(pid>0 for pid in workers['worker_PIDs']) and workers['torch_imported']==[False]*16
        for cfg,row in zip(workers['configs'],registered):
            assert all(cfg[name]==row[name] for name in ['map','role','opponent','seed','family']) and cfg['TRAIN_scenario_index']==row['scenario_index'] and cfg['initial_reset_once'] and cfg['step_cost']==0
        p0,next0,c0,f0=raw_check(folder/'admitted-0.pt',32,True);p1,next1,c1,f1=raw_check(folder/'admitted-1.pt',32,True,next0);s,nexts,cs,fs=raw_check(folder/'suffix.pt',64,False,next1)
        assert p1['behavior_checkpoint_sha256']==s['behavior_checkpoint_sha256']
        saved=payload(folder/'TARGETS.pt');recomputed=targets.build(p1['arrays'],s['arrays'],d['arm'])
        behavior=torch.load(s['behavior_checkpoint'],map_location='cpu',weights_only=True)
        assert restore.digest(restore.weight_state(behavior))==saved['behavior_model_digest']==saved['behavior_model_after_suffix']
        assert restore.digest(behavior['optimizer_state_dict'])==saved['Adam_digest']==saved['Adam_after_suffix']
        assert saved['learning_RNG_before_suffix']==saved['learning_RNG_after_suffix'] and len(saved['private_sampling_RNG_before'])==len(saved['private_sampling_RNG_after'])==16
        for key in ['advantage','returns','base_advantage','base_returns','candidate_advantage','candidate_returns','eligible']:assert np.array_equal(recomputed[key],saved['targets'][key]),key
        assert saved['targets']['reason']==recomputed['reason'] and saved['global_RNG_unchanged']
        for kind in ['prefix','suffix']:
            e=saved[kind];assert restore.sha(e['path'])==e['sha256']
        checks.append(dict(phase=int(folder.name.split('-')[-1]),admitted_observed_rows=1024,suffix_observed_rows=1024,suffix_loss_rows=0,eligible_workers=int(recomputed['eligible'].sum()),reasons=recomputed['reason'],prefix_terminations=c0['terminals']+c1['terminals'],suffix_terminations=cs['terminals'],all_journal_files=len(f0+f1+fs),behavior_checkpoint_sha256=s['behavior_checkpoint_sha256']))
    if d['qualify_only']:assert d['actual_Adam_steps']==7680 and d['admitted_stage_rows']==0 and d['qualified']
    else:
        for record in d['records']:
            assert record['actual_Adam']==128 and restore.sha(record['checkpoint'])==record['checkpoint_sha256']
            m,opt,b,spec=restore.prepare(record['checkpoint'],record['checkpoint_sha256']);counter=restore.install_counter(opt);restore.restore_CPU(b,spec,m,opt,counter)
            assert b['actual_Adam_steps']==record['cumulative_Adam'] and b['environment_steps']==30720+record['admitted_stage_rows'] and b['terminal_credit_experiment']['suffix_stage_rows']==record['suffix_stage_rows']
            assert all(restore.sha(path)==expected for path,expected in b['frozen_inputs']['input_sha256'].items())
    report=dict(passed=True,stage=str(a.stage),qualify_only=d['qualify_only'],phase_checks=checks,actual_Adam_steps=d['actual_Adam_steps'],source_sha256=restore.sha(__file__),new_native_games=0,GPU_operations=0,optimizer_steps=0,independent_native_step_and_target_recompute=True)
    (a.stage/'AUDIT.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
