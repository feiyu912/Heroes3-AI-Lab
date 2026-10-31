"""Prepare owned-request drain; terminal foreign waits are cancelled, never acknowledged."""
import difflib,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'strategic-request-bind-barrier-v2'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((OLD/'CANDIDATE_MANIFEST.json').read_text());entries={p:dict(e) for p,e in manifest['files'].items()}
for relative in entries:
    p=HERE/'candidate'/relative;assert not p.exists();p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((OLD/'candidate'/relative).read_bytes())
p=HERE/'candidate/client/Client.h';text=p.read_text();needle='\tThreadSafeVector<int> waitingRequest;';assert text.count(needle)==1
text=text.replace(needle,needle+'\n\tThreadSafeVector<int> waitingDirectorRequest;\n\tbool directorTerminalShutdownScheduled = false;')
needle='\tbool empty()\n\t{\n\t\tTLock lock(mx);\n\t\treturn items.empty();\n\t}\n';assert text.count(needle)==1
text=text.replace(needle,needle+'\n\tstd::vector<T> snapshot()\n\t{\n\t\tTLock lock(mx);\n\t\treturn items;\n\t}\n')
p.write_text(text)
p=HERE/'candidate/client/Client.cpp';text=p.read_text()
needle='\tif(bindBeforeSend)\n\t\treceiver->requestSent(&request, requestID);';assert text.count(needle)==1
text=text.replace(needle,'''	if(bindBeforeSend)
	{
		waitingDirectorRequest.pushBack(requestID);
		logGlobal->info("DirectorNativeRequestRegistered id=%u player=%d type=%s",requestID,player.getNum(),typeid(request).name());
		receiver->requestSent(&request, requestID);
	}''')
needle='\twaitingRequest.requestTermination();';assert text.count(needle)==1
text=text.replace(needle,needle+'\n\twaitingDirectorRequest.clear();')
p.write_text(text)
p=HERE/'candidate/client/NetPacksClient.cpp';text=p.read_text()
start=text.index('static void shutdownAutoTestAfterNativeAcks(');end=text.index('void ApplyClientNetPackVisitor::visitPlayerEndsGame(',start)
helper='''static void shutdownAutoTestAfterNativeAcks(CClient & cl, const CGameState & gs)
{
	const bool allPlayersEndedGame = std::none_of(gs.players.begin(), gs.players.end(), [](const auto & player)
	{ return player.second.status == EPlayerStatus::INGAME; });
	const bool autoTest = !settings["session"]["testmap"].isNull() || !settings["session"]["testsave"].isNull();
	if(!autoTest || !allPlayersEndedGame || cl.directorTerminalShutdownScheduled) return;
	const bool directorGame = std::any_of(cl.playerint.begin(),cl.playerint.end(),[](const auto & entry)
	{ return entry.second && entry.second->dllName=="DirectorAI"; });
	if(directorGame ? !cl.waitingDirectorRequest.empty() : !cl.waitingRequest.empty())
	{
		logAi->info("Auto-test shutdown deferred: pending native request acknowledgments");
		return;
	}
	cl.directorTerminalShutdownScheduled=true;
	if(directorGame)
	{
		const auto remaining=cl.waitingRequest.snapshot();
		if(!remaining.empty())
		{
			std::ostringstream ids;ids << '[';
			for(size_t i=0;i<remaining.size();++i) { if(i) ids << ',';ids << remaining[i]; }
			ids << ']';
			logAi->info("TerminalPeerRequestCancellation ids=%s",ids.str());
		}
		logAi->info("All players have ended the game. Ending game after Director request ACK drain.");
	}
	else logAi->info("All players have ended the game. Ending game after native ACK drain.");
	// finishGameplay performs real requestTermination on unprocessed peer waits.
	GAME->onShutdownRequested(settings["session"]["spectate"].Bool());
}

'''
text=text[:start]+helper+text[end:]
needle='\tif (!cl.waitingRequest.tryRemovingElement(pack.requestID))';assert text.count(needle)==1
text=text.replace(needle,'''	if(cl.waitingDirectorRequest.tryRemovingElement(pack.requestID))
		logAi->info("DirectorNativeRequestAck id=%u player=%d pack_type=%d success=%d",pack.requestID,pack.player.getNum(),pack.packType,pack.result);
'''+needle)
text=text.replace('#include "StdInc.h"','#include "StdInc.h"\n#include <sstream>',1)
p.write_text(text)
for relative,e in entries.items():e['candidate_sha256']=sha(HERE/'candidate'/relative)
(HERE/'CANDIDATE_MANIFEST.json').write_text(json.dumps(dict(schema='director-native-terminal-drain-v1',files=entries,compiled=False,installed=False,
    plan_sha256=sha(HERE/'PLAN.md'),native_games=0,optimizer_steps=0,
    scope='Real Director registration/ACK ledger. Native all-player terminal required. Non-Director unprocessed terminal waits explicitly cancelled, never successful.'),indent=2))
diff=''
for relative in entries:
    diff+=''.join(difflib.unified_diff((OLD/'candidate'/relative).read_text().splitlines(True),(HERE/'candidate'/relative).read_text().splitlines(True),fromfile='bind-first/'+relative,tofile='owned-drain/'+relative))
(HERE/'candidate.diff').write_text(diff)
p=HERE/'build_capsule.py';assert not p.exists();p.write_bytes((OLD/'build_capsule.py').read_bytes())
print(json.dumps({'prepared':True,'native_writes':0,'files':len(entries),'optimizer_steps':0}))
