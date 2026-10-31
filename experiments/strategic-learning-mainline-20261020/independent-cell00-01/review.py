"""CPU-only read-only check of completed cell00 while the batch continues."""
import collections,hashlib,json,statistics,sys
from pathlib import Path
import torch
OUT=Path(__file__).resolve().parent;HERE=OUT.parent;TRAIN=HERE.parent/'strategic-typed-training-v1';PIPE=HERE/'native-pipeline'
sys.path.insert(0,str(TRAIN));sys.path.insert(0,str(PIPE))
from load_admitted import load
from model_io import load_model
from episode_balanced_ppo import collate
from pipeline_common import EPOCH,INITIAL_SHA,validate_native_epoch
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    torch.set_num_threads(1);batch=Path('/root/heroes3-ai-lab/evaluations/strategic-mainline-temperature2-train-01');root=batch/'cell-00/native'
    samples,episodes,admission=load(batch/'cell-00/admitted');episode=episodes[0]
    plan=json.loads((root/'PLAN.json').read_text());execution=json.loads((root/'EXECUTION.json').read_text());proof=json.loads((OUT/'raw-audit/AUDIT.json').read_text());batch_plan=json.loads((batch/'PLAN.json').read_text())
    assert plan['pipeline_epoch']==execution['pipeline_epoch']==batch_plan['epoch']==EPOCH
    assert all(sha(Path(p))==h for p,h in batch_plan['input_sha256'].items());validate_native_epoch(proof,plan,execution)
    assert episode['checkpoint_sha256']==plan['hashes'][plan['checkpoint']]==INITIAL_SHA
    assert episode['job']['map']=='takeover-v2-train-01-mines' and episode['job']['owned_player']==0 and episode['job']['opponent']=='EmptyAI' and episode['job']['seed']==2026102000
    assert proof['whole_game_valid'] and execution['client_exit']==0 and admission['optimizer_steps']==0
    model,_,digest=load_model(plan['checkpoint'],'cpu');assert digest==INITIAL_SHA
    totals=collections.Counter();groups={k:dict(rows=0,stops=0,non_argmax=0,stop_probability=[],entropy=[]) for k in ['one_move','multiple_moves','no_move']};errors=[];turns=collections.defaultdict(collections.Counter);movement_at_stop=[]
    with torch.no_grad():
        for row in samples:
            q=row['request'];moves=[i for i,c in enumerate(q['candidates']) if c['op']=='move'];stop=[i for i,c in enumerate(q['candidates']) if c['op']=='end_turn'];assert len(stop)==1
            key='no_move' if not moves else 'one_move' if len(moves)==1 else 'multiple_moves';group=groups[key]
            logits,_=model(**collate([q],'cpu'));logits=logits[0].double();logp=logits.log_softmax(0);p=logp.exp();action=row['action'];is_stop=q['candidates'][action]['op']=='end_turn'
            errors.append(abs(float(logp[action])-row['old_logprob']));group['rows']+=1;group['stops']+=is_stop;group['non_argmax']+=action!=int(logits.argmax());group['stop_probability'].append(float(p[stop[0]]));group['entropy'].append(float(-(p*logp).sum()))
            totals['stops' if is_stop else 'moves']+=1;turns[q['own_turn']]['stops' if is_stop else 'moves']+=1
            if is_stop:movement_at_stop.append(q['movement'])
    assert len(samples)==811 and totals['moves']==752 and totals['stops']==59 and max(errors)<1e-4
    trace=[json.loads(s) for s in (root/'strategy-trace.jsonl').read_text().splitlines()];terminal=[e for e in trace if e['event'] in ['victory','defeat']];assert len(terminal)==1
    typed=[json.loads(s) for s in (root/'typed.jsonl').read_text().splitlines()];auto=[e for e in typed if e['event']=='native_action_sent' and e.get('decision_id') is None];auto_reasons=collections.Counter(e.get('automatic_reason') for e in auto)
    for group in groups.values():
        for field in ['stop_probability','entropy']:
            values=group.pop(field);group[field+'_summary']=dict(mean=statistics.mean(values),median=statistics.median(values),min=min(values),max=max(values)) if values else None
    logical_turns=max(turns);assert logical_turns==terminal[0]['own_turn']==len(auto)+totals['stops']+1
    original_proof=json.loads((batch/'cell-00/raw-audit/AUDIT.json').read_text());assert original_proof==proof
    paths=[Path(__file__),root/'PLAN.json',root/'EXECUTION.json',root/'client.log',root/'typed.jsonl',root/'strategy-trace.jsonl',batch/'cell-00/raw-audit/AUDIT.json',batch/'cell-00/admitted/AUDIT.json',batch/'cell-00/admitted/episode.json',batch/'cell-00/admitted/samples.jsonl',OUT/'raw-audit/AUDIT.json',batch/'PLAN.json']
    result=dict(passed=True,scope='Completed TRAIN cell00 only; CPU/source/native re-audit, no new CUDA replay or optimization',new_native_games=0,GPU_operations=0,optimizer_steps_performed=0,policy_sha256=digest,
        native_winner=proof['winner'],terminal_day=terminal[0]['day'],own_turns=logical_turns,counts=dict(totals),opportunity_groups=groups,automatic_end_turns=len(auto),automatic_reasons=dict(auto_reasons),
        stop_observed_fraction=totals['stops']/len(samples),all_policy_stops_had_positive_movement=min(movement_at_stop)>0,movement_at_stop_summary=dict(min=min(movement_at_stop),median=statistics.median(movement_at_stop),max=max(movement_at_stop)),
        sampled_logprob_max_abs_CPU_error=max(errors),CUDA_exact_replay_report_verified=True,CUDA_replay_independently_rerun=False,
        native_execution_independently_reaudited=True,owned_register_count=proof['director_registry_proof']['registered_count'],owned_ACK_count=proof['director_registry_proof']['actual_director_ack_count'],
        actual_foreign_atomic_cleared_ids=proof['director_registry_proof']['actual_atomic_cleared_ids'],per_turn_policy_counts={str(k):dict(v) for k,v in turns.items()},
        input_sha256={str(p):sha(p) for p in paths},ability_improvement_claim=False,
        limitation='One EmptyAI TRAIN win and a changed stochastic trajectory do not establish learned waiting, improved strength or temperature benefit. Historical cell has a different seed; do not treat it as a paired control.')
    (OUT/'AUDIT.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k not in ['input_sha256','per_turn_policy_counts']},indent=2))
if __name__=='__main__':main()
