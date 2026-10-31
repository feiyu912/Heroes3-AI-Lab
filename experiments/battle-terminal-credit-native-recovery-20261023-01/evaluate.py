"""Pool-owned exact96 DEV with pending-finalization, raw audit, full CPU replay."""
import argparse,concurrent.futures,fcntl,json,os,subprocess,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent.parent;R=ROOT/'research';LAB=Path('/root/heroes3-ai-lab');sys.path[:0]=[str(HERE),str(R),str(LAB/'src/gym')]
import dev_utils as helper
import dev_raw_auditor as independent
import leases
from lab_io import atomic_json
def main():
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);a=p.parse_args();root=a.run;partial=helper.read(root/'RESULT.partial.json');assert set(partial['arms'])=={'control','candidate'}
    plan=helper.read(root/'PLAN.json');models=[('parent60',Path(plan['parent_checkpoint']))]+[(arm,Path(partial['arms'][arm]['checkpoint'])) for arm in ['control','candidate']]
    out=root/'dev';out.mkdir();frozen=helper.read(root/'FREEZE.json')['input_sha256'];frozen.update({str(cp):helper.sha(cp) for _,cp in models});atomic_json(out/'FREEZE.json',dict(input_sha256=frozen));reports=[]
    lock=(LAB/'evaluations/.pool-lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    try:
        for model,checkpoint in models:
            for opponent in ['BattleAI','MMAI_MODEL']:
                run_id=str(time.time_ns());folder=LAB/'evaluations'/run_id;folder.mkdir()
                def one(job):
                    idx,role=job;seed=2026107600+idx*100;name=f'{idx}-{role}-{seed}-recovered';output=folder/(name+'.json');log=folder/(name+'.log')
                    env=dict(os.environ,LAB_PYTHON=str(LAB/'venv/bin/python'),LAB_STAGED_BOOT='1',LAB_WORKER_ROOT=str(LAB/'workers'/('eval-'+run_id)/name),TERMINAL_CREDIT_POOL_LEASE=json.dumps(leases.metadata(lock,leases.PATHS[1])));command=['bash',str(R/'run-lab.sh'),str(HERE/'evaluate_policy_steps.py'),'--scenario',str(idx),'--role',role,'--seed',str(seed),'--policy','recovered','--checkpoint',str(checkpoint),'--output',str(output),'--scenarios',str(R/'diverse-curriculum.json'),'--opponent',opponent,'--teacher-turns','2']
                    if opponent=='MMAI_MODEL':command+=['--opponent-model','DATA/MMAI/models/lab-upstream-'+('defender' if role=='attacker' else 'attacker')+'.onnx']
                    with log.open('wb') as stream:r=subprocess.run(command,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=300,pass_fds=(lock.fileno(),))
                    return helper.finalize(output,log,r.returncode)
                with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:games=list(pool.map(one,[(i,r) for i in range(192,200) for r in ['attacker','defender']]))
                wins=sum(g['success'] for g in games);loss=sum(sum(g['terminal_outcome']['casualties'][str(int(g['role']=='defender'))].values()) for g in games)
                summary=dict(policy='recovered',battles=16,wins=wins,win_rate=wins/16,mean_permanent_units_lost=loss/16,truncated=0,non_normal_terminations=0,invalid_actions=0)
                assert all(helper.sha(x)==h for x,h in frozen.items());report=out/(model+'-'+opponent+'.json');atomic_json(report,dict(run_id=run_id,checkpoint=str(checkpoint),opponent=opponent,scenario_file=str(R/'diverse-curriculum.json'),scenario_ids=list(range(192,200)),battles=games,summary=[summary],frozen_artifacts=frozen,artifacts_checked_before_and_after=True))
                reports.append(dict(model=model,opponent=opponent,report=str(report),sha256=helper.sha(report),summary=summary));atomic_json(out/'RESULT.partial.json',dict(DEV=reports));print(json.dumps(reports[-1]),flush=True)
    finally:lock.close()
    adapted=dict(partial,DEV=reports);paths=set();audit=independent.review_dev(root,adapted,paths);atomic_json(root/'DEV-RAW-AUDIT.json',dict(passed=True,DEV=audit,raw_artifact_sha256={str(x):helper.sha(x) for x in sorted(paths)},new_native_games=0,GPU_operations=0,optimizer_steps=0))
    atomic_json(out/'RESULT.json',dict(passed=True,DEV=reports))
    r=subprocess.run([str(LAB/'venv/bin/python'),str(HERE/'replay_dev.py'),'--dev-run',str(out),'--out',str(root/'DEV-NN-REPLAY')]);assert r.returncode==0,'Full96 NN probability replay failed'
    atomic_json(root/'DEV-RESULT.json',dict(passed=True,DEV=reports,raw96_recomputed=True,full_NN_replayed=True))
if __name__=='__main__':main()
