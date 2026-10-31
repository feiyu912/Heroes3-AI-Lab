"""Review-only headless terminal ACK-drain candidate from verified native sources."""
import difflib,hashlib,json,shutil
from pathlib import Path
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'strategic-typed-native-v1'
SOURCE=Path('/root/heroes3-ai-lab/src/vcmi-adv')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((OLD/'CANDIDATE_MANIFEST.json').read_text());entries=manifest['files'].copy()
for relative in ['client/Client.h','client/NetPacksClient.cpp']:
    p=SOURCE/relative;dest=HERE/'baseline'/relative;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(p.read_bytes())
    entries[relative]={'baseline_sha256':sha(p),'candidate_sha256':None}
for relative in manifest['files']:
    source=OLD/'candidate'/relative;dest=HERE/'candidate'/relative;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(source.read_bytes())
header=(HERE/'baseline/client/Client.h').read_text()
needle='\tvoid waitWhileContains(const T & item)'
assert header.count(needle)==1
header=header.replace(needle,'\tbool empty()\n\t{\n\t\tTLock lock(mx);\n\t\treturn items.empty();\n\t}\n\n'+needle)
(HERE/'candidate/client').mkdir(parents=True,exist_ok=True)
(HERE/'candidate/client/Client.h').write_text(header)
text=(HERE/'baseline/client/NetPacksClient.cpp').read_text()
start=text.index('\t// In auto testing mode close client once game is over for all players')
end=text.index('\n}\n',start)
old=text[start:end]
helper='''static void shutdownAutoTestAfterNativeAcks(CClient & cl, const CGameState & gs)
{
	const bool allPlayersEndedGame = std::none_of(gs.players.begin(), gs.players.end(), [](const auto & player)
	{
		return player.second.status == EPlayerStatus::INGAME;
	});
	const bool autoTest = !settings["session"]["testmap"].isNull() || !settings["session"]["testsave"].isNull();
	if(!autoTest || !allPlayersEndedGame)
		return;
	if(!cl.waitingRequest.empty())
	{
		logAi->info("Auto-test shutdown deferred: pending native request acknowledgments");
		return;
	}
	logAi->info("All players have ended the game. Ending game after native ACK drain.");
	GAME->onShutdownRequested(settings["session"]["spectate"].Bool());
}

'''
text=text[:start]+'\tshutdownAutoTestAfterNativeAcks(cl, gs);'+text[end:]
where='void ApplyClientNetPackVisitor::visitPlayerEndsGame(PlayerEndsGame & pack)'
assert text.count(where)==1;text=text.replace(where,helper+where)
needle='\t\tlogNetwork->warn("Surprising server message! PackageApplied for unknown requestID!");\n}'
assert text.count(needle)==1
text=text.replace(needle,'\t\tlogNetwork->warn("Surprising server message! PackageApplied for unknown requestID!");\n\tshutdownAutoTestAfterNativeAcks(cl, gs);\n}')
(HERE/'candidate/client/NetPacksClient.cpp').write_text(text)
for relative in entries:entries[relative]['candidate_sha256']=sha(HERE/'candidate'/relative)
result={'schema':'typed-native-source-candidate-v2-terminal-ack-drain','installed':False,'compiled':False,'native_runs':0,'files':entries,
    'scope':'Native rules, server apply and acknowledgment unchanged. Headless auto-test cleanup waits for existing actual request registry to drain.'}
(HERE/'CANDIDATE_MANIFEST.json').write_text(json.dumps(result,indent=2))
diff=''
for relative in ['client/Client.h','client/NetPacksClient.cpp']:
    diff+=''.join(difflib.unified_diff((HERE/'baseline'/relative).read_text().splitlines(True),(HERE/'candidate'/relative).read_text().splitlines(True),fromfile='baseline/'+relative,tofile='candidate/'+relative))
(HERE/'client.diff').write_text(diff)
print(json.dumps({'prepared_only':True,'files':len(entries),'native_writes':0,'optimizer_steps':0}))
