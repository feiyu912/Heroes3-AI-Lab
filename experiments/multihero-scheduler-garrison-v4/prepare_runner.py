"""Derive an isolated stricter runner; never modify historical probe files."""
from pathlib import Path
import json
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'multihero-scheduler-probe-v1'

def main():
    s=(OLD/'run_scheduler.py').read_text()
    start=s.index('def scheduler_ready(')
    end=s.index('\ndef run(',start)
    s=s[:start]+'''def scheduler_ready(path):
    trace=path.parent/'strategy-trace.jsonl'
    if not path.exists() or not trace.exists(): return False
    try:
        rows=[json.loads(x) for x in path.read_text().splitlines() if x.strip()]
        states=[json.loads(x) for x in trace.read_text().splitlines() if x.strip()]
    except json.JSONDecodeError: return False
    if not any(r.get('event')=='garrison_setup_ack' and r.get('result')==1 for r in rows): return False
    for turn in (1,2):
        for hero in (0,2):
            sent={r['request_id'] for r in rows if r.get('event')=='move_sent' and r.get('hero')==hero and r.get('own_turn')==turn}
            ack={r['request_id'] for r in rows if r.get('event')=='move_ack' and r.get('result')==1 and r.get('hero')==hero and r.get('own_turn')==turn}
            positions={(h['x'],h['y'],h['z']) for r in states if r.get('own_turn')==turn for h in r.get('heroes',[]) if h['id']==hero}
            if not sent.intersection(ack) or len(positions)<2: return False
    return True

''' + s[end:]
    s=s.replace('multihero-scheduler-probe-v1','multihero-scheduler-garrison-v2')
    s=s.replace('fixture-01.vmap','fixture-02.vmap').replace('fixture-01.json','fixture-02.json')
    s=s.replace('HERE / "prepare_scheduler.py"','HERE / "derive.py"')
    s=s.replace('choices=("scheduler",)','choices=("baseline", "filtered")')
    s=s.replace('proved_two_mobile_heroes_move_ack','observed_two_mobile_heroes_two_turns')
    s=s.replace('two-mobile-heroes-distinct-move-sent-ack','real-garrison-and-two-mobile-heroes-each-of-two-turns')
    s=s.replace('inputs += sorted(initial_config.rglob("*.json"))', 'inputs += [HERE / "PLAN.md", HERE / "prepare_runner.py", HERE / "audit_legacy.py", HERE / "DERIVATION.json"]\n    inputs += sorted(initial_config.rglob("*.json"))')
    (HERE/'run_scheduler.py').write_text(s)
    a=(OLD/'audit_scheduler.py').read_text()
    a=a.replace('multihero-scheduler-probe-v1','multihero-scheduler-garrison-v2')
    a=a.replace('row.get("variant") != "scheduler"','row.get("variant") != "garrison-v2"')
    a=a.replace('proved_two_mobile_heroes_move_ack','observed_two_mobile_heroes_two_turns')
    (HERE/'audit_legacy.py').write_text(a)
    (HERE/'fixture-02.json').write_text(json.dumps({
        'map_sha256':'aa50587cb8ced39df3f1e1a476a00bde5cdfbb16c6a8dc12ddfdebbff5498e13',
        'mobile_heroes':[0,2], 'control_hero':3,
        'runtime_setup':'Actual GarrisonHeroSwap request/ACK before any scheduler selection. Require real owned positive-MP garrison, visiting=null, matching town/hero references.',
        'map_bytes':'Unchanged from fixture-01; map alone does not establish garrison.',
        'same_seed':2026102501,'policy_broker':False,'optimizer_steps':0
    },indent=2))

if __name__=='__main__': main()
