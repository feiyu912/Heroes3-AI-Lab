"""Native recovered-policy DEV with real per-step observations/actions and returns."""
import argparse,collections,copy,hashlib,importlib.util,json,os,sys,time
from pathlib import Path
import numpy as np
import torch
from step_evidence import Journal,sha
HERE=Path(__file__).resolve().parent;R=HERE.parent.parent/'research';sys.path.insert(0,str(R))
from observation_digest import update as update_digest
from vcmi_gym.envs.v15.vcmi_env import Action
def load(name,file):
    s=importlib.util.spec_from_file_location(name,file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def main():
    p=argparse.ArgumentParser();p.add_argument('--scenario',type=int,required=True);p.add_argument('--role',choices=['attacker','defender'],required=True)
    p.add_argument('--seed',type=int,required=True);p.add_argument('--policy',choices=['recovered'],required=True);p.add_argument('--checkpoint',required=True)
    p.add_argument('--output',required=True);p.add_argument('--scenarios',required=True);p.add_argument('--opponent',choices=['BattleAI','MMAI_MODEL'],required=True)
    p.add_argument('--opponent-model');p.add_argument('--teacher-turns',type=int,default=2);a=p.parse_args()
    assert all(os.environ.get(k) in (None,'','0') for k in ('LAB_BATTLEAI_TEACHER','LAB_NATIVE_ONNX_CUDA','LAB_ONNX_CUDA'))
    torch.set_num_threads(1);cases=json.loads(Path(a.scenarios).read_text());scenario=cases[a.scenario]
    assert 192<=a.scenario<200 and scenario['split']=='development'
    model=load('recovered_graph',R/'recovered-graph.py').RecoveredPair(a.checkpoint).eval().models[a.role]
    os.environ['LAB_BATTLEAI_TEACHER_TURNS']=str(a.teacher_turns);os.environ['LAB_RANDOM_POLICY_SEED']=str(a.seed+100000)
    identity=dict(scenario_index=a.scenario,scenario=scenario['id'],role=a.role,seed=a.seed,checkpoint=a.checkpoint,checkpoint_sha256=sha(a.checkpoint),opponent=a.opponent,opponent_model=a.opponent_model)
    journal=Journal(Path(a.output).with_suffix('.steps'),identity);env=None;complete=False
    started=time.monotonic();latencies=[];action_types=[];digest=hashlib.sha256();term=trunc=False
    try:
        env=load('lab_env',R/'lab-env.py').make_env(scenario['map'],a.seed,a.role,opponent=a.opponent,opponent_model=a.opponent_model)
        obs,_=env.reset()
        while not (term or trunc):
            update_digest(digest,obs);before=time.perf_counter()
            with torch.inference_mode():logits,value=model(obs)
            ids=np.asarray(obs['active_action_ids']);action=int(ids[int(logits.argmax())]);latencies.append((time.perf_counter()-before)*1000)
            action_types.append(int(Action.decode_one(obs['nodes']['Action'][action]).ACTION_TYPE))
            journal.decision(copy.deepcopy(obs),logits,value,action)
            obs,reward,term,trunc,info=env.step(action)
            journal.transition(copy.deepcopy(obs),reward,term,trunc,copy.deepcopy(info))
        outcome=obs.get('terminal_outcome');side=int(a.role=='defender')
        result=dict(scenario=scenario['id'],split=scenario['split'],role=a.role,seed=a.seed,engine_seed=a.seed,opponent=a.opponent,opponent_model=a.opponent_model,
            opponent_seed=a.seed if a.opponent=='MMAI_MODEL' else None,opponent_temperature=0 if a.opponent=='MMAI_MODEL' else None,
            policy=a.policy,checkpoint=a.checkpoint,steps=len(action_types),terminated=bool(term),truncated=bool(trunc),invalid_actions=0,
            success=bool(term and not trunc and outcome and outcome['result_type']==0 and outcome['winner']==side),terminal_outcome=outcome,
            action_types=dict(collections.Counter(action_types)),trajectory_sha256=digest.hexdigest(),trajectory_hash_version=2,
            wall_seconds=time.monotonic()-started,policy_latency_ms=dict(zip(['p50','p95','p99'],np.percentile(latencies,[50,95,99]).tolist())),step_evidence=journal.manifest(complete=True))
        # Native close can exit the interpreter. Parent alone finalizes this
        # pending result after exit0 AND normal shutdown AND complete raw steps.
        Path(a.output+'.pending.json').write_text(json.dumps(result,indent=2)+'\n')
        env.close();env=None;complete=True
    finally:
        try:
            if env is not None:env.close()
        finally:
            if not complete:Path(a.output+'.partial.json').write_text(json.dumps(journal.manifest(complete=False),indent=2)+'\n')
if __name__=='__main__':main()
