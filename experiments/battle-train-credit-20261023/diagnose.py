"""Read-only common31..57 TRAIN credit audit and existing fixed480 graph replay."""
import argparse,collections,hashlib,json,sys,time
from pathlib import Path
import numpy as np
import torch
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent.parent;R=ROOT/'research';OLD=ROOT/'experiments/battle-training-continuation-20261020';LAB=Path('/root/heroes3-ai-lab')
sys.path[:0]=[str(OLD),str(R),str(LAB/'src/gym')]
import curriculum
import full_graph_policy as graph
from masked_ppo import gae,distribution
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def stat(xs):
    return dict(n=len(xs),mean=float(np.mean(xs)),median=float(np.median(xs)),max=float(max(xs)),p90=float(np.percentile(xs,90))) if xs else dict(n=0)
def summarize(rows):
    done=[r for r in rows if r['terminal']];closed=[r for r in rows if r['fragment']=='phase_close'];censored=[r for r in rows if r['fragment']=='window_end'];episodes=[r['episode_length'] for r in done]
    return dict(rows=len(rows),terminals=len(done),wins=sum(r['win'] for r in done),losses=sum(not r['win'] for r in done),truncations=sum(r['truncated'] for r in rows),
        raw_advantage=stat([r['advantage'] for r in rows]),normalized_advantage=stat([r['normalized_advantage'] for r in rows]),normalized_positive_rows=sum(r['normalized_advantage']>0 for r in rows),
        phase_close_rows=len(closed),phase_close_fraction=len(closed)/len(rows),window_right_censored_rows=len(censored),
        phase_close_normalized_advantage=stat([r['normalized_advantage'] for r in closed]),phase_close_last_bootstrap=stat([r['next_value'] for r in closed if r['phase_last']]),
        terminal_episode_length=stat(episodes),completed_episodes_gt32=sum(x>32 for x in episodes),completed_cross_update_episodes=sum(r['cross_update_episode'] for r in done),
        rows_with_later_observed_terminal_beyond_own_rollout=sum(r['later_terminal_other_update'] for r in rows),rows_with_terminal_in_own_rollout=sum(r['terminal_in_own_rollout'] for r in rows),
        terminal_distance=stat([r['terminal_distance'] for r in rows if r['terminal_distance'] is not None]),direct_terminal_GAE_weight=stat([r['terminal_weight'] for r in rows if r['terminal_in_own_rollout']]))
def rollouts(inputs):
    reports={};allrows={};phaseinfo={}
    for arm in ['control','candidate']:
        tp=LAB/'evaluations/battle-continuation-lr-paired-01'/arm/'training.json';t=read(tp);inputs.add(tp);records=t['records'][:27];assert [x['update'] for x in records]==list(range(31,58))
        rows=[];live=[[] for _ in range(16)];phase_rows=[];phase_summaries=[]
        for offset,record in enumerate(records):
            phase=offset//2
            if offset%2==0:
                assert not any(live);phase_rows=[]
            rp=Path(record['rollout']['path']);assert sha(rp)==record['rollout']['sha256'];inputs.add(rp);raw=torch.load(rp,map_location='cpu',weights_only=False)
            assert len(raw['samples'])==len(raw['actions'])==512 and record['phase']==phase
            adv,ret=gae(raw['rewards'],raw['values'],raw['next_values'],raw['terminated'],raw['truncated'],gamma=1.,lam=.95)
            assert np.isfinite(adv).all() and np.isfinite(ret).all();norm=(adv-adv.mean())/max(float(adv.std()),1e-8)
            last=np.asarray(raw['rewards'][-1])+np.asarray(raw['next_values'][-1])*(~np.asarray(raw['terminated'][-1],bool))-np.asarray(raw['values'][-1]);assert np.allclose(adv[-1],last,atol=1e-6,rtol=0)
            for tick in range(32):
                for slot,cfg in enumerate(raw['configs']):
                    i=tick*16+slot;obs=raw['samples'][i];action=raw['actions'][i];assert 0<=action<len(obs['active_action_ids']) and obs['lab_side']==int(cfg['role']=='defender') and 0<=cfg['TRAIN_scenario_index']<192
                    terminal=bool(raw['terminated'][tick][slot]);truncated=bool(raw['truncated'][tick][slot]);win=False
                    if terminal:
                        reward=float(raw['rewards'][tick][slot])+.5*graph.potential(obs);assert min(abs(reward-1),abs(reward+1))<1e-5;win=reward>0
                    row=dict(update=record['update'],tick=tick,slot=slot,phase=phase,family=cfg['family'],role=cfg['role'],opponent=cfg['opponent'],scenario=cfg['TRAIN_scenario_index'],advantage=float(adv[tick,slot]),normalized_advantage=float(norm[tick,slot]),next_value=float(raw['next_values'][tick][slot]),terminal=terminal,truncated=truncated,win=win,fragment=None,episode_length=None,cross_update_episode=False,terminal_distance=None,terminal_in_own_rollout=False,later_terminal_other_update=False,terminal_weight=0.,phase_last=False)
                    rows.append(row);phase_rows.append(row);live[slot].append(row)
                    if terminal or truncated:
                        episode=live[slot];row['episode_length']=len(episode);row['cross_update_episode']=episode[0]['update']!=row['update']
                        for distance,earlier in enumerate(reversed(episode),1):
                            if terminal:
                                earlier['terminal_distance']=distance;earlier['terminal_in_own_rollout']=earlier['update']==row['update'];earlier['later_terminal_other_update']=earlier['update']!=row['update'];earlier['terminal_weight']=.95**(distance-1) if earlier['terminal_in_own_rollout'] else 0.
                        live[slot]=[]
            if offset%2==1 or offset==26:
                kind='phase_close' if offset%2==1 else 'window_end'
                durations=[len(x) for x in live]
                if kind=='phase_close':assert curriculum.close_evidence(phase,durations,raw['configs'],'phase_switch')==t['phase_close_events'][phase]
                for fragment in live:
                    for row in fragment:row['fragment']=kind
                    if fragment:fragment[-1]['phase_last']=True
                phase_summaries.append(dict(phase=phase,kind=kind,fragment_steps=durations,fragment_rows=sum(durations),sampled_rows=len(phase_rows),terminals=sum(r['terminal'] for r in phase_rows)))
                live=[[] for _ in range(16)]
            print(json.dumps(dict(arm=arm,checked_update=record['update'])),flush=True)
            del raw
        grouped={}
        for fields in [('role',),('opponent',),('family',),('role','opponent','family')]:
            groups=collections.defaultdict(list)
            for row in rows:groups[tuple(row[k] for k in fields)].append(row)
            grouped['+'.join(fields)]=[dict(zip(fields,key),metrics=summarize(value)) for key,value in sorted(groups.items())]
        allrows[arm]=rows;reports[arm]=dict(overall=summarize(rows),groups=grouped,phase_closures=phase_summaries)
        assert sum(r['terminal'] for r in rows)==records[-1]['episodes'] and sum(r['win'] for r in rows)==records[-1]['wins']
    assert len(allrows['control'])==len(allrows['candidate'])==13824
    return reports,allrows
def replay(inputs):
    proofpath=ROOT/'experiments/battle-diverse-curriculum-20261020/final-independent-01/LEARNING_MAGNITUDE.json';proof=read(proofpath);inputs.add(proofpath)
    tp=LAB/'evaluations/battle-diverse60-native-02/training.json';t=read(tp);inputs.add(tp)
    checkpoints=[Path('/root/heroes3-ai-lab/evaluations/battle-diverse60-native-02/models/1792504676114060650/update-30.pt'),ROOT/'experiments/battle-training-continuation-20261020/monitor-independent-01/user-pause-01/control-update-60.pt',ROOT/'experiments/battle-dev-repair-20261023/delivery-01/candidate-update-60.pt']
    expected=['dcaab92162b9c5b4cb9e5d9773067a320fe9b81fe91c1907449d4a7f8374cdaa','443863dd26ea0daaed17cd01ab3dd44a6a16544efac73c96a89839f5b72c0e20','cbac78e2f60e0d4942e6d689ca9878dd7288d9b4faa2dbdd5d7efcb104199bc7']
    assert [sha(x) for x in checkpoints]==expected;inputs.update(checkpoints);models=[graph.FullGraphPair(str(p),'last').cpu().eval() for p in checkpoints];rows=[]
    with torch.inference_mode():
        for record in t['records']:
            rp=Path(record['rollout']['path']);assert sha(rp)==record['rollout']['sha256']==proof['input_sha256'][str(rp)];inputs.add(rp);raw=torch.load(rp,map_location='cpu',weights_only=False);obs=raw['samples'][:16];batch=graph.collate(obs,'cpu');dist=[distribution(m(*batch)[0],batch[-1]) for m in models]
            for i,cfg in enumerate(raw['configs']):
                original=proof['rows'][len(rows)];assert (original['update'],original['slot'],original['scenario'])==(record['update'],i,cfg['TRAIN_scenario_index'])
                row=dict(source_update=record['update'],slot=i,scenario=cfg['TRAIN_scenario_index'],role=cfg['role'],opponent=cfg['opponent'],family=cfg['family'],legal_actions=len(obs[i]['active_action_ids']),argmaxes=[int(d.probs[i].argmax()) for d in dist])
                for left,right,label in [(0,1,'parent_control'),(0,2,'parent_candidate'),(1,2,'control_candidate')]:
                    p=dist[left].probs[i];kl=torch.where(p>0,p*(dist[left].logits[i]-dist[right].logits[i]),0).sum();row[label]=dict(argmax_changed=row['argmaxes'][left]!=row['argmaxes'][right],KL=float(kl),total_variation=float((p-dist[right].probs[i]).abs().sum()/2))
                rows.append(row)
            del raw
            print(json.dumps(dict(fixed_TRAIN_replayed=len(rows))),flush=True)
    assert len(rows)==480
    summaries={label:dict(argmax_changes=sum(r[label]['argmax_changed'] for r in rows),KL=stat([r[label]['KL'] for r in rows]),total_variation=stat([r[label]['total_variation'] for r in rows])) for label in ['parent_control','parent_candidate','control_candidate']}
    groups=[]
    for role in ['attacker','defender']:
        for opponent in ['BattleAI','MMAI_MODEL']:
            selected=[r for r in rows if r['role']==role and r['opponent']==opponent];groups.append(dict(role=role,opponent=opponent,rows=len(selected),comparisons={label:dict(argmax_changes=sum(r[label]['argmax_changed'] for r in selected),mean_KL=float(np.mean([r[label]['KL'] for r in selected]))) for label in summaries}))
    return dict(scope='Same pre-fixed first16 graphs from each original30 TRAIN rollouts,60 cases; no continuation/DEV-based selection',rows=rows,comparisons=summaries,groups=groups)
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);torch.set_num_threads(1);start=time.monotonic();inputs={Path(__file__),R/'masked_ppo.py',R/'full_graph_policy.py',OLD/'curriculum.py'}
    reports,rows=rollouts(inputs);(a.out/'ROLLOUT_CREDIT.json').write_text(json.dumps(dict(passed=True,arms=reports,common_updates=[31,57],rows_per_arm=13824,GAE_gamma=1.,GAE_lambda=.95,GAE_resets_each32step_rollout=True,window_end_not_phase_close=True),indent=2)+'\n')
    probe=replay(inputs);(a.out/'FIXED480_REPLAY.json').write_text(json.dumps(dict(passed=True,**probe),indent=2)+'\n')
    (a.out/'AUDIT.json').write_text(json.dumps(dict(passed=True,common_updates=list(range(31,58)),common_rows_per_arm=13824,fixed_TRAIN_graphs=480,new_native_games=0,GPU_operations=0,optimizer_steps=0,resource_locks_taken=False,input_sha256={str(p):sha(p) for p in sorted(inputs)},elapsed_seconds=time.monotonic()-start),indent=2)+'\n')
if __name__=='__main__':main()
