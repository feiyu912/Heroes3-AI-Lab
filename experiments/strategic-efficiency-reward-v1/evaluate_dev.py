"""Fresh paired DEV games on qualified native runtime; no expert proxy or training."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;EXPERIMENTS=HERE.parent;LAB=Path('/root/heroes3-ai-lab')
DRAIN=EXPERIMENTS/'strategic-director-terminal-drain-v4'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2))

def run_one():
    # Reuse original qualified runner directly. Its CLI advertises TRAIN names;
    # its run() accepts this explicitly frozen DEV map with identical semantics.
    p=argparse.ArgumentParser();p.add_argument('--native-one',action='store_true');p.add_argument('--capsule',type=Path);p.add_argument('--checkpoint',type=Path)
    p.add_argument('--out',type=Path);p.add_argument('--map');p.add_argument('--player',type=int);p.add_argument('--opponent');p.add_argument('--seed',type=int)
    a=p.parse_args();a.seconds=120;a.load_save=None;a.logical_update=0;a.threat_replan='off';a.decision_policy='model'
    assert a.map in ('takeover-v2-dev-01-river','takeover-v2-dev-02-reserves') and a.player in (0,1) and a.opponent in ('EmptyAI','Nullkiller2')
    sys.path.insert(0,str(DRAIN))
    from run_proxy_game_director_drain import run
    return run(a)

def main():
    p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path,required=True);p.add_argument('--candidate',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    capsule=LAB/'evaluations/typed-director-terminal-drain-capsule-03'
    models={'a':a.baseline.resolve(),'b':a.candidate.resolve()};jobs=[]
    for m in ('takeover-v2-dev-01-river','takeover-v2-dev-02-reserves'):
        for o in ('EmptyAI','Nullkiller2'):
            for player in (0,1):jobs.append(dict(map=m,opponent=o,player=player,seed=2026102400+len(jobs)))
    sources=[Path(__file__),HERE/'PLAN.md',DRAIN/'run_proxy_game_director_drain.py',DRAIN/'audit_game_v6.py',DRAIN/'director_registry_v1.py',DRAIN/'CANDIDATE_MANIFEST.json',
        EXPERIMENTS/'strategic-threat-replan-v2/clearance_broker.py',EXPERIMENTS/'strategic-threat-replan-v2/clearance_proxy.py',
        EXPERIMENTS/'strategic-typed-training-v1/model_io.py',EXPERIMENTS/'strategic-typed-training-v1/live_jsonl.py',EXPERIMENTS/'strategic-typed-native-v1/raw_events_v4.py',
        EXPERIMENTS/'multihero-mechanism-probe-v1/build-driver-frozen-03/capsule_support.py',capsule/'EXECUTION.json',capsule/'build-source-manifest.json']
    sources+=list((EXPERIMENTS/'strategic-policy-v3').glob('*.py'))+list(models.values())
    sources +=[LAB/('data/vcmi/Maps/adv/'+j['map']+'.vmap') for j in jobs]
    frozen={str(x):sha(x) for x in sources}
    write(a.out/'PLAN.json',dict(jobs=jobs,model_paths={k:str(v) for k,v in models.items()},input_sha256=frozen,
        native_runtime=str(capsule),threat_replan='off',decision_policy='model',sampling='CPU argmax',training_samples=0,optimizer_steps=0,
        finaltest_touched=False,scope='Two historically seen DEV maps, eight fresh-seed pairs. No claim of hidden-world determinism or general strength. All invalid games abort; never drop a discordant pair.'))
    pairs=[]
    try:
        for i,job in enumerate(jobs):
            pair={'pair':i,'job':job,'arms':{}}
            for arm,checkpoint in models.items():
                assert all(sha(p)==h for p,h in frozen.items())
                root=a.out/f'pair-{i:02d}'/arm;root.mkdir(parents=True)
                commands=[['/usr/bin/python3',Path(__file__),'--native-one','--capsule',capsule,'--checkpoint',checkpoint,'--out',root/'native',
                    '--map',job['map'],'--player',job['player'],'--opponent',job['opponent'],'--seed',job['seed']],
                    [LAB/'venv/bin/python',DRAIN/'audit_game_v6.py',root/'native',root/'raw-audit']]
                for k,command in enumerate(commands):
                    r=subprocess.run(list(map(str,command)),capture_output=True,text=True);(root/f'command-{k}.log').write_text(r.stdout+'\nSTDERR:\n'+r.stderr)
                    assert r.returncode==0,'Invalid evaluation arm, unscored: '+str(root)
                audit=json.loads((root/'raw-audit/AUDIT.json').read_text());assert audit['whole_game_valid'] and audit['native_game_completed'] and audit['transport_drained']
                proposals=[json.loads(s) for s in (root/'native/agent/typed-broker.jsonl').read_text().splitlines()]
                pair['arms'][arm]={'win':audit['winner']==('red' if job['player']==0 else 'blue'),'counts':audit['counts'],
                    'audit_sha256':sha(root/'raw-audit/AUDIT.json'),'initial_request_sha256':sha(root/'native/agent/request-00000001.json'),
                    'policy_end_turns':sum(x['response']['op']=='end_turn' for x in proposals)}
            pair['initial_request_exact']=pair['arms']['a']['initial_request_sha256']==pair['arms']['b']['initial_request_sha256']
            pair['win_delta']=int(pair['arms']['b']['win'])-int(pair['arms']['a']['win']);pairs.append(pair)
            write(a.out/'PROGRESS.json',dict(pairs=pairs));print(json.dumps(pair),flush=True)
        result=dict(passed=True,pairs=pairs,baseline_wins=sum(x['arms']['a']['win'] for x in pairs),candidate_wins=sum(x['arms']['b']['win'] for x in pairs),
            net_wins=sum(x['win_delta'] for x in pairs),optimizer_steps=0,training_samples=0,finaltest_touched=False,ability_improvement_claim=False,
            limitation='Small DEV evidence only. Initial request equality is not hidden-world or RNG equality; raw ordering divergence needs analysis before causal attribution.')
    except BaseException as error:result=dict(passed=False,error=repr(error),completed_pairs=pairs,optimizer_steps=0,training_samples=0)
    write(a.out/'RESULT.json',result);print(json.dumps({k:v for k,v in result.items() if k not in ('pairs','completed_pairs')},indent=2))
    return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(run_one() if '--native-one' in sys.argv else main())

