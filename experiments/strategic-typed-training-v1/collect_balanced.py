"""Eight on-policy cells under one frozen checkpoint; sequential one-CUDA-model collection."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;LAB=Path('/root/heroes3-ai-lab')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,v):Path(p).write_text(json.dumps(v,indent=2))
def main():
    p=argparse.ArgumentParser();p.add_argument('--checkpoint',type=Path,required=True);p.add_argument('--capsule',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=False);checkpoint_sha=sha(a.checkpoint)
    maps=['takeover-v2-train-01-mines','takeover-v2-train-02-development'];jobs=[]
    for map_name in maps:
        for opponent in ['EmptyAI','Nullkiller2']:
            for player in [0,1]:jobs.append(dict(map=map_name,opponent=opponent,player=player,seed=2026102810+len(jobs),logical_update=1))
    existing=HERE/'admitted-episode-02';old=json.loads((existing/'episode.json').read_text())
    assert old['checkpoint_sha256']==checkpoint_sha and old['job']['logical_update']==1
    assert (old['job']['map'],old['job']['opponent'],old['job']['owned_player'])==(jobs[7]['map'],jobs[7]['opponent'],jobs[7]['player'])
    jobs[7]['seed']=old['job']['seed'];jobs[7]['existing_admission']=str(existing)
    sources={str(f):sha(f) for f in [Path(__file__),HERE/'collect_episode_v2.py',HERE/'onpolicy_broker_v2.py',HERE/'model_io.py',HERE/'admit_episode_v2.py',HERE.parent/'strategic-typed-native-v1/audit_game_v4.py',HERE.parent/'strategic-typed-native-v1/raw_events_v4.py']}
    write(a.out/'PLAN.json',dict(schema='typed-eight-cell-onpolicy-collection-v1',jobs=jobs,checkpoint=str(a.checkpoint),checkpoint_sha256=checkpoint_sha,
        source_sha256=sources,optimizer_steps=0,parallelism=1,reason='Equal-cell terminal mixture; never combine different parent policies or optimize on a partial curriculum'))
    completed=[]
    def command(argv,log):
        result=subprocess.run(argv,capture_output=True,text=True);log.write_text(result.stdout+'\nSTDERR:\n'+result.stderr)
        assert result.returncode==0,'Stage failed; see '+str(log)
    try:
        for index,job in enumerate(jobs):
            assert sha(a.checkpoint)==checkpoint_sha and all(sha(f)==h for f,h in sources.items())
            root=a.out/f'cell-{index:02d}';root.mkdir()
            if 'existing_admission' in job:admission=Path(job['existing_admission'])
            else:
                run=root/'native';audit=root/'raw-audit';admission=root/'admitted'
                command(['/usr/bin/python3',str(HERE/'collect_episode_v2.py'),'--capsule',str(a.capsule),'--checkpoint',str(a.checkpoint),
                    '--player',str(job['player']),'--opponent',job['opponent'],'--map',job['map'],'--seed',str(job['seed']),
                    '--logical-update','1','--out',str(run)],root/'collection.log')
                command([str(LAB/'venv/bin/python'),str(HERE.parent/'strategic-typed-native-v1/audit_game_v4.py'),str(run),str(audit)],root/'raw-audit.log')
                command([str(LAB/'gpu-venv/bin/python'),str(HERE/'admit_episode_v2.py'),'--run',str(run),'--native-audit',str(audit/'AUDIT.json'),'--out',str(admission)],root/'admission.log')
            e=json.loads((admission/'episode.json').read_text());report=json.loads((admission/'AUDIT.json').read_text())
            assert report['passed'] and e['checkpoint_sha256']==checkpoint_sha and e['job']['logical_update']==1
            completed.append(dict(cell=index,job=job,admission=str(admission),admission_sha256=sha(admission/'AUDIT.json'),
                episode_id=e['episode_id'],reward=e['reward'],decisions=e['decisions'],policy_end_turns=report['policy_end_turns']))
            write(a.out/'PROGRESS.json',dict(completed=completed,optimizer_steps=0))
            print(json.dumps({'cell':index,'reward':e['reward'],'decisions':e['decisions'],'policy_end_turns':report['policy_end_turns']}),flush=True)
        assert len(completed)==8 and len({e['episode_id'] for e in completed})==8
        assert len({(e['job']['map'],e['job']['opponent'],e['job']['player']) for e in completed})==8
        result=dict(passed=True,episodes=completed,rows=sum(e['decisions'] for e in completed),wins=sum(e['reward']==1 for e in completed),losses=sum(e['reward']==-1 for e in completed),optimizer_steps=0,
            interpretation='On-policy collection only. Training outcomes are not independent evaluation or strength gain.')
    except BaseException as error:
        result=dict(passed=False,error=repr(error),completed=completed,accepted_curriculum_rows=0,optimizer_steps=0)
    write(a.out/'RESULT.json',result);print(json.dumps({k:v for k,v in result.items() if k not in ('episodes','completed')},indent=2))
    return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
