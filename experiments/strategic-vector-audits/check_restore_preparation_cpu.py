"""Synthetic-only positive/negative admission tests; no restore/native process."""
import argparse
import copy
import json
from pathlib import Path

from prepare_native_turnstart_restore import prepare,sha,ROOT,V2


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',required=True,type=Path);args=parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=False)
    (args.out/'SYNTHETIC_ONLY.txt').write_text('Admission fixtures only. No game, GPU, real model or save loading occurred.\n')
    agent=args.out/'agent';native=args.out/'native';tree=args.out/'source';agent.mkdir();native.mkdir()
    manifest={}
    for name in ('server/CGameHandler.h','server/CGameHandler.cpp','server/battles/BattleProcessor.cpp'):
        path=tree/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('SYNTHETIC source manifest fixture\n');manifest[name]=sha(path)
    manifest_path=args.out/'server-manifest.json';manifest_path.write_text(json.dumps(manifest))
    checkpoint=args.out/'checkpoint.pt';checkpoint.write_bytes(b'SYNTHETIC checkpoint admission hash only')
    save=native/'director-v5-initial.vsgm1';save.write_bytes(b'VCMI'+bytes(4)+b'VCMISVG'+b'SYNTHETIC save admission header only')
    (native/'client.log').write_text('SYNTHETIC: Adventure battle barrier ready for player red\n')
    (native/'strategy-trace.jsonl').write_text(json.dumps(dict(event='turn_start',own_turn=1))+'\n')
    request=json.loads((V2/'fixtures/visible-request.json').read_text())
    (agent/'request-00000001.json').write_text(json.dumps(request));(agent/'action-00000001.json').write_text('0\n')
    choice=dict(request,selected_candidate=0,destination=request['candidates'][0]['position'],step=request['candidates'][0]['next'])
    (native/'strategy-decisions.jsonl').write_text(json.dumps(choice)+'\n')
    native_result=dict(completed=True,inputs_unchanged=True,run_dir=str(native.resolve()),config=dict(save_file=''),
                       save_files=[dict(path=str(save.resolve()),sha256=sha(save))])
    summary=dict(passed=True,mode='new-policy',native_result=native_result,SYNTHETIC_ONLY=True)
    (agent/'smoke-result.json').write_text(json.dumps(summary))
    (agent/'smoke-plan.json').write_text(json.dumps(dict(code_sha256={},checkpoint_sha256=sha(checkpoint))))
    (agent/'broker-ready.json').write_text(json.dumps(dict(mode='new-policy',model_version='sha256:'+sha(checkpoint),
        model_scope='New visible threat/supply encoder; SYNTHETIC admission fixture')))
    (native/'plan.json').write_text(json.dumps(dict(hashes={})))
    accepted=prepare(agent,checkpoint,args.out,manifest_path,tree)
    assert accepted['preparation_passed'] and not accepted['game_started'] and not accepted['restore_test_passed']
    assert accepted['restore_command'][-1]==str(args.out.resolve()/'restore-run')
    rejected=[]
    tests=('legacy_mode','wrong_checkpoint','missing_barrier_marker','ambiguous_initial_save','native_failure')
    for test in tests:
        current=copy.deepcopy(summary)
        (native/'client.log').write_text('SYNTHETIC: Adventure battle barrier ready for player red\n')
        (native/'strategy-trace.jsonl').write_text(json.dumps(dict(event='turn_start',own_turn=1))+'\n')
        candidate=checkpoint
        if test=='legacy_mode':current['mode']='legacy-policy'
        if test=='wrong_checkpoint':
            candidate=args.out/'other.pt';candidate.write_bytes(b'SYNTHETIC wrong checkpoint')
        if test=='missing_barrier_marker':(native/'client.log').write_text('SYNTHETIC old native no barrier\n')
        if test=='ambiguous_initial_save':current['native_result']['save_files'].append(copy.deepcopy(current['native_result']['save_files'][0]))
        if test=='native_failure':
            (native/'strategy-trace.jsonl').write_text(json.dumps(dict(event='turn_start',own_turn=1))+'\n'+json.dumps(dict(event='query_failed'))+'\n')
        (agent/'smoke-result.json').write_text(json.dumps(current))
        try:prepare(agent,candidate,args.out,manifest_path,tree)
        except AssertionError as error:rejected.append(dict(test=test,error=str(error)))
        else:raise AssertionError('Invalid admission accepted: '+test)
    report=dict(passed=True,synthetic_only=True,game_started=False,GPU_initialized=False,positive_preparation=True,
                restore_executed=False,invalid_cases_rejected=rejected,preparer_sha256=sha(ROOT/'strategic-vector-audits/prepare_native_turnstart_restore.py'))
    (args.out/'AUDIT.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))


if __name__=='__main__':main()
