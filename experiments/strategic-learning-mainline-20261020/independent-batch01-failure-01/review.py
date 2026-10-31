"""Read existing failed TRAIN evidence; never starts games or admits samples."""
import hashlib,json,re
from pathlib import Path

OUT=Path(__file__).resolve().parent
B=Path('/root/heroes3-ai-lab/evaluations/strategic-mainline-temperature2-train-01')
C=Path('/root/heroes3-ai-lab/evaluations/typed-director-terminal-drain-capsule-03')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    raw=B/'cell-06/native';lines=(raw/'client.log').read_text().splitlines()
    result=json.loads((B/'RESULT.json').read_text());plan=json.loads((raw/'PLAN.json').read_text());execution=json.loads((raw/'EXECUTION.json').read_text())
    assert result['passed'] is False and len(result['completed'])==6
    assert plan['owned_player']==0 and plan['opponent']=='Nullkiller2' and plan['seed']==2026102006
    assert execution['client_exit']==0 and execution['game_completed'] and execution['transport_drained']
    assert not (B/'cell-06/admitted').exists() and not (B/'cell-07').exists()
    registrations=[];acks=[];reject=[]
    for i,s in enumerate(lines,1):
        if 'DirectorNativeRequestRegistered id=291 ' in s:registrations.append(i)
        if 'NativeRequestAck id=291 player=1 pack_type=189 success=1' in s:acks.append(i)
        if 'Got false in applying 16GarrisonHeroSwap' in s:reject.append(i)
    assert not registrations and len(acks)==1 and reject==[28617,28629]
    start=next(i for i,s in enumerate(lines) if 'Sending a request "16GarrisonHeroSwap". It\'ll have an ID=291.' in s)
    end=acks[0]
    window=lines[start:end]
    assert any('Received CPack of type 16GarrisonHeroSwap' in s for s in window)
    assert any('Cannot swap garrison hero!' in s for s in window)
    assert any('NK2AI::AIGateway::requestRealized' in s for s in window)
    manifest=json.loads((C/'build-source-manifest.json').read_text());sources={};source_paths={}
    for rel in ['server/CGameHandler.cpp','server/NetPacksServer.cpp']:
        p=C/'source-snapshot'/rel
        if not p.exists():p=Path('/root/heroes3-ai-lab/src/vcmi-adv')/rel
        assert sha(p)==manifest[rel]['sha256'];sources[rel]=p.read_text();source_paths[rel]=p
    g=sources['server/CGameHandler.cpp'];v=sources['server/NetPacksServer.cpp']
    swap=g[g.index('bool CGameHandler::garrisonSwap('):g.index('// With the amount of changes',g.index('bool CGameHandler::garrisonSwap('))]
    assert 'else\n\t{\n\t\tcomplain("Cannot swap garrison hero!");\n\t\treturn false;' in swap
    assert 'result = gh.garrisonSwap(pack.tid);' in v
    branch=g[g.index('result = applier.getResult();'):g.index('// BattleEnded and movement-query',g.index('result = applier.getResult();'))]
    assert branch.index('Got false in applying')<branch.index('sendPackageResponse(true);')
    paths=[Path(__file__),B/'RESULT.json',B/'PLAN.json',B/'cell-06/audit.log',raw/'client.log',raw/'PLAN.json',raw/'EXECUTION.json',C/'build-source-manifest.json',*source_paths.values()]
    out=dict(passed=True,scope='Independent diagnosis, NOT successful training batch certification',new_native_games=0,GPU_operations=0,optimizer_steps_performed=0,
        batch_valid=False,completed_admitted_cells=6,failed_cell=6,unrun_cells=[7],request=dict(id=291,player=1,owned_player=0,pack_type=189,type='GarrisonHeroSwap',actual_apply=False,ack_success=1,owned_registration=False,ACK_lines=acks,rejection_lines=reject),
        cell06_native_completed=True,cell06_train_admitted=False,source_snapshot_matches_capsule_manifest=True,
        inference='The exact complaint identifies the no-garrison/no-visiting branch at processing time. The log does not establish why NK issued this request or prove deterministic recurrence.',
        strict_global_rejection_preserved=True,ability_improvement_claim=False,input_sha256={str(p):sha(p) for p in paths})
    (OUT/'AUDIT.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({k:out[k] for k in ['passed','batch_valid','completed_admitted_cells','failed_cell','optimizer_steps_performed']}))
if __name__=='__main__':main()
