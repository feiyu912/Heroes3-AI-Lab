"""Verify all completed takeover episodes, including preserved code snapshots."""
import gzip
import json
from pathlib import Path
from events_provenance import digest
from battle_outcome_audit import audit


def main():
    here=Path(__file__).resolve().parent
    roots=[here/'runs']+[here/n/'runs' for n in ('curriculum-v1','curriculum-v2','curriculum-v3','planner-pilot-v1','replay-branch-probe-v1')]
    rows=[]
    for root in roots:
        for path in sorted(root.rglob('*.json')):
            if path.parent.name in ('source-snapshots','source-snapshot'):
                continue
            record=json.loads(path.read_text())
            if not isinstance(record,dict) or record.get('schema')!='human-events-v3.1':
                continue
            assert record['completed'] and record['terminated'] and not record['truncated']
            assert record['invalid_actions']==0 and record['terminal_outcome']['result_type']==0
            audit([record])
            assert digest(record['archive'])==record['archive_sha256']
            restored=0
            for source,expected in record['frozen_artifacts'].items():
                if digest(source)==expected:
                    continue
                candidates=[path.parent/'source-snapshots'/(expected+'-'+Path(source).name),
                            path.parent/'source-snapshot'/Path(source).name]
                assert any(p.exists() and digest(p)==expected for p in candidates), 'Missing old source: '+source
                restored+=1
            with gzip.open(record['archive'],'rt') as f:
                raw=json.load(f)
            assert len(raw['batches'])==record['steps']+1
            assert len(raw['transitions'])==record['steps']
            assert all(t['executed_action'] in t['legal_actions'] and t['action_window']['status']=='matched'
                       and not t['demonstration_gate']['eligible_for_bc'] for t in raw['transitions'])
            end=[e for e in raw['batches'][-1]['events'] if e['kind']==3]
            assert len(end)==1 and end[0]['winner']==record['terminal_outcome']['winner']
            rows.append(dict(path=str(path),summary_sha256=digest(path),archive_sha256=record['archive_sha256'],
                             steps=record['steps'],historical_sources_restored_from_snapshot=restored))
    result=dict(passed=True,episodes=len(rows),steps=sum(r['steps'] for r in rows),
                normal=len(rows),illegal=0,truncated=0,bc_eligible=0,rows=rows)
    (here/'DELIVERY_AUDIT.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k!='rows'}))


if __name__=='__main__':
    main()
