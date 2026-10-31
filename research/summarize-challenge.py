"""Held-out matchup metrics with scenario-cluster uncertainty, including failures."""
import json
from pathlib import Path
import numpy as np
from battle_outcome_audit import audit

r=Path('/mnt/g/Heroes3-AI-Lab/research')
results=json.loads((r/'fresh-challenge-results.json').read_text())
rng=np.random.default_rng(20261019)
groups=None
reports={}
for entry in results:
    data=json.loads(Path(entry['report']).read_text())
    rows=data['battles'];reports[entry['name']]=data
    audited=audit(rows)
    assert audited['battles']==512 and data['summary'][0]['battles']==512
    assert audited['verified_wins']==data['summary'][0]['wins']==entry['summary'][0]['wins']
    assert len({(row['scenario'],row['role'],row['seed']) for row in rows})==512
    cases=sorted({x['scenario'] for x in rows})
    assert len(cases)==32
    means=np.asarray([np.mean([x['success'] for x in rows if x['scenario']==case]) for case in cases])
    boot=means[rng.integers(0,len(means),(20000,len(means)))].mean(1)
    entry['scenario_cluster95']=np.quantile(boot,[.025,.975]).tolist()
    entry['case_results']=[dict(scenario=case,wins=sum(x['success'] for x in rows if x['scenario']==case),
        battles=sum(x['scenario']==case for x in rows),
        truncated=sum(x['truncated'] for x in rows if x['scenario']==case)) for case in cases]
    assert all(x['invalid_actions']==0 for x in rows)

def paired(a,b):
    a=reports[a]['battles'];b=reports[b]['battles']
    key=lambda x:(x['scenario'],x['role'],x['seed'])
    da={key(x):int(x['success']) for x in a};db={key(x):int(x['success']) for x in b}
    assert da.keys()==db.keys()
    cases=sorted({k[0] for k in da})
    differences=np.asarray([np.mean([da[k]-db[k] for k in da if k[0]==case]) for case in cases])
    boot=differences[rng.integers(0,len(cases),(20000,len(cases)))].mean(1)
    return dict(mean=float(differences.mean()),scenario_cluster95=np.quantile(boot,[.025,.975]).tolist())

selection=json.loads((r/'challenge-final-selection.json').read_text())
versus=reports['fresh-selected-vs-upstream']['summary'][0]
battleai=reports['fresh-selected-vs-battleai']['summary'][0]
direct=next(x for x in results if x['name']=='fresh-selected-vs-upstream')
summary=dict(selection=selection,fresh_results=results,
    improvements=dict(vs_old_lab=paired('fresh-selected-vs-battleai','fresh-v3-vs-battleai'),
                      vs_original_upstream=paired('fresh-selected-vs-battleai','fresh-upstream-vs-battleai'),
                      direct_vs_old_lab=paired('fresh-selected-vs-upstream','fresh-v3-vs-upstream')),
    objectives=dict(beat_upstream_point_estimate=versus['win_rate']>.5,
        beat_upstream_cluster95_lower_above_half=direct['scenario_cluster95'][0]>.5,
        near100_defined_as_at_least95_percent=battleai['win_rate']>=.95,
        observed100=battleai['wins']==battleai['battles'] and not battleai['truncated']),
    scope='Fresh32 exact mirror three-stack cases; two upgraded pools absent from local additional curricula (upstream pretraining exposure unknown); each512 real games, role swaps and8 seeds; no test selection',
    limitations=['One new training seed per method; cluster intervals describe scenario variation, not complete training-seed variation',
                'Same plain battlefield geometry; not complete Heroes III strategy, magic, siege or human strength',
                'Previously seen160-test suite used diagnostically; only fresh512 suite is final holdout',
                'Unlinked continuation switched from12/roll64 to24/roll32 at user request; not an architecture-only control',
                'Recovered candidates start from public upstream weights, not a from-scratch achievement; selected fine-tuning mode: '+selection.get('finetuning_mode','heads or lab-gnn')])
(r/'CHALLENGE_RESULTS.json').write_text(json.dumps(summary,indent=2))
print(json.dumps(summary['objectives'],indent=2))
