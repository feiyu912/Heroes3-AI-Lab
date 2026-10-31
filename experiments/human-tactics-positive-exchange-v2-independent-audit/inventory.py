"""Archive integrity inventory; hashes existing G-drive evidence without copying."""
import argparse
import hashlib
import json
from pathlib import Path


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run',required=True);ap.add_argument('--output',required=True)
    args=ap.parse_args();run=Path(args.run);out=Path(args.output);assert not out.exists()
    summaries=sorted(p for p in (run/'runs/train').glob('*.json') if p.name!='PROTOCOL.json')
    assert len(summaries)==16
    union={};archives=[]
    for p in summaries:
        s=json.loads(p.read_text());archive=Path(s['archive'])
        assert archive==p.with_suffix('.json.gz') and sha(archive)==s['archive_sha256']
        assert s['completed'] and s['terminated'] and not s['truncated']
        archives.append(dict(summary=str(p),summary_sha256=sha(p),archive=str(archive),archive_sha256=sha(archive)))
        for source,h in s['frozen_artifacts'].items():
            if source in union:assert union[source]==h
            union[source]=h
    assert len(union)==31 and all(sha(p)==h for p,h in union.items())
    expected=json.loads((run/'PREPARE_CHECK_01.json').read_text())['default_launcher_plan']['frozen_artifacts']
    assert union==expected
    snapshots=sorted((run/'runs/train/source-snapshots').iterdir())
    for p in snapshots:
        assert p.is_file() and sha(p)==p.name[:64]
    snapnames={p.name for p in snapshots}
    for p,h in union.items():
        p=Path(p)
        if p.suffix in ('.py','.sh','.json'):assert h+'-'+p.name in snapnames
    records=[]
    for p in sorted(run.rglob('*')):
        if p.is_file():
            assert not p.name.endswith('.tmp') and '.partial.' not in p.name
            records.append(dict(path=str(p.relative_to(run)),bytes=p.stat().st_size,sha256=sha(p)))
    result=dict(passed=True,copied_files=0,root=str(run),summaries=16,gzip_archives=16,
        source_snapshots=len(snapshots),frozen_inputs_verified=len(union),
        matches_pre_execution_plan=True,all_files=len(records),total_bytes=sum(r['bytes'] for r in records),
        archive_bindings=archives,frozen_inputs=union,files=records,
        experiment_benefit_passed=False,bc_eligible=False,
        note='Integrity inventory of existing evidence, not a capability or benefit acceptance.')
    out.write_text(json.dumps(result,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k not in ('archive_bindings','frozen_inputs','files')}))


if __name__=='__main__':main()
