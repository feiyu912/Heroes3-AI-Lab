"""Scope pre-transport binding to DirectorAI; preserve opponent callback ordering."""
import difflib,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'strategic-request-bind-barrier-v1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((OLD/'CANDIDATE_MANIFEST.json').read_text());entries={p:dict(v) for p,v in manifest['files'].items()}
for relative in entries:
    p=HERE/'candidate'/relative;assert not p.exists();p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((OLD/'candidate'/relative).read_bytes())
p=HERE/'candidate/client/Client.cpp';text=p.read_text()
needle='''	// Bind the allocated request identity before another thread may apply it.
	// waitingRequest already owns this ID; actual server apply/ACK remain mandatory.
	if(vstd::contains(playerint, player))
		playerint[player]->requestSent(&request, requestID);
	GAME->server().sendGamePack(request);''';assert text.count(needle)==1
replacement='''	// Only the experimental Director registers its allocated request before transport.
	// Other interfaces retain their original post-send callback ordering.
	const auto interfaceIt=playerint.find(player);
	const auto receiver=interfaceIt==playerint.end() ? nullptr : interfaceIt->second;
	const bool bindBeforeSend=receiver && receiver->dllName=="DirectorAI";
	if(bindBeforeSend)
		receiver->requestSent(&request, requestID);
	GAME->server().sendGamePack(request);
	if(receiver && !bindBeforeSend)
		receiver->requestSent(&request, requestID);'''
text=text.replace(needle,replacement);p.write_text(text)
for relative,e in entries.items():e['candidate_sha256']=sha(HERE/'candidate'/relative)
(HERE/'CANDIDATE_MANIFEST.json').write_text(json.dumps(dict(schema='typed-director-request-bind-before-transport-v2',files=entries,
    compiled=False,installed=False,native_games=0,optimizer_steps=0,
    scope='Only DirectorAI early observer binding; other AI callback timing unchanged. Retain actual native MoveHero payload/identity guard.'),indent=2))
(HERE/'candidate.diff').write_text(''.join(difflib.unified_diff((OLD/'candidate/client/Client.cpp').read_text().splitlines(True),text.splitlines(True),fromfile='global-bind/client/Client.cpp',tofile='director-bind/client/Client.cpp')))
p=HERE/'build_capsule.py';assert not p.exists();p.write_bytes((OLD/'build_capsule.py').read_bytes())
print(json.dumps({'prepared':True,'native_writes':0,'optimizer_steps':0}))
