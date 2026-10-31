"""Source/pure arithmetic fixtures only. No C++ compilation or native legality certification."""
import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
def main():
    cpp=(HERE/'candidate/AI/DirectorAI/CDirectorAI.cpp').read_text();h=(HERE/'candidate/AI/DirectorAI/TypedPolicyProtocol.h').read_text();server=(HERE/'candidate/server/CGameHandler.cpp').read_text()
    for name in ('appendRecruitCandidates','issuePolicyRecruit','recruitTownState','verifyRecruitApplied','issueFreeArmyTransferV6','verifyFreeTransferApplied'):
        assert cpp.count('CDirectorAI::'+name+'(')==1
    assert 'MAX_POLICY_ECONOMY' not in cpp and 'policyEconomyActions' not in cpp
    assert 'definition->maxAmount(cb->getResourceAmount())' in cpp and 'army->getSlotFor(id)' in cpp
    assert 'town->creatures[ctx.level].first!=ctx.beforeStock-ctx.amount' in cpp
    assert 'armyTotals(army)!=expected' in cpp and 'resources[i]!=ctx.beforeResources[i]-ctx.recruitCost[i]' in cpp
    assert 'beforeRecruitStock.size()!=town->creatures.size()' in cpp and 'ids!=before.second' in cpp and 'armyTotals(visitor)!=ctx.beforeVisitorArmy' in cpp
    assert 'creature->getIndex()' in cpp and 'creature->getJsonKey()' in cpp and 'LIBRARY->creh->objects' in cpp and 'creature_catalog_sha256' in cpp
    newwindow=h.split('namespace LabLearnedRecruit',1)[1]
    assert 'if(op=="move") return true;' in newwindow and 'if(op!="end_turn") return false;' in newwindow
    assert cpp.count('recruitment_draft_execution_disabled')==1
    economy=cpp.split('bool CDirectorAI::issueEconomy()',1)[1].split('void CDirectorAI::traceState',1)[0]
    assert economy.index('if(learnedRecruitEnabled) continue;')<economy.index('for(int level =')
    for f in ('tid','dst','crid','amount','level'):assert 'actualRecruit->'+f in cpp
    assert 'expectedWhat' in cpp and 'actual->val!=0' in cpp and 'attemptedFreeTransferStates.insert' in cpp
    assert 'TypedRecruitApplied' in server and 'TypedFreeTransferApplied' in server
    # Explicitly labelled fake scalar examples: exercise contract mathematics only.
    def buckets(stock,afford):
        limit=min(stock,afford);return sorted({1,max(1,limit//2),limit}) if limit>0 else []
    examples=[(0,10,[]),(1,10,[1]),(2,10,[1,2]),(10,5,[1,2,5]),(10,10,[1,5,10]),(10,0,[])]
    for stock,afford,expected in examples:assert buckets(stock,afford)==expected
    # Clamp/unchanged state must not satisfy exact requested-amount proof.
    before_stock=10;requested=6;clamped_actual=4
    assert before_stock-clamped_actual!=before_stock-requested and before_stock!=before_stock-requested
    result=dict(passed=True,scope='Static strings and fake scalar bucket/conservation examples only; no compile/native predicate or transaction execution',bucket_examples=len(examples),fake_clamp_and_no_progress_rejected=True,
        source_execution_gate_present=True,native_run_allowed=False,CXX_syntax_checked=False,native_builds=0,native_games=0,GPU_runs=0,optimizer_steps=0,
        input_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),HERE/'CANDIDATE_MANIFEST.json',HERE/'candidate.diff',HERE/'CONTRACT_DRAFT.md']})
    (HERE/'CPU_STATIC_REPORT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
