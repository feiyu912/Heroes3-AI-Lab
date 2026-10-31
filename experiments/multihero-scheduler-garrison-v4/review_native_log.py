"""Bind probe IDs to ordinary native protocol logs without changing frozen auditors."""
import hashlib,json,re
from pathlib import Path
HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
out=HERE/'independent-review-02/NATIVE_REQUEST_LOG_BINDING.json';assert not out.exists()
results={}
for arm in ('baseline','filtered'):
    work=HERE/'independent-review-02'/('v4-'+arm)
    rows=[json.loads(x) for x in (work/'probe.jsonl').read_text().splitlines() if x.strip()]
    log=(work/'client.log').read_text()
    requests=re.findall(r'Sending a request "[0-9]+(\w+)"\. It\'ll have an ID=(\d+)\.',log)
    swaps=[int(i) for name,i in requests if name=='GarrisonHeroSwap']
    moves=[int(i) for name,i in requests if name=='MoveHero']
    ack=[r for r in rows if r['event']=='garrison_setup_ack']
    assert len(ack)==1 and swaps==[ack[0]['request_id']] and ack[0]['result']==1
    sent=[r['request_id'] for r in rows if r['event']=='move_sent']
    assert moves==sent and len(moves)==22 and len(set(moves))==22
    assert log.count('Message 16GarrisonHeroSwap successfully applied!')==1
    assert 'Applied on gameState(): 15SetHeroesInTown' in log
    assert log.index('Message 16GarrisonHeroSwap successfully applied!')<log.index('Sending a request "8MoveHero"')
    assert log.count('Message 8MoveHero successfully applied!')==22
    results[arm]=dict(native_garrison_request_id=swaps[0],move_request_ids=moves,ordinary_native_move_success_messages=22,
        garrison_success_before_any_move=True,native_SetHeroesInTown_applied=True,probe_and_native_request_ID_sequences_identical=True,
        raw_sha256={n:sha(work/n) for n in ('probe.jsonl','client.log')})
out.write_text(json.dumps(dict(passed=True,arms=results,new_native_games=0,GPU_operations=0,optimizer_steps=0),indent=2))
print(json.dumps(dict(passed=True,arms=2,native_garrison_requests=2,actual_move_IDs_bound=44)))
