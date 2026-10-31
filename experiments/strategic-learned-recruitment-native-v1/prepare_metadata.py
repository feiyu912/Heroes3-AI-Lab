"""CPU source provenance/diff only. Never installs/builds/runs candidate native files."""
import difflib,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;PARENT=HERE.parent/'strategic-learned-economy-native-v2'
CAP=Path('/root/heroes3-ai-lab/evaluations/strategic-learned-economy-build-capsule-02');SRC=Path('/root/heroes3-ai-lab/src/vcmi-adv')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(name,data):(HERE/name).write_text(json.dumps(data,indent=2)+'\n')
def main():
    manifest=json.loads((PARENT/'CANDIDATE_MANIFEST.json').read_text());compiled=json.loads((CAP/'build-source-manifest.json').read_text());entries={};diff=[];changed=[]
    for rel,e in manifest['files'].items():
        parent=PARENT/'candidate'/rel;candidate=HERE/'candidate'/rel
        assert sha(parent)==e['candidate_sha256']==compiled[rel]['sha256'],'Parent differs from actual compiled capsule02: '+rel
        entries[rel]=dict(baseline_sha256=e['baseline_sha256'],parent_compiled_candidate_sha256=sha(parent),candidate_sha256=sha(candidate))
        if parent.read_text()!=candidate.read_text():
            changed.append(rel);diff+=list(difflib.unified_diff(parent.read_text().splitlines(True),candidate.read_text().splitlines(True),fromfile='capsule02/'+rel,tofile='recruitment-draft/'+rel))
    assert len(entries)==9 and set(changed)=={'AI/DirectorAI/CDirectorAI.cpp','AI/DirectorAI/CDirectorAI.h','AI/DirectorAI/TypedPolicyProtocol.h','server/CGameHandler.cpp'}
    protocol=HERE/'candidate/AI/DirectorAI/TypedPolicyProtocol.h';assert protocol.read_text().startswith((PARENT/'candidate/AI/DirectorAI/TypedPolicyProtocol.h').read_text()),'Legacy protocol prefix changed'
    cpp=(HERE/'candidate/AI/DirectorAI/CDirectorAI.cpp').read_text()
    assert 'if(learnedRecruitEnabled) { typedFailure("recruitment_draft_execution_disabled");return; }' in cpp
    snippets={}
    for rel,start,end in [('server/CGameHandler.cpp',2635,2729),('server/NetPacksServer.cpp',167,173),('lib/callback/CCallback.cpp',64,72),('lib/networkPacks/PacksForServer.h',322,350),('lib/CCreatureHandler.cpp',311,319),('lib/mapObjects/CGTownInstance.cpp',874,879)]:
        p=SRC/rel;lines=p.read_text().splitlines();snippets[rel]=dict(path=str(p),sha256=sha(p),start_line=start,end_line=end,lines=lines[start-1:end])
    original=(SRC/'server/CGameHandler.cpp').read_text();candidate=(PARENT/'candidate/server/CGameHandler.cpp').read_text()
    a='bool CGameHandler::recruitCreatures(';b='bool CGameHandler::upgradeCreature('
    assert original[original.index(a):original.index(b)]==candidate[candidate.index(a):candidate.index(b)]
    catalog_api=[]
    for rel,start,end in [('lib/CCreatureHandler.h',124,133),('lib/CCreatureHandler.cpp',52,65),('lib/IHandlerBase.h',147,149)]:
        p=SRC/rel;catalog_api.append(dict(path=str(p),sha256=sha(p),start_line=start,end_line=end,lines=p.read_text().splitlines()[start-1:end]))
    write('NATIVE_SOURCE_EVIDENCE.json',dict(source_rules=snippets,catalog_api=catalog_api,recruit_handler_text_identical_to_actual_compiled_parent_candidate=True,source_reads_only=True))
    (HERE/'candidate.diff').write_text(''.join(diff))
    write('CANDIDATE_MANIFEST.json',dict(schema='director-learned-recruitment-schema6-draft-v1',status='draft-execution-disabled-not-compiled',native_run_allowed=False,build_allowed=False,build_driver_sha256=sha(HERE/'build_capsule.py'),
        action_schema='strategy-candidates-v6',response_schema='strategy-typed-action-response-v3',economy_epoch='learned-economy-build-recruit-v1',mode='build_recruit_v1',
        parent_manifest_sha256=sha(PARENT/'CANDIDATE_MANIFEST.json'),actual_parent_capsule=str(CAP),compiled_parent_source_manifest_sha256=sha(CAP/'build-source-manifest.json'),
        contract_sha256=sha(HERE/'CONTRACT_DRAFT.md'),source_evidence_sha256=sha(HERE/'NATIVE_SOURCE_EVIDENCE.json'),prepare_metadata_sha256=sha(Path(__file__)),files=entries,
        native_builds=0,native_games=0,GPU_runs=0,optimizer_steps=0))
    print(json.dumps(dict(prepared=True,actual_parent_payloads_matched=9,changed_files=changed,native_run_allowed=False,native_builds=0,native_games=0,GPU_runs=0,optimizer_steps=0),indent=2))
if __name__=='__main__':main()
