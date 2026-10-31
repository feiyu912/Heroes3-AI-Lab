"""Finalize reviewed proposal before any build or game; retain pre-review manifest."""
import difflib,hashlib,json,shutil
from pathlib import Path
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'strategic-terminal-ack-drain-v1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=HERE/'candidate/AI/DirectorAI/CDirectorAI.cpp';text=p.read_text()
assert text.count('<< playerID.getNum()')==1
text=text.replace('<< playerID.getNum()','<< static_cast<int>(playerID.getNum())')
manifest=HERE/'CANDIDATE_MANIFEST.json';backup=HERE/'CANDIDATE_MANIFEST.pre-review.json';assert not backup.exists();shutil.copy2(manifest,backup)
p.write_text(text)
data=json.loads(manifest.read_text())
for relative,e in data['files'].items():e['candidate_sha256']=sha(HERE/'candidate'/relative)
data['review_correction']='Stream PlayerColor as integer, never an unsigned-char JSON token'
manifest.write_text(json.dumps(data,indent=2))
diff=''
for relative in data['files']:
    diff+=''.join(difflib.unified_diff((OLD/'candidate'/relative).read_text().splitlines(True),(HERE/'candidate'/relative).read_text().splitlines(True),fromfile='ack-drain/'+relative,tofile='bounded-replan/'+relative))
(HERE/'candidate.diff').write_text(diff)
print(json.dumps({'reviewed_manifest_sha256':sha(manifest),'native_writes':0,'compiled':False}))
