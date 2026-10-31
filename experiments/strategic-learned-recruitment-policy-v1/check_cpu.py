"""Draft-only CPU migration/feature checks. No saved model, optimizer update or game."""
import argparse,copy,hashlib,importlib.util,json,sys
from pathlib import Path
import torch
import encoder,model
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'strategic-learned-free-transfer-policy-v1'))

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def enrich(q):
    q=copy.deepcopy(q);q['schema']=encoder.SCHEMA;q['economy_epoch']=encoder.EPOCH;q['creature_catalog_sha256']='0'*64
    for t in q['own_towns']:
        t['recruit_state']=dict(town_id=t['town_id'],owner=q['player'],built_today=t['built_today'],resources=copy.deepcopy(q['resources']),
            upper_army_id=t['town_id'],upper_army=[None]*7,visitor=None,recruit_stock=[dict(level=0,available=10,creature_ids=[42])])
    return q

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    torch.set_num_threads(1)
    io=module('_recruit_cpu_parent_io',HERE.parent/'strategic-learned-free-transfer-policy-v1/model_io.py')
    old,bundle,digest=io.load_model(HERE.parent/'strategic-learned-free-transfer-policy-v1/initialization-01/free-transfer-initialization.pt','cpu')
    assert digest=='83319be8bde5d94eea839b1a889821449a7c1492c65da7ca6cde2deb63aab25a'
    new=model.migrate_weights_only(old)
    # Actual TRAIN observations gain explicitly constructed recruit_state fixtures;
    # this verifies projection only, not native legality of those added facts.
    sys.modules['encoder']=encoder.old
    loader=module('_recruit_cpu_old_admission',HERE.parent/'strategic-learned-free-transfer-policy-v1/load_admitted.py')
    rows,_,_=loader.load(Path('/root/heroes3-ai-lab/evaluations/strategic-learned-free-transfer-train-01/cell-00/admitted'))
    sys.modules['encoder']=encoder
    chosen=[rows[0]['request']]
    chosen += [r['request'] for r in rows if any(c['op']=='build' for c in r['request']['candidates'])][:3]
    for original in chosen:
        q=enrich(original);b=encoder.collate([q]);oldbatch=encoder.old.collate([original])
        assert torch.equal(b['state'],oldbatch['state']) and torch.equal(b['candidates'][...,:43],oldbatch['candidates'])
        with torch.no_grad():
            x,v=old(**oldbatch);y,w=new(**b)
        assert torch.equal(x,y) and torch.equal(v,w) and torch.equal(torch.softmax(x,-1),torch.softmax(y,-1))
    q=enrich(chosen[0]);q['economy_window_open']=True
    t=q['own_towns'][0];t['recruit_state']['resources']=copy.deepcopy(q['resources'])
    candidate=dict(op='recruit',actor='player_town',town_id=t['town_id'],destination_army_id=t['town_id'],destination_role='town',
        creature_id=42,amount=1,level=0,destination_slot=0,quantity_bucket='one',available=10,affordable=10,cost={r:0 for r in encoder.RESOURCES})
    q['candidates'].append(candidate)
    batch=encoder.collate([q]);logits,value=new(**batch);loss=-torch.log_softmax(logits,-1)[0,-1]+value.sum();loss.backward()
    gradients={k:float(dict(new.named_parameters())[k].grad.abs().sum()) for k in ('actor.recruit_bias','recruit_actor.weight','recruit_critic.weight')}
    assert all(v>0 for v in gradients.values())
    optimizer=torch.optim.Adam(new.parameters(),lr=3e-4);assert not optimizer.state
    negatives=[]
    mutations=dict(oldschema=lambda x:x.update(schema='strategy-candidates-v5'),badop=lambda x:x['candidates'][-1].update(op='dance'),
        wrongdestination=lambda x:x['candidates'][-1].update(destination_army_id=999999),wrongstock=lambda x:x['candidates'][-1].update(available=9),
        wrongbucket=lambda x:x['candidates'][-1].update(quantity_bucket='half'),closedwindow=lambda x:x.update(economy_window_open=False),
        extraresponsefield=lambda x:x['candidates'][-1].update(position=[0,0,0]),badamount=lambda x:x['candidates'][-1].update(amount=float('nan')),
        occupiedslot=lambda x:x['own_towns'][0]['recruit_state']['upper_army'].__setitem__(0,dict(slot=0,creature_id=99,count=1)))
    for name,fn in mutations.items():
        bad=copy.deepcopy(q);fn(bad)
        try:encoder.validate(bad)
        except (ValueError,TypeError):negatives.append(name)
        else:raise AssertionError('Accepted '+name)
    raw=json.dumps(dict(schema='strategy-runtime-creature-catalog-v1',entries=[dict(creature_id=42,canonical_key='core:fixture')])).encode()
    catalogpath=a.out/'SYNTHETIC_catalog.json';catalogpath.write_bytes(raw)
    catalog=encoder.load_catalog(catalogpath,hashlib.sha256(raw).hexdigest())
    q['creature_catalog_sha256']=catalog['sha256'];qualified_shape=encoder.collate([q],catalog=catalog)
    expanded=model.migrate_weights_only(old,catalog_size=1);expanded(**qualified_shape)
    for name,fn in [('wrong_catalog_SHA',lambda:encoder.load_catalog(catalogpath,'f'*64)),('request_catalog_mismatch',lambda:encoder.validate(dict(q,creature_catalog_sha256='0'*64),catalog=catalog)),('all_unknown_coverage',lambda:encoder.catalog_coverage(catalog,[999])),('training_draft_gate',lambda:encoder.require_training_catalog(catalog,{'passed':True},[42]))]:
        try:fn()
        except ValueError:negatives.append(name)
        else:raise AssertionError('Accepted '+name)
    for name,entries in [('duplicate_catalog_id',[dict(creature_id=42,canonical_key='core:a'),dict(creature_id=42,canonical_key='core:b')]),('duplicate_catalog_key',[dict(creature_id=42,canonical_key='core:a'),dict(creature_id=43,canonical_key='core:a')]),('ordinal_catalog_key',[dict(creature_id=42,canonical_key=42)])]:
        raw=json.dumps(dict(schema='strategy-runtime-creature-catalog-v1',entries=entries)).encode()
        path=a.out/(name+'.json');path.write_bytes(raw)
        try:encoder.load_catalog(path,hashlib.sha256(raw).hexdigest())
        except ValueError:negatives.append(name)
        else:raise AssertionError('Accepted '+name)
    report=dict(passed=True,CPU_only=True,models_saved=0,GPU_steps=0,optimizer_steps=0,native_games=0,
        parent_sha256=digest,weights_only=True,reset_Adam=True,reset_RNG_required=True,discard_rollout=True,
        actual_TRAIN_projection_fixtures=len(chosen),added_recruit_state_is_synthetic=True,
        no_recruit_logits_critic_softmax_bitwise_equal=True,expanded_candidates_total_distribution_equivalence_claimed=False,
        manual_recruit_bias=-4.,manual_prior_is_learning=False,new_feature_gradient_abs_sum=gradients,new_Adam_state_empty=True,
        rejected_cases=negatives,real_catalog_available=False,training_gate='unconditionally closed',
        draft_contract_sha256=encoder.CONTRACT_SHA256,
        source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in HERE.glob('*.py')})
    (a.out/'AUDIT.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
