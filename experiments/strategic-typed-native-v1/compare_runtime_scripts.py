"""Explain the failed capsule using controlled raw-prefix/runtime evidence."""
import json,hashlib,collections
from pathlib import Path
ROOT=Path('/root/heroes3-ai-lab/evaluations')
BAD=ROOT/'typed-schema4-policy-fullgame-01';GOOD=ROOT/'typed-schema4-policy-fullgame-02'
CONTROL=Path('/root/heroes3-ai-lab/workers/adv-runs/typed-battle-loop-v8-control-01-2026102601-gjymqstd')
OUT=Path('/mnt/g/Heroes3-AI-Lab/experiments/strategic-typed-native-v1/runtime-scripts-causal-audit-01')
def rows(p):return [json.loads(s) for s in p.read_text().splitlines()]
def norm(d):
    d=dict(d);d['candidates']=[{k:v for k,v in c.items() if k!='op'} for c in d['candidates'] if c.get('op')!='end_turn']
    return d
bad=[norm(d) for d in rows(BAD/'strategy-decisions.jsonl')]
good=[norm(d) for d in rows(GOOD/'strategy-decisions.jsonl')]
control=[norm(d) for d in rows(CONTROL/'strategy-decisions.jsonl')]
assert len(bad)==264 and len(good)==len(control)==275
assert bad==good[:264] and good==control
badplan=json.loads((BAD/'PLAN.json').read_text());goodplan=json.loads((GOOD/'PLAN.json').read_text())
assert badplan['seed']==goodplan['seed']==2026102601 and badplan['checkpoint']==goodplan['checkpoint']
be=json.loads((BAD/'EXECUTION.json').read_text());ge=json.loads((GOOD/'EXECUTION.json').read_text())
assert be['loaded_library_observations'][0]['libraries'][0]['sha256']==ge['loaded_library_observations'][0]['libraries'][0]['sha256']
missing=[]
for n,line in enumerate((BAD/'client.log').read_text(errors='replace').splitlines(),1):
    if 'Script layer not found:' in line:missing.append({'line':n,'message':line.split('Script layer not found:',1)[1].strip()})
assert any('DAMAGE/DAMAGECALCULATOR' in x['message'] for x in missing)
assert 'Script layer not found:' not in (GOOD/'client.log').read_text(errors='replace')
assert not be['game_completed'] and ge['game_completed'] and ge['client_exit']==0
states=rows(GOOD/'strategy-trace.jsonl');ending=[x for x in states if x['event'] in ('victory','defeat')]
assert len(ending)==1 and ending[0]['event']=='victory' and ending[0]['day']==30
scripts={k:v for k,v in goodplan['hashes'].items() if '/scripts/' in k}
assert scripts and all(hashlib.sha256(Path(k).read_bytes()).hexdigest()==v for k,v in scripts.items())
result={'passed':True,'same_capsule_same_seed_same_model':True,'same_initial_264_move_decisions':True,
        'all_275_normalized_move_decisions_match_V8_control':True,'missing_native_script_layers':missing,
        'restored_script_files':len(scripts),'normal_native_outcome':'red victory day30','ability_improvement_claim':False,
        'failed_run_reward':None,'training_samples':0,'optimizer_steps':0,
        'interpretation':'Omitted native runtime scripts caused zero-damage battle behavior. Adding the compiled-epoch scripts restored normal game completion. Neither model nor battle AI algorithm was changed.'}
OUT.mkdir(exist_ok=False);(OUT/'AUDIT.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='missing_native_script_layers'},indent=2))
