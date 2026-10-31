"""Bind actual first native owned army to each registered map multiplier."""
import argparse,collections,hashlib,json
from pathlib import Path
ROOT=Path('/mnt/g/Heroes3-AI-Lab')
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();assert not a.out.exists()
    d=read(a.run/'RESULT.json');assert d['passed'] and len(d['results'])==12
    manifest=read(ROOT/'experiments/strategic-active-opponent-curriculum-v2-20261023/MAP_MANIFEST.json')
    binding=read(ROOT/'experiments/strategic-learned-recruitment-run-v2/QUALIFICATION.json');assert sha(binding['catalog_path'])==binding['catalog_sha256']
    catalog=read(binding['catalog_path']);ids={x['canonical_key']:x['creature_id'] for x in catalog['entries']}
    results=[]
    for i,r in enumerate(d['results']):
        job=r['job'];entry=next(e for e in manifest['variants'] if e['map']==job['map'])
        native=a.run/f'cell-{i:02d}/native';trace=[json.loads(x) for x in (native/'strategy-trace.jsonl').read_text().splitlines() if x.strip()]
        first=trace[0];assert first['event']=='turn_start' and first['player']==job['player'] and first['day']==1 and len(first['heroes'])==1
        expected=collections.Counter()
        for s in entry['modified_army']:expected[ids[s['type']]]+=s['amount']
        actual=collections.Counter()
        for cid,n in first['heroes'][0]['army']:actual[cid]+=n
        assert actual==expected
        q=read(native/'agent/request-00000001.json');assert q['player']==job['player'] and q['own_hero_count']==1 and q['creature_catalog_sha256']==binding['catalog_sha256']
        local=native/'data/vcmi/Maps/adv'/(job['map']+'.vmap');assert sha(local)==entry['sha256']
        results.append(dict(cell=i,job=job,actual_initial_owned_army=dict(actual),expected_initial_owned_army=dict(expected),runtime_map_sha256=sha(local),trace_sha256=sha(native/'strategy-trace.jsonl')))
    result=dict(passed=True,all12_runtime_owned_initial_armies_exact=True,actual_runtime_catalog_bound=True,all12_private_maps_exact=True,entries=results,new_native_games=0,GPU_operations=0,optimizer_steps=0,enemy_initial_state_scope='Static map strict diff and loaded map identity; unseen enemy state is not inferred from owned-only trace')
    a.out.write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='entries'}))
if __name__=='__main__':main()
