"""Synthetic facts check code only. Never qualify a catalog or deliver a model."""
import argparse,copy,hashlib,importlib.util,json,sys
from pathlib import Path
import torch
import encoder,model
HERE=Path(__file__).resolve().parent
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    torch.set_num_threads(1)
    raw=(json.dumps(dict(schema='strategy-runtime-creature-catalog-v1',entries=[dict(creature_id=42,canonical_key='core:synthetic')]))+'\n').encode()
    catpath=a.out/'SYNTHETIC_catalog.json';catpath.write_bytes(raw)
    catalog=encoder.load_catalog(catpath,hashlib.sha256(raw).hexdigest());encoder.configure_catalog(catalog)
    oldio=module('_recruit_cpu_parent',HERE.parent/'strategic-learned-free-transfer-policy-v1/model_io.py')
    old,_,parent_sha=oldio.load_model(HERE.parent/'strategic-learned-free-transfer-policy-v1/initialization-01/free-transfer-initialization.pt')
    assert parent_sha=='83319be8bde5d94eea839b1a889821449a7c1492c65da7ca6cde2deb63aab25a'
    new=model.migrate_weights_only(old,catalog_size=1)
    source=Path('/root/heroes3-ai-lab/evaluations/strategic-learned-free-transfer-train-01/cell-00/admitted/samples.jsonl')
    records=[json.loads(line) for line in source.read_text().splitlines()]
    chosen=[records[0]['request']]+[r['request'] for r in records if any(c['op']=='build' for c in r['request']['candidates'])][:3]
    def enrich(original):
        q=copy.deepcopy(original);q.update(schema=encoder.SCHEMA,economy_epoch=encoder.EPOCH,creature_catalog_sha256=catalog['sha256'])
        for t in q['own_towns']:
            t['recruit_state']=dict(town_id=t['town_id'],owner=q['player'],built_today=t['built_today'],resources=copy.deepcopy(q['resources']),
                upper_army_id=t['town_id'],upper_army=[None]*7,visitor=None,recruit_stock=[dict(level=0,available=10,creature_ids=[42])])
        return q
    for original in chosen:
        q=enrich(original);b=encoder.collate([q],catalog=catalog);oldbatch=encoder.old.collate([original])
        assert torch.equal(b['state'],oldbatch['state']) and torch.equal(b['candidates'][...,:43],oldbatch['candidates'])
        with torch.no_grad():x,v=old(**oldbatch);y,w=new(**b)
        assert torch.equal(x,y) and torch.equal(v,w) and torch.equal(x.softmax(-1),y.softmax(-1))
    q=enrich(chosen[0]);q['economy_window_open']=True;t=q['own_towns'][0]
    q['candidates'].append(dict(op='recruit',actor='player_town',town_id=t['town_id'],destination_army_id=t['town_id'],destination_role='town',
        creature_id=42,amount=1,level=0,destination_slot=0,quantity_bucket='one',available=10,affordable=10,cost={r:0 for r in encoder.RESOURCES}))
    logits,value=new(**encoder.collate([q],catalog=catalog));(-logits.log_softmax(-1)[0,-1]+value.sum()).backward()
    gradients={k:float(dict(new.named_parameters())[k].grad.abs().sum()) for k in ('actor.recruit_bias','recruit_actor.weight','recruit_critic.weight')}
    assert all(v>0 for v in gradients.values())
    optimizer=torch.optim.Adam(new.parameters(),lr=3e-4);assert not optimizer.state
    cases=dict(wrong_destination=lambda x:x['candidates'][-1].update(destination_army_id=999999),wrong_stock=lambda x:x['candidates'][-1].update(available=9),
        wrong_bucket=lambda x:x['candidates'][-1].update(quantity_bucket='half'),closed_window=lambda x:x.update(economy_window_open=False),
        wrong_schema=lambda x:x.update(schema='strategy-candidates-v5'),wrong_catalog=lambda x:x.update(creature_catalog_sha256='0'*64),
        nonfinite_amount=lambda x:x['candidates'][-1].update(amount=float('nan')),foreign_resource=lambda x:x['candidates'][-1]['cost'].update(unknown=0),
        occupied_slot=lambda x:x['own_towns'][0]['recruit_state']['upper_army'].__setitem__(0,dict(slot=0,creature_id=9,count=1)),
        duplicate_candidate=lambda x:x['candidates'].append(copy.deepcopy(x['candidates'][-1])))
    rejected=[]
    for name,mutate in cases.items():
        bad=copy.deepcopy(q);mutate(bad)
        try:encoder.validate(bad,catalog=catalog)
        except (ValueError,TypeError):rejected.append(name)
        else:raise AssertionError('Accepted '+name)
    for name,fn in [('synthetic_training_catalog',lambda:encoder.require_training_catalog(catalog,{'passed':True},[42])),
                    ('all_unknown',lambda:encoder.catalog_coverage(catalog,[999999]))]:
        try:fn()
        except ValueError:rejected.append(name)
        else:raise AssertionError('Accepted '+name)
    report=dict(passed=True,CPU_only=True,synthetic_catalog_and_added_facts=True,native_qualification_claim=False,models_saved=0,GPU_steps=0,optimizer_steps=0,native_games=0,
        parent_sha256=parent_sha,weights_only=True,projection_rows=len(chosen),no_recruit_logits_critic_softmax_bitwise_equal=True,
        new_feature_gradient_abs_sum=gradients,new_Adam_state_empty=True,rejected_cases=rejected)
    (a.out/'AUDIT.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
