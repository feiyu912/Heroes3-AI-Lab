"""Bind the pinned independent raw-native auditor to production schema6 epoch."""
import importlib.util,json,sys
from pathlib import Path
from pipeline_common import audit_metadata,require_qualification,sha
def main():
    work=Path(sys.argv[1]);out=Path(sys.argv[2]);b=require_qualification()
    spec=importlib.util.spec_from_file_location('_actual_recruit_raw_auditor',b['per_game_auditor'])
    auditor=importlib.util.module_from_spec(spec);spec.loader.exec_module(auditor)
    result=auditor.audit_game(work,Path(b['native_directory']),mechanism=False)
    assert result['compiled_manifest_sha256']==b['native_manifest_sha256'] and result['catalog_sha256']==b['catalog_sha256']
    result.update(audit_metadata())
    result.update(candidate_manifest_sha256=result['compiled_manifest_sha256'],compiled_native_epoch_proven=True,
        event_contract_valid=True,contract_errors=[],owned_player=json.loads((work/'PLAN.json').read_text())['owned_player'])
    proposals=[json.loads(x) for x in (work/'agent/typed-broker.jsonl').read_text().splitlines()]
    events=[json.loads(x) for x in (work/'typed.jsonl').read_text().splitlines()]
    assert len(proposals)==result['actual_decisions_checked']
    for number,proposal in enumerate(proposals,1):
        assert proposal['request']==json.loads((work/f'agent/request-{number:08d}.json').read_text())
        assert proposal['response']==json.loads((work/f'agent/action-{number:08d}.json').read_text())
    trace=[json.loads(x) for x in (work/'strategy-trace.jsonl').read_text().splitlines()]
    ending=[x for x in trace if x['event'] in ('victory','defeat')]
    assert len(ending)==1 and ending[0]['player']==result['owned_player']
    own='red' if result['owned_player']==0 else 'blue'
    result['winner']=own if ending[0]['event']=='victory' else ('blue' if own=='red' else 'red')
    result['counts']=dict(new_policy_decisions=len(proposals),policy_builds=sum(p['response']['op']=='build' for p in proposals),
        policy_recruits=sum(p['response']['op']=='recruit' for p in proposals),automatic_end_turns=sum(e['event']=='automatic_end_turn' for e in events))
    for relative in ('agent/typed-broker.jsonl','strategy-trace.jsonl','strategy-decisions.jsonl','build-packs.jsonl'):
        result['raw_sha256'][relative]=sha(work/relative)
    out.mkdir(parents=True,exist_ok=False)
    (out/'AUDIT.json').write_text(json.dumps(result,indent=2)+'\n')
    (out/'events.jsonl').write_text((work/'typed.jsonl').read_text())
    print(json.dumps({k:v for k,v in result.items() if k not in ('checks','drain','raw_sha256','source_sha256')},indent=2))
    return 0
if __name__=='__main__':raise SystemExit(main())
