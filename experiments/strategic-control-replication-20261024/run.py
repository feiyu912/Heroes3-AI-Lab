"""Execute all fixed16 active-opponent DEV games; never select or train."""
import argparse,json,os,signal
from pathlib import Path
import leases
from pipeline_common import HERE,BASE,LAB,DEFAULT_CAPSULE,DEFAULT_INITIAL,CONTROL_CHECKPOINT,INITIAL_SHA,CONTROL_CHECKPOINT_SHA,source_inputs,capsule_inputs,sha
def write(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def interrupt(signum,frame):raise KeyboardInterrupt('Replication interrupted '+str(signum))
signal.signal(signal.SIGTERM,interrupt)
def resource(log,phase):
    m={k:int(v.split()[0]) for k,v in (x.split(':',1) for x in Path('/proc/meminfo').read_text().splitlines())}
    q=dict(phase=phase,available_mib=m['MemAvailable']/1024,swap_mib=(m['SwapTotal']-m['SwapFree'])/1024)
    with log.open('a') as f:f.write(json.dumps(q)+'\n')
    assert q['available_mib']>2048 and q['swap_mib']<256
def call(argv,log):
    resource(log.with_suffix('.memory.jsonl'),'before')
    with log.open('w') as stream:code=leases.run_owned(argv,env=dict(os.environ),stream=stream)
    assert code==0,'Invalid complete cell; preserve without retry '+str(log)
    resource(log.with_suffix('.memory.jsonl'),'after')
def jobs():
    return [dict(rep=rep,cell=i,map=('takeover-v2-dev-01-river' if i<4 else 'takeover-v2-dev-02-reserves'),player=i%2,opponent='Nullkiller2',seed=base+i) for rep,base in enumerate((2026108800,2026108900)) for i in (2,3,6,7)]
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--execute',action='store_true');a=p.parse_args()
    freeze=json.loads((HERE/'SOURCE_FREEZE.json').read_text());assert all(sha(path)==h for path,h in freeze['files'].items())
    assert sha(DEFAULT_INITIAL)==INITIAL_SHA and sha(CONTROL_CHECKPOINT)==CONTROL_CHECKPOINT_SHA
    a.out.mkdir(parents=True,exist_ok=False);models=dict(initial=DEFAULT_INITIAL,control=CONTROL_CHECKPOINT)
    write(a.out/'PLAN.json',dict(jobs=jobs(),models={k:dict(path=str(v),sha256=sha(v)) for k,v in models.items()},input_sha256=freeze['files'],execute=a.execute,optimizer_steps=0,model_promoted=False,final_test_touched=False))
    if not a.execute:return 0
    pairs=[];result=dict(passed=False,pairs=pairs,new_optimizer_steps=0,new_PPO_admissions=0,model_promoted=False,final_test_touched=False)
    try:
        for index,job in enumerate(jobs()):
            pair=dict(index=index,job=job,arms={})
            for arm,checkpoint in models.items():
                assert all(sha(path)==h for path,h in freeze['files'].items());root=a.out/f'pair-{index:02d}'/arm;root.mkdir(parents=True)
                call([str(LAB/'venv/bin/python'),str(HERE/'collect_cpu.py'),'--capsule',str(DEFAULT_CAPSULE),'--checkpoint',str(checkpoint),'--out',str(root/'native'),'--map',job['map'],'--player',str(job['player']),'--opponent',job['opponent'],'--seed',str(job['seed']),'--seconds','120'],root/'collect.log')
                call([str(LAB/'venv/bin/python'),str(HERE/'audit_game_v6.py'),str(root/'native'),str(root/'raw-audit')],root/'audit.log')
                call([str(LAB/'venv/bin/python'),str(HERE.parent/'takeover-20261023/independent-evidence-01/replay_priorzero_arm.py'),'--policy',str(BASE),'--raw',str(root/'native'),'--out',str(root/'CPU-REPLAY.json')],root/'replay.log')
                audit=json.loads((root/'raw-audit/AUDIT.json').read_text());cpu=json.loads((root/'CPU-REPLAY.json').read_text())
                assert cpu['model_sha256']==sha(checkpoint) and cpu['CPU_full_proposals_recomputed']==audit['actual_decisions_checked'] and cpu['victory']==(audit['winner']==('red' if job['player']==0 else 'blue'))
                pair['arms'][arm]=dict(win=cpu['victory'],decisions=cpu['CPU_full_proposals_recomputed'],recruits=cpu['counts'].get('recruit',0),creatures=cpu['recruited_quantity'],initial_request_sha256=sha(root/'native/agent/request-00000001.json'),audit_sha256=sha(root/'raw-audit/AUDIT.json'),CPU_replay_sha256=sha(root/'CPU-REPLAY.json'))
            pair['initial_request_equal']=len({x['initial_request_sha256'] for x in pair['arms'].values()})==1;pairs.append(pair);write(a.out/'PROGRESS.json',dict(pairs=pairs))
        result.update(passed=True,wins={arm:sum(p['arms'][arm]['win'] for p in pairs) for arm in models},positive_flips=sum(p['arms']['control']['win'] and not p['arms']['initial']['win'] for p in pairs),negative_flips=sum(p['arms']['initial']['win'] and not p['arms']['control']['win'] for p in pairs),full_CPU_proposals_recomputed=sum(x['decisions'] for p in pairs for x in p['arms'].values()),native_games=16)
    except BaseException as error:result['error']=repr(error)
    finally:leases.finish_owned_groups()
    write(a.out/'RESULT.json',result);print(json.dumps({k:v for k,v in result.items() if k!='pairs'}));return 0 if result['passed'] else 1
if __name__=='__main__':main()
