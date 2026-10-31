"""Prepare only. Frozen v3, accepted engine source/build and evidence are never mutated."""
from pathlib import Path
import hashlib,json,shutil,difflib
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'strategic-multihero-supply-v3'
sha=lambda data:hashlib.sha256(data).hexdigest()

def main():
    out=HERE/'candidate';out.mkdir(exist_ok=True)
    parent=json.loads((BASE/'CANDIDATE_MANIFEST.json').read_text())
    assert len(parent['files'])==11
    for rel,entry in parent['files'].items():
        data=(BASE/'candidate'/rel).read_bytes();assert sha(data)==entry['candidate_sha256']
        target=out/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    folder=out/'AI/DirectorAI'
    for name in ['SupplyRecovery.h','SupplyRecovery.inc']:shutil.copyfile(HERE/name,folder/name)
    h=folder/'CDirectorAI.h';text=h.read_text()
    text=text.replace('#include "SupplyController.h"','#include "SupplyController.h"\n#include "SupplyRecovery.h"\n#include "../../lib/json/JsonNode.h"',1)
    marker=' bool supplyMode() const;';assert text.count(marker)==1
    text=text.replace(marker,''' bool supplyMode() const;
 std::map<int,std::pair<int,int>> recoveryOwned;
 int recoveryLocalRequest=-1,recoverySaveRequest=-1,recoveryTargetTurn=0,recoveryBoundaryTurn=0;
 bool recoveryPersistenceBusy=false,recoveryCheckpointDone=false,recoveryResumePending=false;
 std::string recoveryNonce,recoverySaveName;
 JsonNode recoveryPayload;
 std::string recoveryEconomy() const;
 supply_recovery_v4::Snapshot recoveryCurrent() const;
 void recoveryEvent(const std::string & event,int request) const;
 void recoveryInit();
 bool recoveryResumeTurn(QueryID q);
 bool recoveryBeforeAdvance();
 bool recoverySent(const CPackForServer * pack,int request);
 bool recoveryAck(PackageApplied * pa);''',1);h.write_text(text)
    cpp=folder/'CDirectorAI.cpp';text=cpp.read_text()
    marker='logGlobal->info("DirectorAI: game interface ready for player %s", playerID.toString());'
    assert text.count(marker)==1;text=text.replace(marker,marker+'\n recoveryInit();',1)
    old='if(supplyMode()) {supplySent(pack,requestID);return;}';assert text.count(old)==1
    text=text.replace(old,'if(supplyMode()) {try {if(!recoverySent(pack,requestID))supplySent(pack,requestID);}catch(const std::exception&e){typedFailure(e.what());}return;}',1)
    old='if(supplyMode()) {supplyAck(pa);return;}';assert text.count(old)==1
    text=text.replace(old,'if(supplyMode()) {try {if(!recoveryAck(pa))supplyAck(pa);}catch(const std::exception&e){typedFailure(e.what());}return;}',1)
    text+='\n#include "SupplyRecovery.inc"\n';cpp.write_text(text)
    adapter=folder/'SupplyAdapter.inc';text=adapter.read_text()
    old='  // Native load integration is deliberately disabled until save/sidecar/load proof exists.';assert text.count(old)==1
    text=text.replace(old,'  if(recoveryResumeTurn(q))return;\n'+old,1)
    old='  if(!turnActive || typedProtocolFailed || supply.failed || endingTurn || supply.pending || supplyReplyRequest>=0) return;';assert text.count(old)==1
    text=text.replace(old,old+'\n  if(recoveryBeforeAdvance())return;',1);adapter.write_text(text)
    clienth=out/'client/Client.h';text=clienth.read_text();old='int requestCounter = 1;';assert text.count(old)==1
    clienth.write_text(text.replace(old,old+'\n bool recoveryLoadingGame=false;',1))
    client=out/'client/Client.cpp';text=client.read_text()
    text=text.replace('#include "StdInc.h"','#include "StdInc.h"\n#include "../AI/DirectorAI/SupplyRecovery.h"',1)
    old='void CClient::loadGame(std::shared_ptr<CGameState> initializedGameState)\n{';assert text.count(old)==1
    text=text.replace(old,old+'\n recoveryLoadingGame=true;',1);start=text.index(old);end=text.index('\n}',start)
    text=text[:end]+'\n recoveryLoadingGame=false;'+text[end:]
    old='void CClient::installNewPlayerInterface(std::shared_ptr<CGameInterface> gameInterface, PlayerColor color, bool battlecb)\n{';assert text.count(old)==1
    gate='''
 if(recoveryLoadingGame && gameInterface && gameInterface->dllName=="DirectorAI")
 {
  using namespace supply_recovery_v4;
  const char*mode=std::getenv("LAB_ADV_MODE");const char*bundlePath=std::getenv("LAB_ADV_RECOVERY_BUNDLE");
  const auto*state=gameInfo().getPlayerState(color);
  bool embedded=false;
  if(state&&state->playerLocalSettings){const JsonNode&settings=*state->playerLocalSettings;embedded=!settings["heroes3_supply_v4"].isNull();}
  const bool requested=(mode&&std::string(mode)=="scripted_supply_v1")||(bundlePath&&*bundlePath);
  if(embedded||requested)
  {
  ensure(mode&&std::string(mode)=="scripted_supply_v1"&&bundlePath&&*bundlePath,"native_director_load_requires_supply_recovery_bundle");
  const auto bytes=readFile(bundlePath,16*1024*1024);JsonParsingSettings parsing;parsing.strict=true;
  const JsonNode bundle(bytes.data(),bytes.size(),parsing,"supply-recovery-bundle");
  ensure(bundle["epoch"].String()==epoch&&bundle["source_token"].String()==sourceToken,"native_loaded_source_or_epoch_mismatch");
  auto actual=CResourceHandler::get()->getResourceName(ResourcePath(GAME->server().si->mapname,EResType::SAVEGAME));
  ensure(bool(actual),"native_loaded_save_unresolved");
  const auto actualSHA=sha256(readFile(actual->string()));ensure(actualSHA==bundle["save_sha256"].String(),"actual_loaded_save_hash_mismatch");
  logGlobal->info("DirectorSupplyActualLoad file=%s sha256=%s source=%s",actual->string(),actualSHA,sourceToken);
  }
 }
'''
    text=text.replace(old,old+gate,1);client.write_text(text)
    inputs={str(p.relative_to(out)).replace('\\','/'):sha(p.read_bytes()) for p in sorted(out.rglob('*')) if p.is_file()}
    token=sha(json.dumps(inputs,sort_keys=True,separators=(',',':')).encode())
    rh=folder/'SupplyRecovery.h';text=rh.read_text();assert text.count('@COMPILED_SOURCE_TOKEN@')==1
    rh.write_text(text.replace('@COMPILED_SOURCE_TOKEN@',token))
    files={str(p.relative_to(out)).replace('\\','/'): {'baseline_sha256':parent['files'].get(str(p.relative_to(out)).replace('\\','/'),{}).get('baseline_sha256'),
           'candidate_sha256':sha(p.read_bytes())} for p in sorted(out.rglob('*')) if p.is_file()}
    assert len(files)==13
    manifest={'schema':'scripted-supply-native-candidate-v4','controller_epoch':'scripted-supply-cargo-v3','recovery_epoch':'supply-native-boundary-v4',
              'files':files,'source_token':token,'normalized_source_inputs':inputs,'native_built':False,'native_games':0,
              'native_restore_qualified':False,'optimizer_steps':0,'parent_manifest_sha256':sha((BASE/'CANDIDATE_MANIFEST.json').read_bytes())}
    (HERE/'CANDIDATE_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n');(HERE/'MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
    delta=[]
    for rel in files:
        original=BASE/'candidate'/rel;a=original.read_text().splitlines(True) if original.exists() else []
        delta.extend(difflib.unified_diff(a,(out/rel).read_text().splitlines(True),fromfile='v3/'+rel,tofile='v4/'+rel))
    (HERE/'v3-to-v4.diff').write_text(''.join(delta));(HERE/'candidate.diff').write_text(''.join(delta))
    driver=(BASE/'build_capsule.py').read_text();old="DELETE_ALLOWLIST={'TypedPolicyProtocol.h','SupplyController.h','SupplyAdapter.inc'}";assert driver.count(old)==1
    driver=driver.replace(old,"DELETE_ALLOWLIST={'TypedPolicyProtocol.h','SupplyController.h','SupplyAdapter.inc','SupplyRecovery.h','SupplyRecovery.inc'}")
    (HERE/'build_capsule.py').write_text(driver)
    print(json.dumps({'plan_only':True,'files':len(files),'source_token':token,'native_built':False}))

if __name__=='__main__':main()
