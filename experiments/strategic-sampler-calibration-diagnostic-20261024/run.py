"""Four argmax TRAIN games, paired with already archived stochastic evidence."""
import argparse,json,os,signal
from pathlib import Path
import leases
from pipeline_common import HERE,PARENT,BASE,LAB,DEFAULT_CAPSULE,DEFAULT_INITIAL,INITIAL_SHA,source_inputs,capsule_inputs,sha
STUDY=LAB/'evaluations/strategic-active-learning-native-01'
def write(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def interrupt(signum,frame):raise KeyboardInterrupt('Diagnostic interrupted '+str(signum))
signal.signal(signal.SIGTERM,interrupt)
def resources(log,phase):
    m={k:int(v.split()[0]) for k,v in (line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines())}
    row=dict(phase=phase,available_mib=m['MemAvailable']/1024,swap_mib=(m['SwapTotal']-m['SwapFree'])/1024)
    with log.open('a') as f:f.write(json.dumps(row)+'\n')
    assert row['available_mib']>2048 and row['swap_mib']<256
def command(argv,log):
    resources(log.with_suffix('.memory.jsonl'),'before')
    with log.open('w') as stream:code=leases.run_owned(argv,env=dict(os.environ),stream=stream)
    assert code==0,'Invalid diagnostic stage; no retry: '+str(log)
    resources(log.with_suffix('.memory.jsonl'),'after')
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--execute',action='store_true');a=p.parse_args()
    frozen=json.loads((HERE/'SOURCE_FREEZE.json').read_text())['files'];assert all(sha(p)==h for p,h in frozen.items())
    jobs=[]
    for i in (2,3,6,7):
        raw=STUDY/'curriculum'/f'cell-{i:02d}'/'native';plan=json.loads((raw/'PLAN.json').read_text());episode=json.loads((raw.parent/'admitted/episode.json').read_text())
        assert episode['reward']==-1. and plan['checkpoint']==str(DEFAULT_INITIAL) and plan['multiplier']==4 and plan['seed']==2026104400+i
        assert sha(DEFAULT_INITIAL)==INITIAL_SHA and episode['sampling_replay_exact']
        jobs.append(dict(index=i,map=plan['map'],player=plan['owned_player'],opponent=plan['opponent'],seed=plan['seed'],stochastic_native=str(raw),stochastic_plan_sha256=sha(raw/'PLAN.json'),stochastic_proposals_sha256=sha(raw/'agent/typed-broker.jsonl')))
    a.out.mkdir(parents=True,exist_ok=False);write(a.out/'PLAN.json',dict(jobs=jobs,files=frozen,execute=a.execute,optimizer_steps=0,new_PPO_admissions=0,final_test_touched=False))
    if not a.execute:return 0
    assert json.loads((STUDY/'RESULT.json').read_text())['passed'],'Existing full study must finish before diagnostics'
    entries=[];report=dict(passed=False,entries=entries,optimizer_steps=0,new_PPO_admissions=0,final_test_touched=False)
    try:
        for j in jobs:
            assert all(sha(p)==h for p,h in frozen.items());root=a.out/f"cell-{j['index']:02d}";root.mkdir()
            command([str(LAB/'venv/bin/python'),str(HERE/'collect_cpu.py'),'--capsule',str(DEFAULT_CAPSULE),'--checkpoint',str(DEFAULT_INITIAL),'--out',str(root/'native'),'--map',j['map'],'--player',str(j['player']),'--opponent',j['opponent'],'--seed',str(j['seed']),'--seconds','120'],root/'collect.log')
            command([str(LAB/'venv/bin/python'),str(HERE/'audit_game_v6.py'),str(root/'native'),str(root/'raw-audit')],root/'audit.log')
            command([str(LAB/'venv/bin/python'),str(HERE.parent/'takeover-20261023/independent-evidence-01/replay_priorzero_arm.py'),'--policy',str(BASE),'--raw',str(root/'native'),'--out',str(root/'CPU-REPLAY.json')],root/'replay.log')
            replay=json.loads((root/'CPU-REPLAY.json').read_text());audit=json.loads((root/'raw-audit/AUDIT.json').read_text());assert replay['CPU_full_proposals_recomputed']==audit['actual_decisions_checked']
            from collections import Counter
            from pipeline_common import require_qualification
            binding=require_qualification();ids={x['canonical_key']:x['creature_id'] for x in json.loads(Path(binding['catalog_path']).read_text())['entries']}
            local_plan=json.loads((root/'native/PLAN.json').read_text());variant=local_plan['map_variant']
            expected=Counter()
            for stack in variant['modified_army']:expected[ids[stack['type']]]+=stack['amount']
            first=json.loads((root/'native/strategy-trace.jsonl').read_text().splitlines()[0]);assert first['event']=='turn_start' and first['day']==1 and first['player']==j['player'] and len(first['heroes'])==1
            actual=Counter()
            for cid,n in first['heroes'][0]['army']:actual[cid]+=n
            assert actual==expected and sha(root/'native'/('data/vcmi/Maps/adv/'+j['map']+'.vmap'))==variant['sha256']
            archived=Path(j['stochastic_native']);old=[json.loads(x) for x in (archived/'agent/typed-broker.jsonl').read_text().splitlines()];new=[json.loads(x) for x in (root/'native/agent/typed-broker.jsonl').read_text().splitlines()]
            first=None;prefix=0
            for index,(s,g) in enumerate(zip(old,new),1):
                if s['request']!=g['request'] or s['action']!=g['action']:
                    first=dict(step=index,request_equal=s['request']==g['request'],stochastic_action=s['action'],argmax_action=g['action'],stochastic_request_sha256=s['request_sha256'],argmax_request_sha256=g['request_sha256']);break
                prefix+=1
            entries.append(dict(job=j,argmax_win=replay['victory'],stochastic_win=False,argmax_decisions=len(new),stochastic_decisions=len(old),equal_public_request_action_prefix=prefix,first_difference=first,full_CPU_decisions_recomputed=replay['CPU_full_proposals_recomputed']))
            write(a.out/'PROGRESS.json',dict(entries=entries))
        command([str(LAB/'gpu-venv/bin/python'),str(HERE/'check_devices.py'),'--run',str(a.out),'--out',str(a.out/'DEVICES.json')],a.out/'devices.log')
        devices=json.loads((a.out/'DEVICES.json').read_text());assert devices['passed']
        assert all(sha(p)==h for p,h in frozen.items())
        report.update(passed=True,argmax_wins=sum(e['argmax_win'] for e in entries),stochastic_wins=0,actual_new_native_games=4,full_CPU_proposals_recomputed=sum(e['full_CPU_decisions_recomputed'] for e in entries),device_check=devices)
    except BaseException as error:report['error']=repr(error)
    finally:leases.finish_owned_groups()
    write(a.out/'RESULT.json',report);print(json.dumps({k:v for k,v in report.items() if k not in ('entries','device_check')}));return 0 if report['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
