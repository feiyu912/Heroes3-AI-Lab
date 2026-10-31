"""Recover genuine completed original games; run only missing fixed DEV IDs."""
import argparse,collections,concurrent.futures,fcntl,hashlib,json,os,shutil,subprocess,sys,time
from pathlib import Path
import numpy as np
import torch
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent.parent;R=ROOT/'research';LAB=Path('/root/heroes3-ai-lab')
sys.path[:0]=[str(R),str(LAB/'src/gym')]
from observation_digest import update
from vcmi_gym.envs.v15.vcmi_env import Action
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,d):Path(p).write_text(json.dumps(d,indent=2)+'\n')
def inspect_steps(folder,identity):
    files=sorted(folder.glob('decision-*.pt'));assert files
    assert len(list(folder.glob('*.pt')))==2*len(files)
    evidence=[];digest=hashlib.sha256();types=collections.Counter();prior=None;last=None
    for tick,dp in enumerate(files,1):
        assert dp.name==f'decision-{tick:06d}.pt';tp=folder/f'transition-{tick:06d}.pt';d=torch.load(dp,map_location='cpu',weights_only=False);t=torch.load(tp,map_location='cpu',weights_only=False)
        assert d['identity']==t['identity']==identity and d['step']==t['step']==tick
        obs=d['obs'];ids=np.asarray(obs['active_action_ids']);scores=d['logits'];assert d['action']==int(ids[int(scores.argmax())]) and torch.equal(torch.softmax(scores,-1),d['probabilities'])
        h=hashlib.sha256();update(h,obs)
        if prior is not None:assert h.hexdigest()==prior
        update(digest,obs);h=hashlib.sha256();update(h,t['next_obs']);prior=h.hexdigest()
        if last:assert not last['terminated'] and not last['truncated']
        types[str(int(Action.decode_one(obs['nodes']['Action'][d['action']]).ACTION_TYPE))]+=1;last=t
        for p in (dp,tp):evidence.append(dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size))
    assert last['terminated'] and not last['truncated'] and last['next_obs']['terminal_outcome']['result_type']==0
    return dict(schema='battle-step-evidence-v1',path=str(folder),identity=identity,complete=True,decisions=len(files),native_step_returns=len(files),files=evidence,unreturned_decision=0),last,dict(types),digest.hexdigest()
def recovered(source,checkpoint,idx,role,seed):
    name=f'{idx}-{role}-{seed}-recovered';log=source/(name+'.log');steps=source/(name+'.steps')
    if not log.is_file():return None
    text=log.read_text();assert 'VCMI shutdown complete.' in text and 'Traceback' not in text
    first=torch.load(steps/'decision-000001.pt',map_location='cpu',weights_only=False);identity=first['identity']
    assert identity['checkpoint']==str(checkpoint) and identity['checkpoint_sha256']==sha(checkpoint) and identity['seed']==seed and identity['role']==role and identity['scenario_index']==idx and identity['opponent']=='BattleAI' and identity['opponent_model'] is None
    e,last,types,digest=inspect_steps(steps,identity);outcome=json.loads(json.dumps(last['next_obs']['terminal_outcome']));side=int(role=='defender')
    return dict(scenario=identity['scenario'],split='development',role=role,seed=seed,engine_seed=seed,opponent='BattleAI',opponent_model=None,opponent_seed=None,opponent_temperature=None,policy='recovered',checkpoint=str(checkpoint),steps=e['decisions'],terminated=True,truncated=False,invalid_actions=0,
        success=outcome['winner']==side,terminal_outcome=outcome,action_types=types,trajectory_sha256=digest,trajectory_hash_version=2,wall_seconds=None,policy_latency_ms=None,step_evidence=e,
        recovery=dict(source_log=str(log),source_log_sha256=sha(log),original_game_replayed=False,timing_not_reconstructable=True,individual_exit_code_not_recorded=True,normal_shutdown_and_complete_terminal_evidence_verified=True))
def finalize(output,log,returncode):
    assert returncode==0,'Child returned nonzero'
    text=log.read_text();assert 'VCMI shutdown complete.' in text and 'Traceback' not in text,'No normal native shutdown'
    pending=Path(str(output)+'.pending.json');d=read(pending);e,last,types,digest=inspect_steps(Path(d['step_evidence']['path']),d['step_evidence']['identity'])
    assert e==d['step_evidence'] and json.loads(json.dumps(last['next_obs']['terminal_outcome']))==d['terminal_outcome'] and d['trajectory_sha256']==digest and d['action_types']==types
    assert d['terminated'] and not d['truncated'] and d['terminal_outcome']['result_type']==0
    os.replace(pending,output)
    with log.open('a') as stream:stream.write(json.dumps(d)+'\n')
    return d
def main():
    p=argparse.ArgumentParser();p.add_argument('--training-run',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--execute',action='store_true');a=p.parse_args()
    assert a.execute;a.out.mkdir(parents=True,exist_ok=False);torch.set_num_threads(1)
    train=read(a.training_run/'candidate/training.json');assert train['completed'] and [x['update'] for x in train['records']]==[58,59,60]
    plan=read(a.training_run/'PLAN.json');parent=Path(plan['parent_checkpoint']);control=ROOT/'experiments/battle-training-continuation-20261020/monitor-independent-01/user-pause-01/control-update-60.pt';candidate=Path(train['checkpoint'])
    assert sha(control)==plan['control_unchanged_sha256'] and train['records'][-1]['actual_Adam_steps_total']==7680
    frozen=read(a.training_run/'candidate/FREEZE.json')['input_sha256'];assert all(sha(x)==h for x,h in frozen.items())
    frozen.update({str(x):sha(x) for x in HERE.iterdir() if x.is_file()})
    for x in (parent,control,candidate):frozen[str(x)]=sha(x)
    for x in [a.training_run/'candidate/training.json',a.training_run/'candidate/training.restoration.json',a.training_run/'candidate/FREEZE.json']:
        frozen[str(x)]=sha(x)
    for record in train['records']:
        for x in [candidate.parent/f"update-{record['update']}.pt",Path(record['rollout']['path'])]:frozen[str(x)]=sha(x)
    for x in (LAB/'evaluations/1792726710179968280').rglob('*'):
        if x.is_file():frozen[str(x)]=sha(x)
    write(a.out/'FREEZE.json',dict(input_sha256=frozen));write(a.out/'PLAN.json',dict(parent_checkpoint=str(parent),training_run=str(a.training_run),fixed96=True,seed_base=2026103600,DEV_indices=list(range(192,200)),no_retraining=True,old_failed_raw='/root/heroes3-ai-lab/evaluations/1792726710179968280'))
    result=dict(passed=False,control_retrained=False,candidate=dict(checkpoint=str(candidate),sha256=sha(candidate)),DEV=[],recovered_games=0,new_native_games=0,unscored_old_games=[])
    lock=(LAB/'evaluations/.pool-lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    try:
        for model,checkpoint in [('parent30',parent),('control',control),('candidate',candidate)]:
            for opponent in ['BattleAI','MMAI_MODEL']:
                run_id=str(time.time_ns());folder=LAB/'evaluations'/run_id;folder.mkdir();records={};jobs=[]
                for idx in range(192,200):
                    for role in ['attacker','defender']:
                        seed=2026103600+idx*100;name=f'{idx}-{role}-{seed}-recovered';out=folder/(name+'.json');log=folder/(name+'.log')
                        old=None
                        if model=='parent30' and opponent=='BattleAI':
                            try:old=recovered(LAB/'evaluations/1792726710179968280',checkpoint,idx,role,seed)
                            except BaseException as error:result['unscored_old_games'].append(dict(scenario=idx,role=role,seed=seed,error=repr(error)))
                        if old is not None:
                            write(out,old);shutil.copyfile(old['recovery']['source_log'],log)
                            with log.open('a') as stream:stream.write(json.dumps(old)+'\n')
                            records[(idx,role)]=old;result['recovered_games']+=1
                        else:jobs.append((idx,role,seed,out,log))
                def run(job):
                    idx,role,seed,out,log=job;env=dict(os.environ,LAB_PYTHON=str(LAB/'venv/bin/python'),LAB_STAGED_BOOT='1',LAB_WORKER_ROOT=str(LAB/'workers'/('eval-'+run_id)/out.stem))
                    command=['bash',str(R/'run-lab.sh'),str(HERE/'evaluate_policy_steps.py'),'--scenario',str(idx),'--role',role,'--seed',str(seed),'--policy','recovered','--checkpoint',str(checkpoint),'--output',str(out),'--scenarios',str(R/'diverse-curriculum.json'),'--opponent',opponent,'--teacher-turns','2']
                    if opponent=='MMAI_MODEL':command+=['--opponent-model','DATA/MMAI/models/lab-upstream-'+('defender' if role=='attacker' else 'attacker')+'.onnx']
                    with log.open('wb') as stream:r=subprocess.run(command,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=300)
                    return (idx,role),finalize(out,log,r.returncode)
                with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
                    for key,d in pool.map(run,jobs):records[key]=d;result['new_native_games']+=1
                games=[records[(i,r)] for i in range(192,200) for r in ['attacker','defender']];wins=sum(g['success'] for g in games);loss=sum(sum(g['terminal_outcome']['casualties'][str(int(g['role']=='defender'))].values()) for g in games)
                s=dict(policy='recovered',battles=16,wins=wins,win_rate=wins/16,truncated=0,non_normal_terminations=0,invalid_actions=0,mean_permanent_units_lost=loss/16)
                assert all(sha(x)==h for x,h in frozen.items());report=a.out/(model+'-'+opponent+'-DEV.json');write(report,dict(run_id=run_id,checkpoint=str(checkpoint),opponent=opponent,scenario_file=str(R/'diverse-curriculum.json'),scenario_ids=list(range(192,200)),summary=[s],battles=games,frozen_artifacts=frozen,artifacts_checked_before_and_after=True))
                result['DEV'].append(dict(model=model,opponent=opponent,report=str(report),sha256=sha(report),summary=s));write(a.out/'RESULT.partial.json',result);print(json.dumps(dict(model=model,opponent=opponent,summary=s,recovered=result['recovered_games'],native_new=result['new_native_games'])),flush=True)
        assert result['recovered_games']+result['new_native_games']==96;result['passed']=True
    except BaseException as error:result['error']=repr(error);raise
    finally:lock.close();write(a.out/'RESULT.json',result)
if __name__=='__main__':main()
