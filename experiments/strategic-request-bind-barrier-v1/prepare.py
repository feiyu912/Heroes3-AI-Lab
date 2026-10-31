"""Register the actual request/typed context before native transport can run it."""
import difflib,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'strategic-threat-replan-v2';SOURCE=Path('/root/heroes3-ai-lab/src/vcmi-adv')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((OLD/'CANDIDATE_MANIFEST.json').read_text());entries={p:dict(v) for p,v in manifest['files'].items()}
for relative in entries:
    p=HERE/'candidate'/relative;assert not p.exists();p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((OLD/'candidate'/relative).read_bytes())
relative='client/Client.cpp';original=SOURCE/relative;baseline=HERE/'baseline'/relative;baseline.parent.mkdir(parents=True);baseline.write_bytes(original.read_bytes())
text=original.read_text();needle='''	GAME->server().sendGamePack(request);
	if(vstd::contains(playerint, player))
		playerint[player]->requestSent(&request, requestID);'''
assert text.count(needle)==1
text=text.replace(needle,'''	// Bind the allocated request identity before another thread may apply it.
	// waitingRequest already owns this ID; actual server apply/ACK remain mandatory.
	if(vstd::contains(playerint, player))
		playerint[player]->requestSent(&request, requestID);
	GAME->server().sendGamePack(request);''')
p=HERE/'candidate'/relative;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
entries[relative]=dict(baseline_sha256=sha(original),candidate_sha256=sha(p))
h=HERE/'candidate/AI/DirectorAI/CDirectorAI.h';text=h.read_text();needle='  bool automatic = false;bool moveResultSeen = false;';assert text.count(needle)==1
text=text.replace(needle,needle+'\n  int3 objectStep = int3(-1,-1,-1);');h.write_text(text)
p=HERE/'candidate/AI/DirectorAI/CDirectorAI.cpp';text=p.read_text()
needle='\tcb->moveHero(hero, hero->convertFromVisitablePos(step), false, EPathfindingLayer::LAND);';assert text.count(needle)==1
text=text.replace(needle,'\tpreparedTyped->objectStep=hero->convertFromVisitablePos(step);\n'+needle)
needle=' outstandingTyped=*preparedTyped;outstandingTyped->nativeRequestID=requestID;preparedTyped.reset();';assert text.count(needle)==1
text=text.replace(needle,'''
 if(pack->player!=playerID || static_cast<int>(pack->requestID)!=requestID)
 { typedFailure("actual_native_request_identity_mismatch");return; }
 if(const auto * actual=dynamic_cast<const MoveHero *>(pack))
 {
  if(actual->hid.getNum()!=preparedTyped->hero || actual->path.size()!=1 || actual->path.front()!=preparedTyped->objectStep)
  { typedFailure("actual_native_move_payload_mismatch");return; }
 }
'''+needle)
p.write_text(text)
for relative,e in entries.items():e['candidate_sha256']=sha(HERE/'candidate'/relative)
(HERE/'CANDIDATE_MANIFEST.json').write_text(json.dumps(dict(schema='typed-request-bind-before-native-transport-v1',files=entries,
    compiled=False,installed=False,native_games=0,optimizer_steps=0,
    scope='Same native rules and packets. Register existing real ID before transport; validate selected hero/object-coordinate payload. All AI requestSent callbacks now occur before sendGamePack.'),indent=2))
diff=''
for relative in entries:
    old=baseline if relative=='client/Client.cpp' else OLD/'candidate'/relative
    diff+=''.join(difflib.unified_diff(old.read_text().splitlines(True),(HERE/'candidate'/relative).read_text().splitlines(True),fromfile='previous/'+relative,tofile='bind-first/'+relative))
(HERE/'candidate.diff').write_text(diff)
p=HERE/'build_capsule.py';assert not p.exists();p.write_bytes((OLD/'build_capsule.py').read_bytes())
print(json.dumps({'prepared':True,'files':len(entries),'native_writes':0,'optimizer_steps':0}))
