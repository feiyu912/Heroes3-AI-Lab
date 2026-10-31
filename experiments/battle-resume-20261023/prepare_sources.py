"""Derive isolated audited continuation; never modifies the frozen experiment."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'battle-training-continuation-20261020'
def derive(name,replacements):
    text=(OLD/name).read_text()
    for before,after in replacements:
        assert before in text,(name,before)
        text=text.replace(before,after)
    (HERE/name).write_text(text)
    return dict(source=str(OLD/name),sha256=hashlib.sha256((OLD/name).read_bytes()).hexdigest())
provenance={}
provenance['restore_learner.py']=derive('restore_learner.py',[
 ("/root/heroes3-ai-lab/evaluations/battle-diverse60-native-02/models/1792504676114060650/update-30.pt","/root/heroes3-ai-lab/evaluations/battle-continuation-lr-paired-01/candidate/models/1792509605969861627/update-57.pt"),
 ('dcaab92162b9c5b4cb9e5d9773067a320fe9b81fe91c1907449d4a7f8374cdaa','8d3169e85d51b0bf7d7247cc2d4bdc6949410d5262793f1729a6463dbd3976bf')])
provenance['support.py']=derive('support.py',[
 ("(16,30,32,'last')","(16,3,32,'last')"),
 ("assert a.arm in ('control','candidate')","assert a.arm == 'candidate'"),
 ("battle-continuation-lastgraph-lr-v1","battle-candidate57-resume-v1")])
provenance['curriculum.py']=derive('curriculum.py',[
 ("SCHEDULE_EPOCH='continuation-update31-60-native-seeds3800-v1'","SCHEDULE_EPOCH='candidate57-resume-fresh-phase13-20261023-v1'"),
 ("seed=r['seed'],feature_version", "seed=(2026105800+phase*1000+r['slot'] if phase==13 else r['seed']),feature_version")])
provenance['audit_restore_cuda.py']=derive('audit_restore_cuda.py',[])
provenance['train_last_graph.py']=derive('train_last_graph.py',[
 ("==(30,15360,3840)","==(57,29184,7296)"),
 ("parent_completed_updates=30,parent_environment_steps=15360,parent_actual_Adam_steps=3840", "parent_completed_updates=57,parent_environment_steps=29184,parent_actual_Adam_steps=7296"),
 ("optimizer.param_groups[1]['lr']==1e-6", "optimizer.param_groups[1]['lr']==3e-6"),
 ("group='last_graph',before=1e-6", "group='last_graph',before=3e-6"),
 ("if iteration%args.rotate_every==0:","if iteration==0 or iteration==1:"),
 ("phase=iteration//args.rotate_every", "phase=13 if iteration==0 else 14"),
 ("assert counter['steps']==3840", "assert counter['steps']==7296"),
 ("counter['steps']-3840", "counter['steps']-7296"),
 ("counter['steps']>3840", "counter['steps']>7296"),
 ("native_environment_restorable=False,phase_close_events", "resume_boundary=dict(checkpoint_update=57,checkpoint_Adam=7296,discarded_native_inflight=True,first_phase=13,phase13_remaining_updates=1,phase13_fresh_seed_base=2026105800,phase14_original_seeds=True),native_environment_restorable=False,phase_close_events")])
(HERE/'DERIVATION.json').write_text(json.dumps(provenance,indent=2)+'\n')
