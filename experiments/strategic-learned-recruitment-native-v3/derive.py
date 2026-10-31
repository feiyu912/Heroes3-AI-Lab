"""CPU-only exact derivation from preserved reviewed v1 draft; never installs native files."""
import difflib,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;DRAFT=HERE.parent/'strategic-learned-recruitment-native-v1';COMPILED_PARENT=HERE.parent/'strategic-learned-economy-native-v2'
CAP=Path('/root/heroes3-ai-lab/evaluations/strategic-learned-economy-build-capsule-02')
CPP='AI/DirectorAI/CDirectorAI.cpp'
GATE=b'if(learnedRecruitEnabled) { typedFailure("recruitment_draft_execution_disabled");return; }'
COMMENT=b'// Deliberate source-level draft gate. Remove only in a reviewed, new qualified source epoch.'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(name,data):(HERE/name).write_text(json.dumps(data,indent=2)+'\n')
def expected_cpp(data):
    lines=data.splitlines(keepends=True);assert sum(l.strip()==GATE for l in lines)==1 and sum(l.strip()==COMMENT for l in lines)==1
    data=b''.join(l for l in lines if l.strip() not in (GATE,COMMENT))
    anchor=b'#include "../../lib/CCreatureHandler.h"'
    assert data.count(anchor)==1
    return data.replace(anchor, anchor+b'\n#include "../../lib/GameLibrary.h"',1)
def main():
    draft=json.loads((DRAFT/'CANDIDATE_MANIFEST.json').read_text());parent=json.loads((COMPILED_PARENT/'CANDIDATE_MANIFEST.json').read_text());compiled=json.loads((CAP/'build-source-manifest.json').read_text());entries={};diff=[];capsule_diff=[]
    assert draft['native_run_allowed'] is False and draft['build_allowed'] is False
    for rel,e in draft['files'].items():
        p=DRAFT/'candidate'/rel;assert sha(p)==e['candidate_sha256']
        cp=COMPILED_PARENT/'candidate'/rel;assert sha(cp)==e['parent_compiled_candidate_sha256']==parent['files'][rel]['candidate_sha256']==compiled[rel]['sha256']
        expected=expected_cpp(p.read_bytes()) if rel==CPP else p.read_bytes();target=HERE/'candidate'/rel
        # Own new directory only. This never changes preserved v1 or shared VCMI.
        target.write_bytes(expected)
        entries[rel]=dict(baseline_sha256=e['baseline_sha256'],draft_candidate_sha256=sha(p),parent_compiled_candidate_sha256=sha(cp),candidate_sha256=sha(target))
        diff+=list(difflib.unified_diff(p.read_text().splitlines(True),target.read_text().splitlines(True),fromfile='preserved-draft/'+rel,tofile='reviewed-source-ready/'+rel))
        capsule_diff+=list(difflib.unified_diff(cp.read_text().splitlines(True),target.read_text().splitlines(True),fromfile='compiled-capsule02/'+rel,tofile='reviewed-source-ready/'+rel))
    assert len(entries)==9
    (HERE/'draft-to-ready.diff').write_text(''.join(diff));(HERE/'candidate.diff').write_text(''.join(capsule_diff))
    write('CANDIDATE_MANIFEST.json',dict(schema='director-learned-recruitment-schema6-v1',status='reviewed-source-ready-not-compiled-or-native-qualified',build_allowed=True,native_run_allowed=False,
        mode='build_recruit_v1',action_schema='strategy-candidates-v6',response_schema='strategy-typed-action-response-v3',economy_epoch='learned-economy-build-recruit-v1',
        preserved_draft_manifest_sha256=sha(DRAFT/'CANDIDATE_MANIFEST.json'),parent_manifest_sha256=sha(COMPILED_PARENT/'CANDIDATE_MANIFEST.json'),actual_parent_capsule=str(CAP),compiled_parent_source_manifest_sha256=sha(CAP/'build-source-manifest.json'),
        contract_sha256=sha(HERE/'CONTRACT.md'),build_driver_sha256=sha(HERE/'build_capsule.py'),derive_sha256=sha(Path(__file__)),source_evidence_sha256=sha(HERE/'NATIVE_SOURCE_EVIDENCE.json'),files=entries,
        qualification_runner_required=True,native_builds=0,native_games=0,GPU_runs=0,optimizer_steps=0))
    write('DERIVATION_CPU_REPORT.json',dict(passed=True,removes_draft_init_gate_and_adds_GameLibrary_declaration=True,other_eight_payload_bytes_exact=True,preserved_draft_current_SHA_verified=True,actual_compiled_parent_nine_payloads_SHA_verified=True,
        build_allowed=True,native_run_allowed=False,CXX_syntax_checked=False,native_builds=0,native_games=0,GPU_runs=0,optimizer_steps=0,
        inputs={str(p):sha(p) for p in [Path(__file__),DRAFT/'CANDIDATE_MANIFEST.json',HERE/'CONTRACT.md',HERE/'build_capsule.py',HERE/'CANDIDATE_MANIFEST.json']}))
    print(json.dumps(dict(derived=True,only_changed_draft_payload=CPP,other_eight_payload_bytes_exact=True,build_allowed=True,native_run_allowed=False,native_builds=0,native_games=0,GPU_runs=0,optimizer_steps=0),indent=2))
if __name__=='__main__':main()
