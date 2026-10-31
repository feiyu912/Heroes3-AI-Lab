"""Actual parent restore, production targets and real NN collector over marked fixtures."""
import ast,copy,json,random,sys
from pathlib import Path
import numpy as np
import torch
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent.parent;sys.path[:0]=[str(HERE),str(ROOT/'research'),'/root/heroes3-ai-lab/src/gym']
import restore_learner as restore,targets,learner_impl as train
def main():
    p=__import__('argparse').ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);torch.set_num_threads(1)
    for path in HERE.glob('*.py'):ast.parse(path.read_text())
    import subprocess
    probe=subprocess.run([sys.executable,'-c',"import runpy,sys;runpy.run_path(sys.argv[1],run_name='__mp_main__');assert 'torch' not in sys.modules;print('spawn_import_without_Torch_passed')",str(HERE/'train.py')],capture_output=True,text=True)
    assert probe.returncode==0 and 'spawn_import_without_Torch_passed' in probe.stdout
    deriv=json.loads((HERE/'DERIVATION.json').read_text());assert all(restore.sha(x['source'])==x['sha256'] for x in deriv.values())
    m,opt,b,spec=restore.prepare();counter=restore.install_counter(opt);restored=restore.restore_CPU(b,spec,m,opt,counter);restored.pop('CUDA_rng_payload');assert counter['steps']==7680 and b['completed_updates']==60 and [x['lr'] for x in opt.param_groups]==[1e-5,1e-6]
    def blank(n):return dict(reward=np.zeros((n,16),np.float32),value=np.full((n,16),.2,np.float32),next_value=np.full((n,16),.2,np.float32),terminal=np.zeros((n,16),bool),truncated=np.zeros((n,16),bool))
    prefix=blank(32);suffix=blank(64);suffix['terminal'][1,0]=True;suffix['reward'][1,0]=1;suffix['reward'][2:,0]=999;suffix['terminal'][2,1]=True;suffix['reward'][2,1]=-1;suffix['truncated'][0,3]=True
    c=targets.build(prefix,suffix,'control');n=targets.build(prefix,suffix,'candidate');assert np.array_equal(c['advantage'],c['base_advantage']) and np.array_equal(n['advantage'][:,2:],c['advantage'][:,2:]);assert n['advantage'][-1,0]>c['advantage'][-1,0] and n['advantage'][-1,1]<c['advantage'][-1,1]
    suffix2={k:v.copy() for k,v in suffix.items()};suffix2['reward'][2:,0]=-888;assert np.array_equal(n['advantage'][:,0],targets.build(prefix,suffix2,'candidate')['advantage'][:,0])
    # A real NN sees actual historic TRAIN graph inputs. The fixture transition
    # source is deliberately synthetic and marked; no engine/learning is run.
    tp=Path('/root/heroes3-ai-lab/evaluations/battle-diverse60-native-02/training.json');record=json.loads(tp.read_text())['records'][0];rp=Path(record['rollout']['path']);assert restore.sha(rp)==record['rollout']['sha256'];raw=torch.load(rp,map_location='cpu',weights_only=False);obs=raw['samples'][:16]
    class FixtureVector:
        def step(self,actions):
            assert len(actions)==16
            result=[]
            for o,action in zip(obs,actions):
                assert int(action) in o['active_action_ids'];features=copy.deepcopy(o)
                result.append(dict(features=features,reward=0.,terminated=False,truncated=False,final_features=None,outcome=None,CPU_fixture_only=True,native_step_return=dict(obs=features,reward=0.,terminated=False,truncated=False,info=dict(CPU_fixture_only=True))))
            return result
    folder=a.out/'SYNTHETIC_COLLECTOR_FIXTURE';folder.mkdir();digest_before=restore.digest(m.state_dict());adam_before=restore.digest(opt.state_dict());rng=train.global_rng();generators=[torch.Generator().manual_seed(2026106980+i) for i in range(16)]
    _,arrays,proposals,evidence=train.collect(m,FixtureVector(),obs,2,folder,'suffix-fixture',restore.DEFAULT_CHECKPOINT,generators)
    assert train.global_rng()==rng and arrays['reward'].shape==(2,16) and len(proposals['actions'])==32 and len(proposals['old_logp'])==32
    import audit
    try:audit.raw_check(Path(evidence['path']),2,False)
    except AssertionError as error:assert 'Synthetic fixture' in str(error)
    else:raise AssertionError('Synthetic collector fixture accepted as native qualification')
    assert restore.digest(m.state_dict())==digest_before and restore.digest(opt.state_dict())==adam_before and counter['steps']==7680
    assert torch.equal(torch.get_rng_state(),b['torch_rng_state']) and random.getstate()==b['python_rng_state'] and restore.numpy_state_payload()==b['numpy_rng_state']
    report=dict(passed=True,actual_CPU_parent_restore=restored,spawn_import_without_Torch=True,production_float32_target_cases=['win','loss','cap_original_bootstrap','truncation_original_bootstrap','post_terminal_no_leakage','control_exact_baseline'],collector_real_NN_legal_sampling_over_marked_synthetic_fixture=True,collector_private_RNG_preserved=True,collector_zero_loss_suffix=True,collector_evidence=evidence,synthetic_fixture_rejected_by_native_auditor=True,synthetic_fixture_not_native_qualification=True,new_native_games=0,GPU_operations=0,optimizer_steps=0,resource_locks_taken=False,source_sha256={str(x):restore.sha(x) for x in HERE.glob('*.py')})
    (a.out/'AUDIT.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(passed=True,new_native_games=0,GPU_operations=0,optimizer_steps=0)))
if __name__=='__main__':main()
