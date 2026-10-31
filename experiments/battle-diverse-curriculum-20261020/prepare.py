"""CPU-only derivative of the completed family trainer; frozen sources are read-only."""
from pathlib import Path
import difflib
HERE=Path(__file__).resolve().parent;OLD=HERE.with_name('battle-family-curriculum-20261020')
def once(t,a,b):assert t.count(a)==1,(a,t.count(a));return t.replace(a,b,1)
def output(name,old,new):
    (HERE/name).write_text(new);(HERE/(name+'.diff')).write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='frozen-family/'+name,tofile='diverse-60case/'+name)))
def main():
    old=(OLD/'support.py').read_text();t=old.replace("(12,4,32,'last')","(16,30,32,'last')").replace('2026102012','2026102016').replace('battle-family-balanced-last-v1','battle-diverse-60case-last-v1')
    t=once(t,'changed=[];sq=0.;frozen=0',"changed=[];sq=0.;frozen=0;groups={key:dict(changed_tensors=0,squared_delta=0.) for g in ('actor_heads','critic_heads','last_graph') for key in (g,'attacker/'+g,'defender/'+g)}")
    t=once(t,'changed.append(n);sq+=float(d.square().sum())',"""changed.append(n);size=float(d.square().sum());sq+=size
            group='actor_heads' if 'policy_head__' in n else 'critic_heads' if 'value_head__' in n else 'last_graph'
            role='attacker' if 'attacker' in n else 'defender'
            for key in (group,role+'/'+group):
                item=groups.setdefault(key,dict(changed_tensors=0,squared_delta=0.));item['changed_tensors']+=1;item['squared_delta']+=size""")
    t=once(t,'return dict(changed_tensors=len(changed),l2=sq**.5,unchanged_frozen_tensors=frozen,changed_parameter_names=changed)',"for item in groups.values():item['l2']=item.pop('squared_delta')**.5\n    return dict(changed_tensors=len(changed),l2=sq**.5,unchanged_frozen_tensors=frozen,changed_parameter_names=changed,parameter_groups=groups)")
    t=once(t,'torch.save(payload,tmp);os.replace(tmp,p)',"torch.save(payload,tmp);os.replace(tmp,p)\n    return dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size)")
    t=once(t,"assert all(sha(p)==h for p,h in b['frozen_inputs']['input_sha256'].items())","assert all(sha(p)==h for p,h in b['frozen_inputs']['input_sha256'].items())\n        assert sha(b['rollout_evidence']['path'])==b['rollout_evidence']['sha256']")
    output('support.py',old,t)
    old=(OLD/'train_last_graph.py').read_text();t=old
    t=once(t,'    args=p.parse_args()',"    args=p.parse_args()\n    args.torch_version=str(torch.__version__);args.numpy_version=np.__version__;args.cuda_version=torch.version.cuda")
    t=once(t,'phase_close_events=[];live_steps=[]','phase_close_events=[];live_steps=[];phase_resource_events=[]')
    t=once(t,'                curriculum.resource_gate()','                phase_resource_events.append(dict(phase=phase,**curriculum.resource_gate()))')
    t=once(t,'            support.save_rollout(folder,','            rollout_evidence=support.save_rollout(folder,')
    t=once(t,"record.update(actual_Adam_steps=", "record.update(phase=phase,rollout=rollout_evidence,actual_Adam_steps=")
    t=once(t,"actual_Adam_steps=counter['steps'],complete_update_boundary=True,frozen_inputs=frozen,","actual_Adam_steps=counter['steps'],complete_update_boundary=True,frozen_inputs=frozen,rollout_evidence=rollout_evidence,")
    t=t.replace('phase_close_events=phase_close_events','phase_close_events=phase_close_events,phase_resource_events=phase_resource_events')
    output('train_last_graph.py',old,t)
    old=(OLD/'run.py').read_text();t=old.replace('battle-family-balanced-last-v1','battle-diverse-60case-last-v1').replace('2026102012','2026102016').replace('2026102600','2026103400')
    t=t.replace("'--workers','12','--updates','4'","'--workers','16','--updates','30'").replace('workers=12,updates=4,owned_transitions_budget=1536','workers=16,updates=30,owned_transitions_budget=15360')
    t=t.replace("len(t['records'])==4","len(t['records'])==30").replace("'update4'","'update30'")
    t=once(t,"paths.add(LAB/'onnxruntime/lib/libonnxruntime.so')", "paths.add(R/'full-graph-contract.json');paths.update((gym/'vcmi_gym').rglob('*.py'))\n    paths.add(LAB/'onnxruntime/lib/libonnxruntime.so')")
    output('run.py',old,t)
    old=(OLD/'evaluate_bounded.py').read_text();output('evaluate_bounded.py',old,old.replace('default=2026102500','default=2026103400'))
if __name__=='__main__':main()
