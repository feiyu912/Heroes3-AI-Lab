"""Independent read-only audit of the fixed, completed 16-game pilot."""
import gzip
import hashlib
import json
from pathlib import Path
import sys
import numpy as np

HERE=Path(__file__).resolve().parent
RUN=HERE
sys.path.insert(0,str(RUN))
sys.path.insert(0,'/mnt/g/Heroes3-AI-Lab/research')
from event_audit import action_window
from visible_exchange import choose
from battle_outcome_audit import audit as audit_outcome


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def unpack(row):
    return dict(nodes={k:np.asarray(v,dtype=np.float32) for k,v in row['nodes'].items()},
        edges={tuple(e['relation']):dict(index=np.asarray(e['index'],dtype=np.int64),
                                      attrs=np.asarray(e['attrs'],dtype=np.float32)) for e in row['edges']},
        active_action_ids=np.asarray(row['active_action_ids'],dtype=np.int64))


def main():
    protocol=json.loads((RUN/'runs/train/PROTOCOL.json').read_text())
    assert all(sha(p)==s for p,s in protocol['frozen'].items())
    rows=[]
    groups={}
    for path in sorted((RUN/'runs/train').glob('*.json')):
        if path.name=='PROTOCOL.json':continue
        s=json.loads(path.read_text())
        assert s['completed'] and s['terminated'] and not s['truncated']
        assert s['original_split']=='train' and s['invalid_actions']==0 and s['bc_eligible_decisions']==0
        assert all(sha(p)==h for p,h in s['frozen_artifacts'].items())
        audit_outcome([s])
        assert sha(s['archive'])==s['archive_sha256']
        with gzip.open(s['archive'],'rt') as f:d=json.load(f)
        assert len(d['transitions'])==s['steps'] and len(d['batches'])==s['steps']+1
        end=[e for e in d['batches'][-1]['events'] if e['kind']==3]
        assert len(end)==1 and end[0]['winner']==s['terminal_outcome']['winner']
        side=int(s['role']=='defender')
        overrides=[]
        for t in d['transitions']:
            assert t['executed_action'] in t['legal_actions']
            w=t['action_window']
            assert w==action_window(d['batches'][t['post_batch_id']]['events'],side,
                                   t['known_actor_id_before'],w['native_action_type'])
            assert w['status']=='matched' and not t['demonstration_gate']['eligible_for_bc']
            if s['policy']=='positive-exchange':
                obs=unpack(t['observation_before'])
                obs['teacher_action_id']=t['quality']['teacher_action']
                action,quality=choose(obs)
                assert action==t['executed_action'] and quality==t['quality']
                if quality['overrode_teacher']:
                    b=d['batches'][t['post_batch_id']]
                    overrides.append(dict(step=t['step_id'],quality=quality,
                        selected_facts=t['selected_facts'],strict_events=b['events'][w['start']:w['finish']+1]))
        casualty=s['terminal_outcome']['casualties'][str(side)]
        row=dict(path=str(path),summary_sha256=sha(path),archive_sha256=s['archive_sha256'],
            scenario=s['scenario'],role=s['role'],seed=s['seed'],policy=s['policy'],
            steps=s['steps'],won=int(s['success']),main_loss=casualty.get('6',0),
            total_loss=sum(casualty.values()),overrides=overrides,wall_seconds=s['wall_seconds'])
        rows.append(row)
        groups.setdefault((s['scenario'],s['role'],s['seed']),{})[s['policy']]=(row,d)
    assert len(rows)==16 and len(groups)==8
    paired=[]
    for key,p in groups.items():
        assert set(p)=={'teacher','positive-exchange'}
        b,bd=p['teacher'];c,cd=p['positive-exchange']
        assert bd['initial_observation']==cd['initial_observation']
        paired.append(dict(scenario=key[0],role=key[1],seed=key[2],delta_wins=c['won']-b['won'],
            delta_main_loss=c['main_loss']-b['main_loss'],delta_total_loss=c['total_loss']-b['total_loss'],
            overrides=len(c['overrides'])))
    cells={(p['scenario'],p['role']) for p in paired if p['overrides']}
    main_delta=sum(p['delta_main_loss'] for p in paired)
    map_deltas={s:sum(p['delta_main_loss'] for p in paired if p['scenario']==s) for s in {p['scenario'] for p in paired}}
    passed_gate=(len(cells)>=2 and min(p['delta_wins'] for p in paired)>=0 and main_delta<0 and max(map_deltas.values())<=0 and sum(p['delta_total_loss'] for p in paired)<=0)
    report=dict(schema='positive-exchange-v2-native-event-audit-v1',passed=True,episodes=16,
        steps=sum(r['steps'] for r in rows),normal=16,illegal=0,truncated=0,bc_eligible=0,
        actual_policy_choices_recomputed=True,raw_action_windows_recomputed=True,
        wins_by_method={m:sum(r['won'] for r in rows if r['policy']==m) for m in ('teacher','positive-exchange')},
        paired=paired,net_wins=sum(p['delta_wins'] for p in paired),
        mean_delta_main_loss=main_delta/8,mean_delta_total_loss=sum(p['delta_total_loss'] for p in paired)/8,
        overrides=sum(len(r['overrides']) for r in rows),override_fixture_role_cells=len(cells),
        map_main_casualty_deltas=map_deltas,preregistered_progression_gate_passed=passed_gate,
        independent_capability_test=False,certified=False,rows=rows,
        policy_sha256=sha(RUN/'visible_exchange.py'),protocol_sha256=sha(RUN/'runs/train/PROTOCOL.json'))
    target=HERE/'AUDIT.json'
    assert not target.exists()
    target.write_text(json.dumps(report,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k not in ('rows','paired')}))


if __name__=='__main__':main()
