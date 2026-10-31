"""Build a review-only candidate from an archived source; never edits native tree."""
from pathlib import Path
import difflib,hashlib,json

HERE=Path(__file__).resolve().parent
BASELINE=HERE/'baseline-CDirectorAI.cpp'
CANDIDATE=HERE/'candidate-CDirectorAI.cpp'
NEEDLE='\t\tauto previous = committedTargets.find(hero->id.getNum());\n'
ADDITION='''\t\t// Coordinate pressure only: no enemy reachability/interception prediction.
\t\t// Thresholds exactly match strategic-threat-response-v1/threat_contract.py.
\t\tconst double ownArmyValue = static_cast<double>(ArmyDescriptor(hero, true).getStrength());
\t\tconst int3 currentPosition = hero->visitablePos();
\t\tconst bool visiblePressure = std::any_of(visibleThreats.begin(), visibleThreats.end(), [&](const auto & threat)
\t\t{
\t\t\treturn threat.first.z == currentPosition.z &&
\t\t\t\tstd::max(std::abs(threat.first.x - currentPosition.x), std::abs(threat.first.y - currentPosition.y)) <= 12 &&
\t\t\t\tthreat.second >= 1.5 * std::max(1.0, ownArmyValue);
\t\t});
\t\tif(visiblePressure && previous != committedTargets.end())
\t\t{
\t\t\tcommittedTargets.erase(previous);
\t\t\tprevious = committedTargets.end();
\t\t\ttraceState("threat_commit_released");
\t\t}
'''

def expected_candidate(baseline):
    assert baseline.count(NEEDLE)==1,'Original commit branch changed; review instead of patch guessing'
    return baseline.replace(NEEDLE,NEEDLE+ADDITION)

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    outputs=[CANDIDATE,HERE/'candidate.diff',HERE/'CANDIDATE_MANIFEST.json']
    assert not any(p.exists()for p in outputs),'Never overwrite review artifacts'
    baseline=BASELINE.read_text();candidate=expected_candidate(baseline)
    CANDIDATE.write_text(candidate,newline='\n')
    (HERE/'candidate.diff').write_text(''.join(difflib.unified_diff(baseline.splitlines(True),candidate.splitlines(True),
        fromfile='baseline/AI/DirectorAI/CDirectorAI.cpp',tofile='candidate/AI/DirectorAI/CDirectorAI.cpp')))
    result=dict(schema='threat-response-source-candidate-v1',status='review_only_not_installed_or_compiled',
        source_origin='/root/heroes3-ai-lab/src/vcmi-adv/AI/DirectorAI/CDirectorAI.cpp',
        thresholds=dict(enemy_to_own_min_ratio=1.5,own_denominator_floor=1.0,same_level=True,chebyshev_max=12),
        behavior='Only erase an existing same-turn commit under current visible pressure; then keep all existing native legal candidates',
        trace='threat_commit_released only when an existing commit is actually erased',
        request_schema='strategy-candidates-v3',all_actions='MoveHero',hold_added=False,
        source_sha256={p.name:sha(p)for p in [BASELINE,CANDIDATE,HERE/'candidate.diff',HERE/'prepare_candidate.py',HERE/'threat_contract.py']})
    (HERE/'CANDIDATE_MANIFEST.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
