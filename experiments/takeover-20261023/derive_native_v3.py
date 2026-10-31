"""Preserve v2 compile failure; isolate missing-declaration include correction."""
import hashlib,json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]/'experiments'
src=ROOT/'strategic-learned-recruitment-native-v2'
dst=ROOT/'strategic-learned-recruitment-native-v3'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert not dst.exists()
shutil.copytree(src,dst,ignore=shutil.ignore_patterns('__pycache__'))
p=dst/'derive.py';s=p.read_text()
s=s.replace("return b''.join(l for l in lines if l.strip() not in (GATE,COMMENT))", "data=b''.join(l for l in lines if l.strip() not in (GATE,COMMENT))\n    anchor=b'#include \"../../lib/CCreatureHandler.h\"'\n    assert data.count(anchor)==1\n    return data.replace(anchor, anchor+b'\\n#include \"../../lib/GameLibrary.h\"',1)")
s=s.replace("only_runtime_logic_difference_removes_draft_init_gate=True", "removes_draft_init_gate_and_adds_GameLibrary_declaration=True")
p.write_text(s)
p=dst/'README.md';p.write_text('''# Recruitment native v3: missing declaration repair

Preserves the complete v2 draft and failed capsule01 build evidence. The only
candidate source change from v2 is including lib/GameLibrary.h to declare LIBRARY.
No native engine or policy logic is changed. Uses the unchanged schema6 contract.
New compilation and actual mechanism qualification remain mandatory.
''')
p=dst/'qualification/pipeline_common.py';s=p.read_text().replace('recruitment-capsule-01','recruitment-capsule-02')
# SHA is filled only after exact v3 manifest derivation.
s=s.replace("MANIFEST_SHA='865988a27bc8de8f257b767ac5b10927e76da96fe974e37414fe7519f38e7830'", "MANIFEST_SHA='PENDING_V3_MANIFEST'")
p.write_text(s)
(dst/'V2_PROVENANCE.json').write_text(json.dumps(dict(parent=str(src),parent_manifest_sha256=sha(src/'CANDIDATE_MANIFEST.json'),failed_capsule='/root/heroes3-ai-lab/evaluations/strategic-learned-recruitment-capsule-01',failure='LIBRARY was not declared in exportCreatureCatalog; add GameLibrary.h only'),indent=2)+'\n')
print(dst)
