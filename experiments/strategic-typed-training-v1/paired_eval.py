"""Frozen CPU argmax paired DEV evaluation; no optimizer, no final test maps."""
import argparse,hashlib,json,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent;LAB=Path('/root/heroes3-ai-lab')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,v):Path(p).write_text(json.dumps(v,indent=2))
def schedule():
    jobs=[]
    for map_name in ['takeover-v2-dev-01-river','takeover-v2-dev-02-reserves']:
        for opponent in ['EmptyAI','Nullkiller2']:
            for player in [0,1]:jobs.append(dict(map=map_name,opponent=opponent,player=player,seed=2026110600+len(jobs)))
    return jobs
def main():
    p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path,required=True);p.add_argument('--candidate',type=Path,required=True);p.add_argument('--capsule',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=False)
    models={'a':a.baseline,'b':a.candidate};hashes={arm:sha(path) for arm,path in models.items()}
    native=HERE.parent/'strategic-typed-native-v1'
    sources={str(p):sha(p) for p in [Path(__file__),HERE/'evaluate_game.py',HERE/'evaluation_broker.py',HERE/'model_io.py',native/'audit_game_v5.py',native/'raw_events_v4.py']}
    write(a.out/'PLAN.json',dict(schema='typed-cpu-argmax-paired-dev-v1',jobs=schedule(),models={k:str(v) for k,v in models.items()},model_sha256=hashes,
        source_sha256=sources,comparison='Frozen warmstart versus one same-policy eight-cell curriculum update',optimizer_steps=0,training_samples=0,
        preregistration=str(HERE/'PAIRED_DEV_PREREGISTRATION.md'),maps_seen_in_historical_development=True,finaltest_touched=False,
        outcomes='All eight pairs retained; invalid native game aborts; report pre-policy initial-state divergence if any.'))
    pairs=[]
    try:
        for i,job in enumerate(schedule()):
            result={'pair':i,'job':job,'arms':{}}
            for arm,checkpoint in models.items():
                assert sha(checkpoint)==hashes[arm] and all(sha(p)==h for p,h in sources.items())
                root=a.out/f'pair-{i:02d}'/arm;root.mkdir(parents=True)
                command=['/usr/bin/python3',str(HERE/'evaluate_game.py'),'--capsule',str(a.capsule),'--checkpoint',str(checkpoint),
                    '--player',str(job['player']),'--opponent',job['opponent'],'--map',job['map'],'--seed',str(job['seed']),'--out',str(root/'native')]
                executed=subprocess.run(command,capture_output=True,text=True);(root/'execution.log').write_text(executed.stdout+'\nSTDERR:\n'+executed.stderr)
                assert executed.returncode==0,'Evaluation launcher failed: '+str(root)
                audit_command=[str(LAB/'venv/bin/python'),str(native/'audit_game_v5.py'),str(root/'native'),str(root/'audit')]
                reviewed=subprocess.run(audit_command,capture_output=True,text=True);(root/'audit.log').write_text(reviewed.stdout+'\nSTDERR:\n'+reviewed.stderr)
                assert reviewed.returncode==0
                audit=json.loads((root/'audit/AUDIT.json').read_text())
                assert audit['whole_game_valid'] and audit['native_game_completed'] and audit['transport_drained'] and not audit['contract_errors']
                own='red' if job['player']==0 else 'blue'
                result['arms'][arm]={'win':audit['winner']==own,'winner':audit['winner'],'counts':audit['counts'],'audit_sha256':sha(root/'audit/AUDIT.json'),
                    'initial_request_sha256':sha(root/'native/agent/request-00000001.json')}
            result['initial_request_exact']=result['arms']['a']['initial_request_sha256']==result['arms']['b']['initial_request_sha256']
            result['win_delta']=int(result['arms']['b']['win'])-int(result['arms']['a']['win']);pairs.append(result)
            write(a.out/'PROGRESS.json',{'pairs':pairs,'optimizer_steps':0});print(json.dumps({'pair':i,'baseline_win':result['arms']['a']['win'],'candidate_win':result['arms']['b']['win'],'initial_request_exact':result['initial_request_exact']}),flush=True)
        summary=dict(passed=True,pairs=pairs,baseline_wins=sum(r['arms']['a']['win'] for r in pairs),candidate_wins=sum(r['arms']['b']['win'] for r in pairs),
            net_wins=sum(r['win_delta'] for r in pairs),discordant_pairs=sum(r['win_delta']!=0 for r in pairs),
            prepolicy_divergent_pairs=[r['pair'] for r in pairs if not r['initial_request_exact']],optimizer_steps=0,training_samples=0,
            limitation='Eight fresh-seed DEV pairs on two historically seen development maps. No final-test, universal win-rate or automatic learning-gain certification.')
    except BaseException as error:summary=dict(passed=False,error=repr(error),completed_pairs=pairs,optimizer_steps=0,training_samples=0)
    write(a.out/'RESULT.json',summary);print(json.dumps({k:v for k,v in summary.items() if k not in ['pairs','completed_pairs']},indent=2))
    return 0 if summary['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
