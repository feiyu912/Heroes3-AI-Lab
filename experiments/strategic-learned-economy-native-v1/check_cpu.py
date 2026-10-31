"""Pure helper tests and exact source/diff invariants; never engine/runtime qualification."""
import hashlib,json,subprocess,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def main():
    manifest=json.loads((HERE/'CANDIDATE_MANIFEST.json').read_text());assert len(manifest['files'])==9
    assert manifest['contract_sha256']==sha(HERE/'CONTRACT.md')
    for relative,entry in manifest['files'].items():
        assert sha(HERE/'candidate'/relative)==entry['candidate_sha256']
        assert sha(HERE.parent/'strategic-director-terminal-drain-v3/candidate'/relative)==entry['parent_candidate_sha256']
    source=(HERE/'candidate/AI/DirectorAI/CDirectorAI.cpp').read_text()
    checks=dict(no_scripted_build_fallback='if(!learnedBuildEnabled) for(const auto building : priorities)' in source,
        window_before_optional_spend='(!learnedBuildEnabled || !buildWindow.open || cb->getHeroesInfo().empty()) && issueEconomy()' in source,
        immutable_late_end_ack='else if(end && ctx.ownTurn==ownTurns)' in source,
        unique_pending_build='if(build && (pendingEconomy || actualBuild->tid.getNum()!=preparedTyped->townID' in source,
        actual_payload_check='actualBuild->bid.getNum()!=preparedTyped->buildingID' in source,
        no_build_move_commit='if(candidates[selected].build) { reason="typed_build";return true; }' in source,
        no_build_move_dispatch='if(candidates[selectedCandidate].build) return issuePolicyBuild();' in source,
        real_ack_required='if(pa->result && !ctx.buildResultSeen)' in source,
        ordinary_native_legal_only='definition->second->mode!=CBuilding::BUILD_NORMAL' in source and 'cb->canBuildStructure(town,id)!=EBuildingState::ALLOWED' in source,
        callback_observation_no_advance='// Observation only: never clear the tuple, synthesize ACK, or advance here.' in source,
        retained_query_battle_barrier='!pendingQueries.empty() || !queryRequests.empty() || outstandingTyped || preparedTyped' in source)
    assert all(checks.values()),checks
    with tempfile.TemporaryDirectory(prefix='learned-build-wire-cpu-') as temp:
        binary=Path(temp)/'test';subprocess.run(['g++','-std=c++17','-O0','-I',str(HERE),str(HERE/'test_protocol.cpp'),'-o',str(binary)],check=True)
        unit=json.loads(subprocess.check_output([str(binary)],text=True))
    result=dict(passed=unit['passed'],unit=unit,source_invariants=checks,candidate_manifest_sha256=sha(HERE/'CANDIDATE_MANIFEST.json'),
        candidate_files={r:e['candidate_sha256'] for r,e in manifest['files'].items()},native_builds=0,native_games=0,gpu_runs=0,
        limitation='Wire/window unit assertions and source guards; native ordering/legality still needs actual engine qualification')
    (HERE/'CPU_REPORT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
