"""CPU-only synthetic syntax + frozen TRAIN movement migration audit. No optimizer."""
import argparse,copy,hashlib,importlib.util,json,sys
from pathlib import Path
import torch
import encoder,model_io
from migrate import migrate,PARENT
HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def fixture():
    return dict(schema=encoder.SCHEMA,economy_epoch=encoder.EPOCH,economy_window_open=True,
        request_id=1,player=0,hero=0,own_turn=1,own_hero_count=1,day=1,gold=10000,wood=10,ore=10,
        resources=dict(wood=10,mercury=0,ore=10,sulfur=0,crystal=0,gems=0,gold=10000),
        own_army_value=1000,movement=1500,**{'from':[1,1,0]},visible_threats=[],
        own_towns=[dict(town_id=3,faction_id=0,built_today=0,buildings=[0],position=[1,2,0],army_value=0)],
        candidates=[dict(op='move',kind=5,position=[8,8,0],next=[2,2,0],path_cost=1.,heuristic_score=4.),
                    dict(op='end_turn'),dict(op='build',actor='player_town',town_id=3,building_id=11,category='income',
                    cost=dict(wood=0,mercury=0,ore=0,sulfur=0,crystal=0,gems=0,gold=2500))])
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False,parents=True)
    torch.set_num_threads(1);old,new,bundle=migrate()
    target=a.out/'build-initialization.pt';initial_sha=model_io.save_initialization(bundle,target)
    loaded,_,loaded_sha=model_io.load_model(target)
    assert initial_sha==loaded_sha and model_io.tensor_sha(loaded.state_dict())==model_io.tensor_sha(new.state_dict())
    good=fixture();batch=encoder.collate([good]);logits,value=new(**batch);prob=logits.softmax(-1)
    losses=-torch.log_softmax(logits,-1)[0,2];new.zero_grad();losses.backward()
    assert new.actor[0].weight.grad[:,35+23:35+40].abs().sum()>0
    assert new.actor[0].weight.grad[:,35+42].abs().sum()>0
    gradients=dict(build_economy_columns_l1=float(new.actor[0].weight.grad[:,58:75].abs().sum()),
        build_op_column_l1=float(new.actor[0].weight.grad[:,77].abs().sum()))
    new.zero_grad();rejects=[]
    def reject(label,change):
        bad=copy.deepcopy(good);change(bad)
        try:encoder.encode(bad)
        except (ValueError,TypeError):rejects.append(label);return
        raise AssertionError('Accepted '+label)
    reject('old_schema',lambda r:r.update(schema='strategy-candidates-v4'))
    reject('wrong_epoch',lambda r:r.update(economy_epoch='other'))
    reject('missing_resource',lambda r:r['resources'].pop('mercury'))
    reject('extra_resource',lambda r:r['resources'].update(mithril=0))
    reject('NaN_resource',lambda r:r['resources'].update(gems=float('nan')))
    reject('bool_resource',lambda r:r['resources'].update(gems=True))
    reject('fractional_cost',lambda r:r['candidates'][2]['cost'].update(gold=1.5))
    reject('negative_cost',lambda r:r['candidates'][2]['cost'].update(wood=-1))
    reject('unaffordable_cost',lambda r:r['candidates'][2]['cost'].update(gold=10001))
    reject('unknown_town',lambda r:r['candidates'][2].update(town_id=99))
    reject('hero_actor',lambda r:r['candidates'][2].update(actor='hero'))
    reject('fake_build_coordinates',lambda r:r['candidates'][2].update(position=[1,2,0]))
    reject('already_built',lambda r:r['own_towns'][0]['buildings'].append(11))
    reject('daily_limit',lambda r:r['own_towns'][0].update(built_today=1))
    reject('closed_window',lambda r:r.update(economy_window_open=False))
    reject('bad_category',lambda r:r['candidates'][2].update(category='grail'))
    reject('duplicate_build',lambda r:r['candidates'].append(copy.deepcopy(r['candidates'][2])))
    reject('duplicate_town',lambda r:r['own_towns'].append(copy.deepcopy(r['own_towns'][0])))
    reject('unsorted_buildings',lambda r:r['own_towns'][0].update(buildings=[1,0]))
    reject('alias_mismatch',lambda r:r.update(gold=1))
    reject('wrong_op',lambda r:r['candidates'][2].update(op='recruit'))
    reject('NaN_move',lambda r:r['candidates'][0].update(path_cost=float('nan')))
    # Model rejects tensor contamination independently of JSON validation.
    for label,index,value in [('non_onehot',40,1.),('build_move_payload',0,1.),('negative_cost_tensor',23,-1.),('invalid_category',37,.5)]:
        bad={k:v.clone() for k,v in batch.items()};bad['candidates'][0,2,index]=value
        try:new(**bad)
        except ValueError:rejects.append(label)
        else:raise AssertionError('Model accepted '+label)
    # Complete genuine old TRAIN requests, projected into new epoch for migration only.
    _spec=importlib.util.spec_from_file_location('_cpu_old_train_admission',HERE.parent/'strategic-typed-training-v1/load_admitted.py')
    _loader=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(_loader);load=_loader.load
    sealed=HERE.parent/'strategic-typed-training-v1/balanced-ack-certified-01/RESULT.json'
    entries=json.loads(sealed.read_text())['episodes'];count=0;logit_error=0.;value_error=0.;synthetic_probs=[]
    with torch.no_grad():
        for entry in entries:
            samples,_,_=load(entry['admission'])
            for sample in samples:
                r=sample['request'];project=copy.deepcopy(r)
                project.update(schema=encoder.SCHEMA,economy_epoch=encoder.EPOCH,economy_window_open=True,
                    resources=dict(wood=r['wood'],mercury=0,ore=r['ore'],sulfur=0,crystal=0,gems=0,gold=r['gold']))
                for tid,town in enumerate(project['own_towns']):town.update(town_id=tid,faction_id=0,built_today=0,buildings=[])
                before,bv=old(**encoder.legacy.collate([r]));after,av=new(**encoder.collate([project]))
                logit_error=max(logit_error,float((before-after).abs().max()));value_error=max(value_error,float((bv-av).abs().max()))
                assert before.argmax(-1).item()==after.argmax(-1).item()
                if project['own_towns'] and r['gold']>=2500:
                    build=copy.deepcopy(good['candidates'][2]);build['town_id']=0;project['candidates'].append(build)
                    bb=encoder.collate([project]);bl,_=new(**bb);synthetic_probs.append(float(bl.softmax(-1)[0,-1]))
                    bb['mask'][0,-1]=False;ml,mv=new(**bb)
                    logit_error=max(logit_error,float((before-ml[:,:-1]).abs().max()));value_error=max(value_error,float((bv-mv).abs().max()))
                count+=1
    assert count==2588 and logit_error<1e-5 and value_error<1e-5
    probs=sorted(synthetic_probs)
    report=dict(passed=True,cpu_only=True,native_games=0,gpu_steps=0,optimizer_steps=0,
        parent_sha256=sha(PARENT),initialization_sha256=initial_sha,contract_sha256=model_io.CONTRACT_SHA256,
        state_dim=35,candidate_dim=43,rejection_checks=rejects,gradient_checks=gradients,
        frozen_train_movement_requests_checked=count,masked_build_logit_max_error=logit_error,masked_build_critic_max_error=value_error,
        synthetic_fixture_build_probability=float(prob[0,2]),
        synthetic_build_risk_probe=dict(count=len(probs),minimum=min(probs),median=probs[len(probs)//2],maximum=max(probs),
            below_1e_6=sum(x<1e-6 for x in probs),below_1e_3=sum(x<1e-3 for x in probs),
            scope='Synthetic 2500gold build appended to old TRAIN facts; missing resource/town metadata are explicit fixtures. NOT native legality/frequency qualification.'),
        input_sha256={str(p):sha(p) for p in [PARENT,sealed,HERE.parent/'strategic-learned-economy-native-v1/CONTRACT.md',encoder.LEGACY_PATH]},
        source_sha256={p.name:sha(p) for p in HERE.glob('*.py')},ability_improvement_claim=False)
    assert sha(HERE.parent/'strategic-learned-economy-native-v1/CONTRACT.md')==model_io.CONTRACT_SHA256
    (a.out/'AUDIT.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
