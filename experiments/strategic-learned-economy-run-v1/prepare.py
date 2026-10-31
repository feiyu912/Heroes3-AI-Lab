"""Produce inspectable isolated adapters; never change the frozen parent files."""
import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;EXPERIMENTS=HERE.parent
sources={}
def read(path):
    path=Path(path);raw=path.read_bytes();sources[str(path)]=hashlib.sha256(raw).hexdigest();return raw.decode()
def change(text,a,b):
    assert text.count(a)==1,(a,text.count(a));return text.replace(a,b,1)
def main():
    old=EXPERIMENTS/'strategic-learning-mainline-20261020/native-pipeline'
    t=read(old/'collect_episode_v5.py')
    t=change(t,"BASE=LOCAL.parent.parent/'strategic-typed-training-v1'","BASE=LOCAL.parent/'strategic-learned-economy-policy-v1'\nLEGACY=LOCAL.parent/'strategic-typed-training-v1'\nsys.path.append(str(LEGACY))")
    t=change(t,"HERE/'live_jsonl.py'","LEGACY/'live_jsonl.py'")
    t=change(t,"LAB_ADV_TYPED_EVENTS=str(work/'typed.jsonl'))","LAB_ADV_TYPED_EVENTS=str(work/'typed.jsonl'),LAB_ADV_LEARNED_ECONOMY='build_v1',LAB_ADV_BUILD_PACKS=str(work/'build-packs.jsonl'))")
    t=change(t,"loaded={};child=None;broker=None;result=", "(work/'build-packs.jsonl').touch(exist_ok=False)\n    loaded={};child=None;broker=None;result=")
    (HERE/'collect_episode_v5.py').write_text(t)
    t=read(EXPERIMENTS/'strategic-policy-v3/audit_typed_execution.py')
    t=change(t,"policy_moves=0,policy_end_turns=0","policy_moves=0,policy_builds=0,policy_end_turns=0")
    t=change(t,"response['schema']=='strategy-typed-action-response-v1'","response['schema']=='strategy-typed-action-response-v2'")
    t=change(t,"event['op'] in ('move','end_turn') and event['pack_type']==('EndTurn' if event['op']=='end_turn' else 'MoveHero')","event['op'] in ('move','end_turn','build') and event['pack_type']=={'move':'MoveHero','end_turn':'EndTurn','build':'BuildStructure'}[event['op']]")
    t=change(t,"counts['policy_end_turns' if event['op']=='end_turn' else 'policy_moves']+=1","counts[{'move':'policy_moves','end_turn':'policy_end_turns','build':'policy_builds'}[event['op']]]+=1")
    t=change(t,"row['complete']=(row['server_applied'] and row['ack']) if sent['op']=='end_turn' else (row['move_result'] is not None and row['ack'])","row['complete']=(row['server_applied'] and row['ack']) if sent['op'] in ('end_turn','build') else (row['move_result'] is not None and row['ack'])")
    t=change(t,"row['classification']='complete_end_turn' if sent['op']=='end_turn' else 'complete_move'","row['classification']={'move':'complete_move','end_turn':'complete_end_turn','build':'complete_build_requires_raw_evidence'}[sent['op']]")
    t=change(t,"if sent['op']=='end_turn':\n                        require(row['server_applied']","if sent['op'] in ('end_turn','build'):\n                        require(row['server_applied']")
    # Uses only the new strict encoder/broker and an additional build proof.
    t='import sys\nfrom pathlib import Path\nsys.path.insert(0,str(Path(__file__).resolve().parent.parent/"strategic-learned-economy-policy-v1"))\n'+t
    (HERE/'audit_contract.py').write_text(t)
    t=read(EXPERIMENTS/'strategic-typed-native-v1/raw_events_v4.py')
    t=change(t,'from audit_typed_execution import BINDING','from audit_contract import BINDING')
    t=change(t,'op=(move|end_turn)','op=(move|end_turn|build)')
    (HERE/'raw_events_v5.py').write_text(t)
    t=read(EXPERIMENTS/'strategic-director-terminal-drain-v4/audit_game_v6.py')
    start=t.index('import collections,json,re,sys')
    end=t.index('folder=Path(sys.argv[1])')
    t=t[:start]+'''import collections,json,re,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
from pipeline_common import NATIVE,BASE,AUDIT_EPOCH,MARKER,audit_metadata,AUDITOR_SOURCES,registry
verify_registry,whole_game_pass=registry.verify,registry.whole_game_pass
sys.path.insert(0,str(BASE))
from broker import validate_response,digest
from raw_events_v5 import extract
from audit_contract import audit
from build_evidence import verify as verify_build

'''+t[end:]
    start=t.index('input_audit_epoch=')
    end=t.index('capsule=Path(plan')
    t=t[:start]+'''input_audit_epoch=plan.get('audit_epoch')
assert input_audit_epoch==AUDIT_EPOCH
assert all(plan.get(k)==v for k,v in audit_metadata().items())
candidate_manifest=json.loads((NATIVE/'CANDIDATE_MANIFEST.json').read_text())
assert candidate_manifest['schema']=='director-learned-economy-build-v1'
manifest_path=NATIVE/'CANDIDATE_MANIFEST.json'
assert plan['hashes'][str(manifest_path)]==digest(manifest_path.read_bytes())
'''+t[end:]
    t=change(t,"contract=audit(proposals,events,fixture=False)","contract=audit(proposals,events,fixture=False)\nbuild_proof=verify_build(raw,proposals,[json.loads(s) for s in (folder/'build-packs.jsonl').read_text().splitlines()])\nassert build_proof['passed'] and build_proof['policy_builds']==contract['counts']['policy_builds']")
    t=change(t,"read_only_legacy_reaudit=legacy_reaudit","read_only_legacy_reaudit=False")
    t=change(t,"digest((HERE/'CANDIDATE_MANIFEST.json').read_bytes())","digest((NATIVE/'CANDIDATE_MANIFEST.json').read_bytes())")
    t=change(t,"'EXECUTION.json','PLAN.json')","'EXECUTION.json','PLAN.json','agent/typed-broker.jsonl','build-packs.jsonl')")
    t=change(t,"auditor_sha256={p.name:digest(p.read_bytes()) for p in [Path(__file__),TYPED/'raw_events_v4.py',HERE/'director_registry_v1.py']}","auditor_sha256={n:digest(p.read_bytes()) for n,p in AUDITOR_SOURCES.items()}")
    t=change(t,"(out/'events.jsonl').write_text", "report.update(audit_metadata());report.update(build_evidence_verified=True,build_evidence=build_proof)\n(out/'events.jsonl').write_text")
    (HERE/'audit_game_v6.py').write_text(t)
    t=read(old/'run_pipeline.py')
    t=change(t,"default=2026102000","default=2026102600")
    t=change(t,"[Path(__file__).resolve(),HERE/'train_update_v3.py',checkpoint]","[Path(__file__).resolve(),BASE/'train_update_v3.py',checkpoint]")
    t=change(t,"str(HERE/'train_update_v3.py')","str(BASE/'train_update_v3.py')")
    t=change(t,"str(HERE/'admit_episode_v5.py')","str(BASE/'admit_episode_v5.py')")
    t=change(t,"First mainline batch must use the explicit temperature2 initialization","First build batch must use the explicit schema5 migration initialization")
    t=change(t,"Python integration only; reward/PPO/sampler unchanged; no partial-cell update","Schema5 real build integration; original terminal reward/PPO unchanged; no partial-cell update")
    (HERE/'run_pipeline.py').write_text(t)
    (HERE/'PARENT_SOURCES.json').write_text(json.dumps(sources,indent=2)+'\n')
if __name__=='__main__':main()
