"""Read-only CPU replay of sealed TRAIN. No DEV, optimizer, native or resource locks."""
import argparse,collections,hashlib,json,math,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
POLICY=ROOT/'experiments/strategic-learned-recruitment-policy-v3'
RUN=ROOT/'experiments/strategic-learned-recruitment-run-v2'
sys.path.insert(0,str(RUN));sys.path.insert(0,str(POLICY))
import torch
import encoder
from load_admitted import load
from model_io import load_model,tensor_sha,architecture
from episode_balanced_ppo import prepare_batch
from pipeline_common import validate_cells,sha
OPS=('move','end_turn','build','recruit')
def dump(p,value):p.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
def stock_band(n):return '1' if n==1 else '2..9' if n<10 else '10..49' if n<50 else '50+'
def summary(values):
    values=sorted(values)
    return None if not values else dict(n=len(values),mean=sum(values)/len(values),minimum=values[0],median=values[len(values)//2],maximum=values[-1])
def pooled(rows):
    if not rows:return dict(rows=0)
    opportunities=[r for r in rows if r['recruit_candidate_count']]
    actor_mass=sum(r['actor_weight'] for r in rows)
    return dict(rows=len(rows),recruit_opportunity_rows=len(opportunities),
        episode_choice_weighted_initial_op_probability={op:sum(r['actor_weight']*r['initial_op_probability'][op] for r in rows)/actor_mass if actor_mass else None for op in OPS},
        episode_choice_weighted_updated_op_probability={op:sum(r['actor_weight']*r['updated_op_probability'][op] for r in rows)/actor_mass if actor_mass else None for op in OPS},
        initial_argmax_ops=dict(collections.Counter(r['initial_argmax_op'] for r in rows)),updated_argmax_ops=dict(collections.Counter(r['updated_argmax_op'] for r in rows)),
        action_changes=sum(r['initial_argmax_index']!=r['updated_argmax_index'] for r in rows),
        initial_recruit_probability=summary([r['initial_op_probability']['recruit'] for r in opportunities]),
        updated_recruit_probability=summary([r['updated_op_probability']['recruit'] for r in opportunities]),
        recruit_probability_delta=summary([r['updated_op_probability']['recruit']-r['initial_op_probability']['recruit'] for r in opportunities]),
        initial_recruit_margin=summary([r['initial_recruit_margin'] for r in opportunities]),updated_recruit_margin=summary([r['updated_recruit_margin'] for r in opportunities]),
        minus_four_recruit_probability=summary([r['minus_four_op_probability']['recruit'] for r in opportunities]),minus_four_recruit_margin=summary([r['minus_four_recruit_margin'] for r in opportunities]),
        episode_choice_weighted_minus_four_op_probability={op:sum(r['actor_weight']*r['minus_four_op_probability'][op] for r in rows)/actor_mass if actor_mass else None for op in OPS},
        minus_four_argmax_ops=dict(collections.Counter(r['minus_four_argmax_op'] for r in rows)),manual_prior_argmax_changes=sum(r['minus_four_argmax_index']!=r['initial_argmax_index'] for r in rows),
        fixed_initial_best_pair_margin_shift=summary([r['fixed_initial_best_pair_margin_shift'] for r in opportunities]),
        fixed_pair_recruit_residual_margin_shift=summary([r['fixed_pair_recruit_residual_margin_shift'] for r in opportunities]),
        selected_recruit_rows=sum(r['selected_op']=='recruit' for r in rows),
        selected_raw_advantage=summary([r['raw_advantage'] for r in rows]),selected_normalized_advantage=summary([r['normalized_advantage'] for r in rows]),
        negative_selected_advantages=sum(r['normalized_advantage']<0 for r in rows),positive_selected_advantages=sum(r['normalized_advantage']>0 for r in rows),
        weighted_selected_advantage_sum=sum(r['actor_weight']*r['normalized_advantage'] for r in rows))
def main():
    p=argparse.ArgumentParser();p.add_argument('--train',type=Path,required=True);p.add_argument('--initial',type=Path,required=True);p.add_argument('--candidate',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--minus-four-initial',type=Path,default=ROOT/'experiments/strategic-learned-recruitment-policy-v2/initialization-01/recruitment-initialization.pt')
    a=p.parse_args();assert not a.out.exists(),'Preserve prior diagnostics'
    torch.set_num_threads(1);torch.use_deterministic_algorithms(True)
    initial,ib,isha=load_model(a.initial,'cpu');updated,ub,usha=load_model(a.candidate,'cpu')
    minus_four_sha=sha(a.minus_four_initial)
    assert minus_four_sha=='b9ede0d158d113eff42d58cb8a844277b42e8a0820122d985299dfcf9cdb7b79'
    old_bundle=torch.load(a.minus_four_initial,map_location='cpu',weights_only=True)
    assert [name for name in ib['state_dict'] if not torch.equal(ib['state_dict'][name],old_bundle['state_dict'][name])]==['actor.recruit_bias']
    assert float(ib['state_dict']['actor.recruit_bias'])==0. and float(old_bundle['state_dict']['actor.recruit_bias'])==-4.
    minus_four=architecture.PriorCandidateActorCritic(old_bundle['hidden'],**old_bundle['prior_config']);minus_four.load_state_dict(old_bundle['state_dict'],strict=True);minus_four.eval()
    assert ub['training_updates']==1 and ub['parent_checkpoint_sha256']==isha and ib['catalog_sha256']==ub['catalog_sha256']
    assert all(sha(path)==h for path,h in ub['protocol']['sources'].items())
    samples=[];episodes=[];admissions=[]
    for cell in sorted(a.train.glob('cell-*')):
        rows,manifest,admission=load(cell/'admitted');samples.extend(rows);episodes.extend(manifest);admissions.append(admission)
    validate_cells(episodes)
    assert all(e['checkpoint_sha256']==isha and e['job']['logical_update']==0 for e in episodes)
    prepared=prepare_batch(samples,'cpu',episodes=episodes)
    jobs={e['episode_id']:e['job'] for e in episodes}
    rows=[];bucket_groups={};cpu_logprob_error=[];cpu_value_error=[]
    initial_bias=float(initial.actor.recruit_bias.detach());updated_bias=float(updated.actor.recruit_bias.detach())
    initial_parameters=tensor_sha(initial.state_dict());updated_parameters=tensor_sha(updated.state_dict());minus_four_parameters=tensor_sha(minus_four.state_dict())
    for offset in range(0,len(samples),64):
        block=samples[offset:offset+64];batch=encoder.collate([s['request'] for s in block],'cpu')
        with torch.no_grad():iz,iv=initial(**batch);uz,uv=updated(**batch);mz,mv=minus_four(**batch)
        assert torch.equal(iv,mv),'Initial critics must match for pure bias contrast'
        for local,sample in enumerate(block):
            index=offset+local;q=sample['request'];candidates=q['candidates'];count=len(candidates);i=iz[local,:count];u=uz[local,:count];m=mz[local,:count]
            ip=i.softmax(-1);up=u.softmax(-1);mp=m.softmax(-1);action=sample['action'];selected=candidates[action]
            recruit=[j for j,c in enumerate(candidates) if c['op']=='recruit'];other=[j for j,c in enumerate(candidates) if c['op']!='recruit']
            assert other
            assert torch.equal(i[other],m[other])
            if recruit:assert bool(((i[recruit]-m[recruit])-4.).abs().le(2e-6).all())
            reset=u.clone()
            if recruit:reset[recruit]+=initial_bias-updated_bias
            rp=reset.softmax(-1)
            fixed_recruit=recruit[int(i[recruit].argmax())] if recruit else None
            fixed_other=other[int(i[other].argmax())]
            residual_change=0.
            if recruit:
                extra=batch['candidates'][local,fixed_recruit,43:]
                with torch.no_grad():residual_change=float(updated.recruit_actor(extra)-initial.recruit_actor(extra))
            byop=lambda probabilities:{op:sum(float(probabilities[j]) for j,c in enumerate(candidates) if c['op']==op) for op in OPS}
            iarg=int(i.argmax());uarg=int(u.argmax());marg=int(m.argmax())
            cpu_logprob_error.append(abs(float(i.log_softmax(-1)[action])-sample['old_logprob']))
            cpu_value_error.append(abs(float(iv[local])-sample['old_value']))
            at=[t['town_id'] for t in q['own_towns'] if t['position']==q['from']]
            visiting=[t['town_id'] for t in q['own_towns'] if t['recruit_state']['visitor'] is not None and t['recruit_state']['visitor']['hero_id']==q['hero'] and t['recruit_state']['visitor']['owner']==q['player']]
            reinforce=[j for j,c in enumerate(candidates) if c['op']=='move' and c['kind']==4]
            row=dict(episode_id=sample['episode_id'],decision_id=q['request_id'],opponent=jobs[sample['episode_id']]['opponent'],map=jobs[sample['episode_id']]['map'],
                player=q['player'],own_turn=q['own_turn'],day=q['day'],hero_army_value=q['own_army_value'],from_position=q['from'],at_owned_towns=at,actual_visiting_owned_towns=visiting,
                resources=q['resources'],return_value=sample['return'],selected_op=selected['op'],selected_candidate=selected,
                selected_move_kind=selected.get('kind'),raw_advantage=sample['return']-sample['old_value'],normalized_advantage=float(prepared['advantages'][index]),actor_weight=float(prepared['actor_weights'][index]),
                minus_four_initial_value=float(mv[local]),minus_four_op_probability=byop(mp),minus_four_argmax_op=candidates[marg]['op'],minus_four_argmax_index=marg,
                minus_four_recruit_margin=float(m[recruit].max()-m[other].max()) if recruit else None,
                initial_value=float(iv[local]),updated_value=float(uv[local]),initial_op_probability=byop(ip),updated_op_probability=byop(up),
                initial_argmax_index=iarg,updated_argmax_index=uarg,initial_argmax_op=candidates[iarg]['op'],updated_argmax_op=candidates[uarg]['op'],
                initial_argmax_candidate=candidates[iarg],updated_argmax_candidate=candidates[uarg],recruit_candidate_count=len(recruit),
                initial_recruit_margin=float(i[recruit].max()-i[other].max()) if recruit else None,updated_recruit_margin=float(u[recruit].max()-u[other].max()) if recruit else None,
                updated_reset_bias_to_initial_recruit_probability=sum(float(rp[j]) for j in recruit),
                fixed_initial_best_pair_margin_shift=float((u[fixed_recruit]-u[fixed_other])-(i[fixed_recruit]-i[fixed_other])) if recruit else None,
                fixed_pair_recruit_bias_margin_shift=updated_bias-initial_bias if recruit else None,fixed_pair_recruit_residual_margin_shift=residual_change if recruit else None,
                minus_four_reinforce_probability=sum(float(mp[j]) for j in reinforce),initial_reinforce_probability=sum(float(ip[j]) for j in reinforce),updated_reinforce_probability=sum(float(up[j]) for j in reinforce))
            rows.append(row)
            for j in recruit:
                c=candidates[j];key=(row['opponent'],stock_band(c['available']),c['quantity_bucket'])
                g=bucket_groups.setdefault(key,dict(candidate_occurrences=0,minus_four_probability_mass_sum=0.,initial_probability_mass_sum=0.,updated_probability_mass_sum=0.,selected_count=0,selected_positive=0,selected_negative=0,selected_weighted_advantage_sum=0.,creatures_recruited=0,resource_spend={r:0 for r in encoder.RESOURCES}))
                g['candidate_occurrences']+=1;g['minus_four_probability_mass_sum']+=float(mp[j]);g['initial_probability_mass_sum']+=float(ip[j]);g['updated_probability_mass_sum']+=float(up[j])
                if j==action:
                    g['selected_count']+=1;g['selected_positive']+=int(row['normalized_advantage']>0);g['selected_negative']+=int(row['normalized_advantage']<0)
                    g['selected_weighted_advantage_sum']+=row['actor_weight']*row['normalized_advantage'];g['creatures_recruited']+=c['amount']
                    for r in encoder.RESOURCES:g['resource_spend'][r]+=c['cost'][r]
    episode_reports=[]
    for episode in episodes:
        erows=[r for r in rows if r['episode_id']==episode['episode_id']]
        native=json.loads(Path(episode['raw_audit_path']).read_text());raw=Path(native['raw'])
        events=[json.loads(x) for x in (raw/'typed.jsonl').read_text().splitlines()]
        selected=[r for r in erows if r['selected_op']=='recruit']
        transfers=[e for e in events if e['event']=='free_transfer_native_sent'];assert len(transfers)==native['actual_transfers_checked']
        byday=collections.defaultdict(list)
        for r in erows:
            if r['at_owned_towns']:byday[r['day']].append(r)
        first=erows[0];last=erows[-1]
        episode_reports.append(dict(episode_id=episode['episode_id'],job=episode['job'],terminal_return=episode['reward'],decisions=len(erows),
            recruit_transactions=[dict(decision_id=r['decision_id'],day=r['day'],own_turn=r['own_turn'],candidate=r['selected_candidate'],raw_advantage=r['raw_advantage'],normalized_advantage=r['normalized_advantage']) for r in selected],
            actual_free_transfers=[dict(native_request_id=e['native_request_id'],town_id=e['before_state']['town_id'],source_army_id=e['source_army_id'],target_army_id=e['target_army_id'],creature_id=e['creature_id'],amount=e['amount']) for e in transfers],
            free_transfer_transactions=len(transfers),transferred_creatures=sum(e['amount'] for e in transfers),
            at_owned_town_observed_days=sorted(byday),selected_reinforce_moves=sum(r['selected_op']=='move' and r['selected_move_kind']==4 for r in erows),
            actual_owned_town_visiting_observed_days=sorted(set(r['day'] for r in erows if r['actual_visiting_owned_towns'])),
            initial_reinforce_probability_mean=sum(r['initial_reinforce_probability'] for r in erows)/len(erows),updated_reinforce_probability_mean=sum(r['updated_reinforce_probability'] for r in erows)/len(erows),
            first_observed_hero_army_value=first['hero_army_value'],last_observed_hero_army_value=last['hero_army_value'],first_observed_resources=first['resources'],last_observed_resources=last['resources'],
            limitation='Town observations and reinforce moves do not alone prove replenishment; actual free-transfer deltas are reported separately. Last request is not terminal full-world state.'))
    aggregate=dict(model_roles=dict(minus_four='frozen -4 initialization, manual sensitivity only',initial='zero-prior initialization that generated the new TRAIN rollouts',updated='its own first actual PPO update'),
        support='Only new zero-prior sealed TRAIN states; previous 3952-state dataset is not read',all_rows=pooled(rows),by_opponent={o:pooled([r for r in rows if r['opponent']==o]) for o in ('EmptyAI','Nullkiller2')},
        by_opponent_selected_op={o+'/'+op:pooled([r for r in rows if r['opponent']==o and r['selected_op']==op]) for o in ('EmptyAI','Nullkiller2') for op in OPS},
        by_outcome={str(outcome):pooled([r for r in rows if r['return_value']==outcome]) for outcome in (-1.,1.)},
        by_recruit_stock_quantity=[dict(opponent=k[0],available_stock_band=k[1],quantity_bucket=k[2],**v) for k,v in sorted(bucket_groups.items())])
    assert initial_parameters==tensor_sha(initial.state_dict()) and updated_parameters==tensor_sha(updated.state_dict()) and minus_four_parameters==tensor_sha(minus_four.state_dict())
    assert all(sha(path)==h for path,h in ub['protocol']['sources'].items())
    a.out.mkdir(parents=True,exist_ok=False)
    (a.out/'REQUEST_COMPARISON.jsonl').write_text(''.join(json.dumps(r,separators=(',',':'),allow_nan=False)+'\n' for r in rows))
    dump(a.out/'AGGREGATES.json',aggregate);dump(a.out/'EPISODES.json',episode_reports)
    audit=dict(passed=True,CPU_only=True,train_rows=len(rows),episodes=len(episodes),initial_sha256=isha,candidate_sha256=usha,minus_four_initial_sha256=minus_four_sha,observation_support='Only this complete prior-zero TRAIN rollout distribution; never compare its state mean directly with old 3952-state means as a pure model effect',
        initial_recruit_bias=initial_bias,updated_recruit_bias=updated_bias,cpu_vs_certified_CUDA_logprob_absolute_error=summary(cpu_logprob_error),cpu_vs_certified_CUDA_value_absolute_error=summary(cpu_value_error),previous_TRAIN_observations_read=False,
        normalized_advantage_protocol=prepared['metadata'],GPU_steps=0,optimizer_steps=0,native_runs=0,locks_acquired=False,DEV_read=False,
        logits_bias_sensitivity_scope='Frozen minus4 init versus zero init on identical new zero-rollout observations differs only by manual bias. Zero init versus zero update on those same observations measures learned model change. Neither establishes independent ability; old/new rollout state means are different supports.',
        interpretation_limits=['Only observed fixed TRAIN state support; no independent ability claim.','Advantages arise from terminal outcome plus stored critic and episode-normalization; correlation does not identify an individual action causal effect.','Initial manual bias effect on probabilities is calculable; it is not alone evidence of the cause of training outcome.','Unselected candidate opportunity rows have no demonstrated action success or per-candidate advantage label.'],
        input_sha256={str(a.minus_four_initial):minus_four_sha,str(a.initial):isha,str(a.candidate):usha,str(Path(__file__)):sha(__file__),**{str(Path(e['raw_audit_path'])):sha(e['raw_audit_path']) for e in episodes}},
        output_sha256={name:sha(a.out/name) for name in ('REQUEST_COMPARISON.jsonl','AGGREGATES.json','EPISODES.json')})
    dump(a.out/'AUDIT.json',audit)
    report=f"""# Prior-zero TRAIN same-observation learning diagnosis\n\nRead-only replay of {len(rows)} sealed observations from all 8 TRAIN cells. No DEV, native game, GPU use or optimizer step.\n\nInitial recruit bias {initial_bias:.9g}; updated {updated_bias:.9g}. See AGGREGATES.json for the same-observation op/argmax/margin and stock/bucket strata; EPISODES.json records actual recruited and transferred amounts separately from town/reinforce observations.\n\nFrozen minus4 init, zero init and zero updated models are replayed on this single new TRAIN support. Minus4 to zero init measures manual-prior sensitivity; zero init to zero update measures model changes on the same states. Old 3952-state means and new state means cannot be directly subtracted as a pure model effect. No previous DEV evidence is read. Terminal advantages are episode-balanced and cannot prove that an individual earlier recruitment, town visit or economic decision caused the result. TRAIN successes are not independent strength evidence.\n"""
    (a.out/'REPORT.md').write_text(report)
    print(json.dumps(dict(passed=True,rows=len(rows),episodes=8,initial_recruit_bias=initial_bias,updated_recruit_bias=updated_bias,aggregate=aggregate['all_rows']),indent=2))
if __name__=='__main__':main()
