#!/usr/bin/env python3
"""Validate a NEW server-barrier smoke and prepare restore command. Launches nothing."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys
import traceback

ROOT=Path(__file__).resolve().parent.parent
V2=ROOT/'strategic-policy-v2'
sys.path.insert(0,str(V2))
from encoder import validate


def read(path):return json.loads(Path(path).read_text())
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def lines(path):return [json.loads(line) for line in Path(path).read_text().splitlines()]


def prepare(original_agent,checkpoint,out,server_manifest,source_tree):
    original_agent=original_agent.resolve();checkpoint=checkpoint.resolve()
    summary=read(original_agent/'smoke-result.json');smoke_plan=read(original_agent/'smoke-plan.json')
    native=summary['native_result'];native_dir=Path(native['run_dir']);native_plan=read(native_dir/'plan.json')
    assert summary['passed'] and native['completed'] and native['inputs_unchanged'],'Fresh original smoke must fully pass'
    assert summary['mode'] in ('new-policy','policy'),'Restore wrapper only supports fresh NEW-model policy smoke'
    assert not native['config'].get('save_file'),'Original must start a fresh map, not an earlier restore'
    ready=read(original_agent/'broker-ready.json');checkpoint_sha=sha(checkpoint)
    assert checkpoint_sha==smoke_plan['checkpoint_sha256'],'Requested checkpoint differs from original smoke'
    assert ready['model_version']=='sha256:'+checkpoint_sha and ready['mode'] in ('new-policy','policy')
    assert 'New visible threat/supply encoder' in ready['model_scope'],'Legacy/script policy cannot silently become new-policy'
    manifest=read(server_manifest)
    required=('server/CGameHandler.h','server/CGameHandler.cpp','server/battles/BattleProcessor.cpp')
    assert set(manifest)==set(required),'Explicit three-source server barrier manifest required'
    server_hashes={str(source_tree/path):sha(source_tree/path) for path in required}
    assert all(server_hashes[str(source_tree/path)]==manifest[path] for path in required),'Current server sources do not match required barrier manifest'
    log=(native_dir/'client.log').read_text(errors='replace')
    marker='Adventure battle barrier ready for player'
    assert marker in log,'Fresh original native log does not prove the new server battle barrier ran; v6/v7 are unsupported'
    frozen=dict(smoke_plan['code_sha256'],**native_plan['hashes'])
    changed=[path for path,value in frozen.items() if not Path(path).is_file() or sha(path)!=value]
    assert not changed,'Original/current native/source snapshot differs: '+', '.join(changed)
    save_files=native['save_files']
    candidates=[entry for entry in save_files if Path(entry['path']).name=='director-v5-initial.vsgm1']
    assert len(candidates)==1 and save_files[0]==candidates[0],'Restore tool currently selects first save; unique initial save must be first'
    saved=candidates[0];save=Path(saved['path'])
    assert sha(save)==saved['sha256'],'Original native turn-start save changed'
    head=save.read_bytes()[:15]
    assert head[:4]==b'VCMI' and head[8:15]==b'VCMISVG','Invalid native save header'
    trace=lines(native_dir/'strategy-trace.jsonl');counts=Counter(row['event'] for row in trace)
    assert trace[0]['event']=='turn_start' and trace[0]['own_turn']==1,'Only fresh first-own-turn boundary is supported'
    assert all(counts[name]==0 for name in ('move_failed','economy_failed','query_failed')),'Original has native failed action/query events'
    assert not any(text in log for text in ('has to answer queries','Got false in applying','external policy failed'))
    assert not re.search(r'(?:QueryReply|query reply).*?(?:failed|success=0|result=0)',log,re.I)
    requests=sorted(original_agent.glob('request-????????.json'));actions=sorted(original_agent.glob('action-????????.json'))
    choices=lines(native_dir/'strategy-decisions.jsonl')
    assert len(requests)==len(actions)==len(choices)>0
    for number,(request_path,choice) in enumerate(zip(requests,choices),1):
        request=validate(read(request_path),number)
        action=int((original_agent/f'action-{number:08d}.json').read_text())
        assert 0<=action<len(request['candidates']) and choice['selected_candidate']==action
        assert choice['candidates']==request['candidates']
        assert all(choice[key]==request[key] for key in ('player','day','hero','from'))
        assert choice['destination']==request['candidates'][action]['position'] and choice['step']==request['candidates'][action]['next']
    # The original comparison tool itself takes an unused output path. This
    # preparation directory already exists, so use its not-yet-created child.
    restore_output=out.resolve()/'restore-run'
    command=[sys.executable,str(ROOT/'verify_native_restore_v3.py'),'--original-agent',str(original_agent),
             '--checkpoint',str(checkpoint),'--out',str(restore_output)]
    dependencies={str(path):sha(path) for path in (ROOT/'verify_native_restore_v3.py',V2/'legacy.py',V2/'supply_policy.py')}
    frozen.update(server_hashes);frozen.update(dependencies);frozen[str(checkpoint)]=checkpoint_sha;frozen[str(save)]=sha(save)
    return dict(preparation_passed=True,game_started=False,uses_shared_pool=False,restore_test_passed=False,
        required_native='Fresh same-runtime new-policy smoke with executed explicit post-request server battle barrier',
        server_barrier_manifest=str(server_manifest),server_source_hashes=server_hashes,
        original_agent=str(original_agent),original_native_dir=str(native_dir),original_request_count=len(requests),
        original_barrier_marker_count=log.count(marker),checkpoint_sha256=checkpoint_sha,
        native_save=dict(path=str(save),sha256=sha(save)),frozen_hashes=frozen,restore_command=command,
        must_remain_frozen_until_restore_finishes=True,
        scope='Native first-own-turn save with no active battle only. pendingBattleBarriers is transient and not serialized.',
        limitations='Preparation only, not a restore result. Native restore launches a game when the prepared command is explicitly executed. '
                    'Preserve source/runtime/model/save freezes; this is separate from PPO checkpoint recovery and cannot certify mid-battle/action resume.')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--original-agent',required=True,type=Path);parser.add_argument('--checkpoint',required=True,type=Path)
    parser.add_argument('--out',required=True,type=Path)
    parser.add_argument('--server-manifest',type=Path,default=ROOT/'adv-server-battle-barrier-v1/installed-source-sha256.json')
    parser.add_argument('--source-tree',type=Path,default=Path('/root/heroes3-ai-lab/src/vcmi-adv'))
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    try:
        report=prepare(args.original_agent,args.checkpoint,args.out,args.server_manifest,args.source_tree)
    except Exception as error:
        report=dict(preparation_passed=False,game_started=False,uses_shared_pool=False,restore_test_passed=False,
                    error=repr(error),context=traceback.format_exc())
    report['preparer_sha256']=sha(Path(__file__))
    (args.out/'PREPARATION.json').write_text(json.dumps(report,indent=2))
    (args.out/Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    print(json.dumps({key:report.get(key) for key in ('preparation_passed','game_started','error','restore_command')},indent=2))
    return 0 if report['preparation_passed'] else 1


if __name__=='__main__':raise SystemExit(main())
