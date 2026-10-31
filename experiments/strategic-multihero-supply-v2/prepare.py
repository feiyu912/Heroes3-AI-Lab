"""Plan-only candidate builder. Never installs, compiles, runs a game, or takes a pool lock."""
from pathlib import Path
import difflib
import hashlib
import json
import shutil

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / 'strategic-director-terminal-drain-v3' / 'candidate'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    out = HERE / 'candidate'
    out.mkdir(exist_ok=True)
    manifest = {'epoch': 'scripted-supply-v1', 'observability_revision':2, 'plan_only': True, 'native_built': False,
                'native_qualified': False, 'native_restore_qualified': False,
                'learned_samples': 0, 'optimizer_steps': 0, 'base_files': {}, 'candidate_files': {}}
    files = sorted(p for p in BASE.rglob('*') if p.is_file())
    assert len(files) == 9
    for p in files:
        rel = p.relative_to(BASE)
        manifest['base_files'][str(rel).replace('\\','/')] = sha(p)
        target = out / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, target)
    h = out/'AI/DirectorAI/CDirectorAI.h'
    text = h.read_text(encoding='utf-8')
    text = text.replace('#pragma once', '#pragma once\n#include "SupplyController.h"', 1)
    mark = 'private:\n'
    assert text.count(mark) == 1
    decl = '''private:
 bool supplyMode() const;
 supply_v1::Controller supply;
 supply_v1::TurnBoundaryGate supplyTurnGate;
 std::map<int,int> supplyReplies;
 int supplyReplyRequest=-1,supplyReplyQuery=-1;
 bool supplyMoveSeen=false;
 int3 supplyStep;
 std::set<std::tuple<int,int,int>> supplyVisited;
 supply_v1::World supplyWorld() const;
 void supplyTrace(const std::string & event,int id=-1,const std::string & actualRequest="") const;
 void supplyQueueReply(QueryID q,int answer);
 void supplyBegin(QueryID q);
 void supplyAdvance();
 void supplySent(const CPackForServer * pack,int id);
 void supplyAck(PackageApplied * pa);
 void supplyMoved(const TryMoveHero & details);
public:
 void heroExchangeStarted(ObjectInstanceID a,ObjectInstanceID b,QueryID q) override;
private:
'''
    h.write_text(text.replace(mark, decl, 1), encoding='utf-8', newline='\n')
    cpp = out/'AI/DirectorAI/CDirectorAI.cpp'
    text = cpp.read_text(encoding='utf-8')
    def entry(signature, body):
        nonlocal text
        marker = signature + '\n{'
        assert text.count(marker) == 1, signature
        text = text.replace(marker, marker+'\n'+body, 1)
    entry('void CDirectorAI::yourTurn(QueryID queryID)',
          ' if(supplyMode()) {supplyBegin(queryID);return;}')
    entry('void CDirectorAI::advanceTurn()',
          ' if(supplyMode()) {supplyAdvance();return;}')
    entry('void CDirectorAI::heroMoved(const TryMoveHero & details, bool verbose)',
          ' if(supplyMode()) {supplyMoved(details);return;}')
    entry('void CDirectorAI::requestRealized(PackageApplied * pa)',
          ' if(supplyMode()) {supplyAck(pa);return;}')
    entry('void CDirectorAI::requestSent(const CPackForServer * pack, int requestID)',
          ' if(supplyMode()) {supplySent(pack,requestID);return;}')
    entry('void CDirectorAI::queryResolved(QueryID queryID)',
          ' if(supplyMode()) {supplyTrace("native_query_resolved");return;}')
    callbacks = [
      ('void CDirectorAI::heroGotLevel(const CGHeroInstance *hero, PrimarySkill pskill, std::vector<SecondarySkill> &skills, QueryID queryID)', 'queryID', '0'),
      ('void CDirectorAI::commanderGotLevel(const CCommanderInstance * commander, std::vector<ui32> skills, QueryID queryID)', 'queryID', '0'),
      ('void CDirectorAI::showBlockingDialog(const std::string &text, const std::vector<Component> &components, QueryID askID, const int soundID, bool selection, bool cancel, bool safeToAutoaccept)', 'askID', '(selection && !components.empty()) || (!selection && cancel) ? 1 : 0'),
      ('void CDirectorAI::showTeleportDialog(const CGHeroInstance * hero, TeleportChannelID channel, TTeleportExitsList exits, bool impassable, QueryID askID)', 'askID', '0'),
      ('void CDirectorAI::showGarrisonDialog(const CArmedInstance * up, const CGHeroInstance * down, bool removableUnits, QueryID queryID, const MetaString & customTitle)', 'queryID', '0'),
      ('void CDirectorAI::showMapObjectSelectDialog(QueryID askID, const Component & icon, const MetaString & title, const MetaString & description, const std::vector<ObjectInstanceID> & objects)', 'askID', '0')]
    for sig, q, answer in callbacks:
        entry(sig, f' if(supplyMode()) {{supplyQueueReply({q},{answer});return;}}')
    text += '\n#include "SupplyAdapter.inc"\n'
    cpp.write_text(text, encoding='utf-8', newline='\n')
    for name in ['SupplyController.h', 'SupplyAdapter.inc']:
        shutil.copyfile(HERE/name, out/'AI/DirectorAI'/name)
    diff=[]
    for p in sorted(out.rglob('*')):
        if not p.is_file(): continue
        rel=p.relative_to(out); key=str(rel).replace('\\','/')
        manifest['candidate_files'][key]=sha(p)
        original=BASE/rel
        a=original.read_text(encoding='utf-8').splitlines(True) if original.exists() else []
        b=p.read_text(encoding='utf-8').splitlines(True)
        diff.extend(difflib.unified_diff(a,b,fromfile='base/'+key,tofile='candidate/'+key))
    (HERE/'candidate.diff').write_text(''.join(diff),encoding='utf-8',newline='\n')
    (HERE/'MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    accepted=json.loads((BASE.parent/'CANDIDATE_MANIFEST.json').read_text(encoding='utf-8'))
    capsule={'schema':'scripted-supply-native-candidate-v2','controller_epoch':'scripted-supply-v1',
             'observability_revision':2,'native_built':False,'native_games':0,
             'native_restore_qualified':False,'optimizer_steps':0,'files':{},
             'parent_candidate_manifest_sha256':sha(BASE.parent/'CANDIDATE_MANIFEST.json'),
             'accepted_baseline':'capsule03 accepted-backup (original accepted V8), NOT capsule03 candidate',
             'termination_registry_semantics':'atomic-termination-closed-registry-v3'}
    for rel,digest in manifest['candidate_files'].items():
        capsule['files'][rel]={'baseline_sha256':accepted['files'].get(rel,{}).get('baseline_sha256'),
                               'candidate_sha256':digest}
    (HERE/'CANDIDATE_MANIFEST.json').write_text(json.dumps(capsule,indent=2)+'\n',encoding='utf-8')
    delta=[]
    old=HERE.parent/'strategic-multihero-supply-v1'/'candidate'
    for p in sorted(out.rglob('*')):
        if not p.is_file(): continue
        rel=p.relative_to(out)
        delta.extend(difflib.unified_diff((old/rel).read_text(encoding='utf-8').splitlines(True),
                     p.read_text(encoding='utf-8').splitlines(True),fromfile='v1/'+str(rel),tofile='v2/'+str(rel)))
    (HERE/'v1-to-v2.diff').write_text(''.join(delta),encoding='utf-8',newline='\n')
    # Preserve the reviewed locked build/recompile-restore procedure, changing
    # only candidate location, exact accepted-V8 pinning, and the deletion whitelist.
    driver=(BASE.parent/'build_capsule.py').read_text(encoding='utf-8')
    driver=driver.replace("LAB=Path('/root/heroes3-ai-lab');SOURCE=LAB/'src/vcmi-adv';BUILD=LAB/'src/vcmi-adv-build'",
        "LAB=Path('/root/heroes3-ai-lab');SOURCE=LAB/'src/vcmi-adv';BUILD=LAB/'src/vcmi-adv-build'\n"
        "ACCEPTED=LAB/'evaluations/typed-director-terminal-drain-capsule-03/accepted-backup'\n"
        "DELETE_ALLOWLIST={'TypedPolicyProtocol.h','SupplyController.h','SupplyAdapter.inc'}\n"
        "def remove_added(target):\n"
        "    assert target.parent.resolve()==(SOURCE/'AI/DirectorAI').resolve() and target.name in DELETE_ALLOWLIST\n"
        "    assert not target.is_symlink()\n"
        "    target.unlink(missing_ok=True)\n")
    marker='assert_no_native(BUILD/\'bin\');base=source_manifest(SOURCE);validate_source_links(base)'
    assert driver.count(marker)==1
    driver=driver.replace(marker,marker+"\n        assert base==json.loads((ACCEPTED/'base-source-manifest.json').read_text()),'Not original accepted V8 source tree'")
    marker="original_hash={n:sha(BUILD/'bin'/n) for n in NAMES}"
    assert driver.count(marker)==1
    driver=driver.replace(marker,marker+"\n        assert original_hash==json.loads((ACCEPTED/'binary-sha256.json').read_text()),'Not exact accepted V8 three binaries'")
    old="assert target.parent.resolve()==(SOURCE/'AI/DirectorAI').resolve() and target.name=='TypedPolicyProtocol.h'\n                            target.unlink()"
    assert driver.count(old)==1
    driver=driver.replace(old,'remove_added(target)')
    old="if value is None:(SOURCE/p).unlink(missing_ok=True)"
    assert driver.count(old)==1
    driver=driver.replace(old,'if value is None:remove_added(SOURCE/p)')
    (HERE/'build_capsule.py').write_text(driver,encoding='utf-8',newline='\n')
    print(json.dumps({'plan_only':True,'base_files':len(files),'candidate_files':len(manifest['candidate_files']),
                      'native_built':False,'native_restore_qualified':False}))

if __name__=='__main__': main()
