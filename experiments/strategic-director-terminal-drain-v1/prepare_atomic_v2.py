"""New epoch: atomically capture IDs actually terminated, retaining built v1."""
import hashlib,json,shutil,difflib
from pathlib import Path
OLD=Path(__file__).resolve().parent;NEW=OLD.parent/'strategic-director-terminal-drain-v2'
NEW.mkdir(exist_ok=False)
for p in OLD.glob('*.py'):
    if p.name not in ('prepare.py','complete_prepare.py','prepare_atomic_v2.py'):shutil.copy2(p,NEW/p.name)
shutil.copytree(OLD/'candidate',NEW/'candidate')
(NEW/'PLAN.md').write_text((OLD/'PLAN.md').read_text()+'''\nAtomic epoch v2: built v1 had no native games. Its pending snapshot before a separate clear was insufficient to identify the exact IDs cancelled under a concurrent ACK. v2 adds requestTerminationWithSnapshot, capturing and clearing the actual pending vector under one mutex with the existing termination flag/notify behavior. NativeRequestTermination is emitted from its returned actual IDs after termination. Built v1 source/binaries remain preserved, not revised.\n''')
p=NEW/'candidate/client/Client.h';text=p.read_text();needle='\tvoid clear()\n';assert text.count(needle)==1
text=text.replace(needle,'''\tstd::vector<T> requestTerminationWithSnapshot()
\t{
\t\tTLock lock(mx);
\t\tisTerminating = true;
\t\tconst auto terminated = items;
\t\titems.clear();
\t\tcond.notify_all();
\t\treturn terminated;
\t}

'''+needle);p.write_text(text)
p=NEW/'candidate/client/Client.cpp';text=p.read_text();assert text.count('const auto remaining=waitingRequest.snapshot();')==1
text=text.replace('const auto remaining=waitingRequest.snapshot();','const auto remaining=waitingRequest.requestTerminationWithSnapshot();')
assert text.count('\twaitingRequest.requestTermination();')==1
text=text.replace('\twaitingRequest.requestTermination();\n','');p.write_text(text)
p=NEW/'qualify.py';text=p.read_text().replace('typed-director-terminal-drain-capsule-01','typed-director-terminal-drain-capsule-02');p.write_text(text)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((OLD/'CANDIDATE_MANIFEST.json').read_text());manifest['schema']='director-native-terminal-drain-atomic-v2';manifest['plan_sha256']=sha(NEW/'PLAN.md')
for relative,e in manifest['files'].items():e['candidate_sha256']=sha(NEW/'candidate'/relative)
(NEW/'CANDIDATE_MANIFEST.json').write_text(json.dumps(manifest,indent=2))
diff=''
for relative in manifest['files']:
    diff+=''.join(difflib.unified_diff((OLD/'candidate'/relative).read_text().splitlines(True),(NEW/'candidate'/relative).read_text().splitlines(True),fromfile='v1/'+relative,tofile='atomic-v2/'+relative))
(NEW/'candidate.diff').write_text(diff)
print(json.dumps(dict(prepared=True,native_writes=0,optimizer_steps=0,old_built_v1_preserved=True)))
