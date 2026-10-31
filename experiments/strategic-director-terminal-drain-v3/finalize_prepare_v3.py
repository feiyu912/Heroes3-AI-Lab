"""Seal review-only v3 payload and diff; no WSL native tree/build/process mutation."""
import difflib
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
PARENT=HERE.parent/'strategic-director-terminal-drain-v2'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    old=json.loads((PARENT/'CANDIDATE_MANIFEST.json').read_text())
    assert len(old['files'])==9
    manifest=dict(old)
    manifest.update(schema='director-native-terminal-drain-closed-v3',compiled=False,installed=False,
                    native_games=0,optimizer_steps=0,plan_sha256=sha(HERE/'PLAN.md'),
                    parent_candidate_manifest_sha256=sha(PARENT/'CANDIDATE_MANIFEST.json'),
                    termination_registry_semantics='atomic-termination-closed-registry-v3')
    differences=[];changed=[]
    for relative,entry in old['files'].items():
        previous=PARENT/'candidate'/relative;current=HERE/'candidate'/relative
        assert sha(previous)==entry['candidate_sha256'],relative
        manifest['files'][relative]=dict(entry,candidate_sha256=sha(current))
        if current.read_bytes()!=previous.read_bytes():
            changed.append(relative)
            differences.extend(difflib.unified_diff(previous.read_text().splitlines(True),current.read_text().splitlines(True),
                               fromfile='atomic-v2/'+relative,tofile='closed-v3/'+relative))
    assert changed==['client/Client.h'],changed
    (HERE/'candidate.diff').write_text(''.join(differences))
    manifest['changed_from_v2']=changed
    manifest['scope']='Atomic termination with late enqueue rejection, terminating wait predicate and nonasserting late ACK removal. Real Director ACK scope unchanged.'
    (HERE/'CANDIDATE_MANIFEST.json').write_text(json.dumps(manifest,indent=2))
    sources=[p for p in HERE.glob('*.py')]+[HERE/'PLAN.md',HERE/'candidate.diff',HERE/'CANDIDATE_MANIFEST.json']
    record=dict(prepared=True,native_engine_builds=0,native_engine_runs=0,GPU_operations=0,optimizer_steps=0,
                changed_from_v2=changed,source_sha256={str(p):sha(p) for p in sources})
    (HERE/'PREPARATION.json').write_text(json.dumps(record,indent=2));print(json.dumps(record,indent=2))


if __name__=='__main__':main()
