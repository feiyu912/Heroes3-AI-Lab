"""CPU TRAIN probe: first16 rows of each saved rollout, fixed before computing results."""
import hashlib,json,sys,time
from pathlib import Path
import numpy as np
import torch
HERE=Path(__file__).resolve().parent;LAB=Path('/root/heroes3-ai-lab');R=HERE.parent.parent.parent/'research';sys.path.insert(0,str(R))
import full_graph_policy as graph
from masked_ppo import distribution
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    torch.set_num_threads(1);start=time.monotonic();run=LAB/'evaluations/battle-diverse60-native-02';tp=run/'training.json';t=json.loads(tp.read_text());assert t['completed'] and len(t['records'])==30
    b=LAB/'models/graph-finetune/1792068859379237126/update-64.pt';f=Path(t['checkpoint']);models=[graph.FullGraphPair(str(p),'last').cpu().eval() for p in (b,f)];results=[];inputs=[Path(__file__),tp,b,f]
    with torch.inference_mode():
        for record in t['records']:
            rp=Path(record['rollout']['path']);assert sha(rp)==record['rollout']['sha256'];raw=torch.load(rp,map_location='cpu',weights_only=False);inputs.append(rp)
            obs=raw['samples'][:16];actions=torch.tensor(raw['actions'][:16]);batch=graph.collate(obs,'cpu');dist=[distribution(m(*batch)[0],batch[-1]) for m in models]
            p,q=dist[0].probs,dist[1].probs;lp0,lp1=[d.log_prob(actions) for d in dist];kl=torch.where(p>0,p*(dist[0].logits-dist[1].logits),0).sum(-1)
            for i,o in enumerate(obs):
                results.append(dict(update=record['update'],slot=i,scenario=raw['configs'][i]['TRAIN_scenario_index'],role=raw['configs'][i]['role'],opponent=raw['configs'][i]['opponent'],legal_actions=len(o['active_action_ids']),B64_argmax=int(p[i].argmax()),final_argmax=int(q[i].argmax()),argmax_changed=bool(p[i].argmax()!=q[i].argmax()),KL_B64_final=float(kl[i]),sampled_action_logp_delta=float(lp1[i]-lp0[i]),B64_entropy=float(dist[0].entropy()[i]),final_entropy=float(dist[1].entropy()[i])))
            print(json.dumps(dict(update=record['update'],probed=len(results))),flush=True)
    def stat(values):return dict(min=float(min(values)),mean=float(np.mean(values)),median=float(np.median(values)),max=float(max(values)))
    metrics={k:stat([r['metrics'][k] for r in t['records']]) for k in ('policy_loss','value_loss','entropy','approximate_kl','gradient_norm','clip_fraction','epochs_completed')}
    report=dict(passed=True,scope='480 fixed TRAIN rows: first16 from each of30 rollouts; not full rollout distribution, DEV or layer-capacity causation',selected_rows=480,unique_cases=len({r['scenario'] for r in results}),argmax_changed=sum(r['argmax_changed'] for r in results),KL_B64_final=stat([r['KL_B64_final'] for r in results]),absolute_sampled_action_logp_delta=stat([abs(r['sampled_action_logp_delta']) for r in results]),B64_entropy=stat([r['B64_entropy'] for r in results]),final_entropy=stat([r['final_entropy'] for r in results]),recorded_all30_update_metrics=metrics,rows=results,new_native_games=0,GPU_operations=0,optimizer_steps_performed=0,input_sha256={str(p):sha(p) for p in inputs},elapsed_seconds=time.monotonic()-start)
    (HERE/'LEARNING_MAGNITUDE.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ('rows','input_sha256')},indent=2))
if __name__=='__main__':main()
