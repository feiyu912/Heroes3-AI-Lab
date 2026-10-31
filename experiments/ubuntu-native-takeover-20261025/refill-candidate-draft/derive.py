"""Source-only derivation. No compiler, native game, model or optimizer."""
import difflib
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
PARENT = PROJECT / 'experiments/strategic-learned-recruitment-native-v3'
CPP = 'AI/DirectorAI/CDirectorAI.cpp'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def derive_cpp(source):
    assert source.count('\tcandidates.clear();\n') == 1
    source = source.replace('\tcandidates.clear();\n', '\tcandidates.clear();\n\tstd::vector<int3> refillTargets;\n', 1)
    before = '''\t\t\tif(town && town->getUpperArmy()->stacksCount() > 0)
\t\t\t\tconsider(obj->visitablePos(), 5, "own town reinforcements", 4);'''
    after = '''\t\t\tif(town && town->getUpperArmy()->stacksCount() > 0)
\t\t\t{
\t\t\t\tconst auto candidateCount = candidates.size();
\t\t\t\tconsider(obj->visitablePos(), 5, "own town reinforcements", 4);
\t\t\t\tconst auto * army = town->getUpperArmy();
\t\t\t\tconst auto * visitor = town->getVisitingHero();
\t\t\t\tif(learnedRecruitEnabled && candidates.size() != candidateCount && army != hero &&
\t\t\t\t\tarmy->getOwner() == playerID && (!visitor || visitor == hero) &&
\t\t\t\t\t!(army->needsLastStack() && army->stacksCount() < 2))
\t\t\t\t{
\t\t\t\t\tfor(const auto & slot : army->Slots())
\t\t\t\t\t{
\t\t\t\t\t\tconst auto count = slot.second->getCount();
\t\t\t\t\t\tif(count > 0 && count <= std::numeric_limits<int>::max() &&
\t\t\t\t\t\t\thero->getSlotFor(slot.second->getCreatureID()).validSlot())
\t\t\t\t\t\t{
\t\t\t\t\t\t\trefillTargets.push_back(obj->visitablePos());
\t\t\t\t\t\t\tbreak;
\t\t\t\t\t\t}
\t\t\t\t\t}
\t\t\t\t}
\t\t\t}'''
    assert source.count(before) == 1
    source = source.replace(before, after, 1)
    before = '                else candidates.assign(1, committed);'
    after = '''                else if(learnedRecruitEnabled)
                {
                    std::vector<Candidate> retainedMoves{committed};
                    for(const auto & candidate : candidates)
                    {
                        if(candidate.kind != 4 ||
                            (candidate.destination == committed.destination && candidate.kind == committed.kind) ||
                            std::find(refillTargets.begin(), refillTargets.end(), candidate.destination) == refillTargets.end())
                            continue;
                        retainedMoves.push_back(candidate);
                    }
                    candidates = std::move(retainedMoves);
                }
                else candidates.assign(1, committed);'''
    assert source.count(before) == 1
    return source.replace(before, after, 1)


def main():
    manifest_path = PARENT / 'CANDIDATE_MANIFEST.json'
    manifest = json.loads(manifest_path.read_text())
    assert manifest['files'][CPP]['candidate_sha256'] == '2d7180f8101d2f60e83d28b84b462e82cd6534b5ce85ac4e13a76c56b7b40eb2'
    entries, changes, old_hashes = {}, [], {}
    for relative, old in manifest['files'].items():
        source = PARENT / 'candidate' / relative
        expected = old['candidate_sha256']
        assert sha(source) == expected
        old_hashes[str(source)] = expected
        output = HERE / 'candidate' / relative
        output.parent.mkdir(parents=True, exist_ok=True)
        raw = source.read_bytes()
        if relative == CPP:
            raw = derive_cpp(raw.decode()).encode()
        with output.open('xb') as stream:
            stream.write(raw)
        entries[relative] = dict(parent_candidate_sha256=expected, candidate_sha256=sha(output),
                                 changed=raw != source.read_bytes())
        changes.extend(difflib.unified_diff(source.read_text().splitlines(True), output.read_text().splitlines(True),
                                          fromfile='qualified-schema6-source/' + relative,
                                          tofile='refill-retention-draft/' + relative))
    assert len(entries) == 9
    assert [name for name, entry in entries.items() if entry['changed']] == [CPP]
    assert all(sha(path) == expected for path, expected in old_hashes.items())
    (HERE / 'candidate.diff').write_text(''.join(changes))
    output = dict(schema='schema6-committed-refill-retention-source-draft-v1',
                  status='source-ready-not-CXX-compiled-not-native-qualified',
                  mode='build_recruit_v1', action_schema='strategy-candidates-v6',
                  response_schema='strategy-typed-action-response-v3',
                  factor='when commitment applies retain original committed move plus generated receivable own-town kind4 moves',
                  parent_manifest_path=str(manifest_path), parent_manifest_sha256=sha(manifest_path),
                  derive_sha256=sha(__file__), files=entries,
                  old_source_bytes_unchanged=True, build_allowed=False, native_run_allowed=False,
                  next_gate='review and adapt isolated native Ubuntu capsule builder, then registered mechanism qualification',
                  CXX_syntax_checked=False, native_builds=0, native_games=0, GPU_operations=0, optimizer_steps=0,
                  reward_changed=False, PPO_changed=False, initialization_changed=False,
                  new_protocol_fields=False, forced_policy_action=False, destination_merging=False)
    (HERE / 'CANDIDATE_MANIFEST.json').write_text(json.dumps(output, indent=2) + '\n')
    report = dict(passed=True, scope='Exact source derivation and unchanged-payload verification only',
                  parent_payloads_checked=9, changed_payloads=[CPP], other_eight_payloads_byte_exact=True,
                  parent_sources_unchanged=True, CXX_syntax_checked=False, native_builds=0, native_games=0,
                  GPU_operations=0, optimizer_steps=0, native_qualification_passed=False,
                  inputs=old_hashes | {str(manifest_path): sha(manifest_path), str(Path(__file__)): sha(__file__)},
                  candidate_manifest_sha256=sha(HERE / 'CANDIDATE_MANIFEST.json'))
    (HERE / 'DERIVATION_REPORT.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({key: value for key, value in output.items() if key != 'files'}, indent=2))


if __name__ == '__main__':
    main()
