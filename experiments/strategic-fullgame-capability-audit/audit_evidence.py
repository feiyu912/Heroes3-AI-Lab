"""Recheck isolated native source snapshots and existing training coverage only."""
import hashlib,json
from collections import Counter
from pathlib import Path
HERE=Path(__file__).resolve().parent
SOURCE=Path('/root/heroes3-ai-lab/src/vcmi-adv')
manifest=json.loads((HERE/'source-sha256.json').read_text())
changed=[];snapshot_differences=[]
for relative,digest in manifest.items():
    current=hashlib.sha256((SOURCE/relative).read_bytes()).hexdigest()
    snapshot=HERE/relative
    if relative.startswith('AI/DirectorAI/'):snapshot=HERE/Path(relative).name
    if current!=digest:changed.append(relative)
    if hashlib.sha256(snapshot.read_bytes()).hexdigest()!=digest:snapshot_differences.append(relative)
ROOT=HERE.parent/'strategic-vector-v1/native-cuda-boundary-clean-4env-01'
runs=[]
for stage in ('continuous-2','split-1','resume-2'):
    for batchpath in sorted((ROOT/stage).glob('update-*-wave-*/batch.json')):
        batch=json.loads(batchpath.read_text())
        # Native run directories are embedded in complete episode reports.
        def find(value):
            if isinstance(value,dict):
                if value.get('schema')=='adventure-run-v5':return [value]
                return sum((find(v) for v in value.values()),[])
            if isinstance(value,list):return sum((find(v) for v in value),[])
            return []
        for native in find(batch):
            run=Path(native['run_dir'])
            trace=[json.loads(line) for line in (run/'strategy-trace.jsonl').read_text().splitlines()]
            choices=[json.loads(line) for line in (run/'strategy-decisions.jsonl').read_text().splitlines()]
            runs.append({'stage':stage,'native_dir':str(run),'max_director_owned_heroes':max(len(r.get('heroes',[])) for r in trace),
                'decision_hero_ids':sorted({r['hero'] for r in choices}),
                'event_counts':dict(Counter(r['event'] for r in trace))})
assert not changed and not snapshot_differences
report={'read_only':True,'games_launched':0,'optimizer_steps':0,'isolated_source':str(SOURCE),
    'source_files':len(manifest),'changed_live_sources':changed,'snapshot_differences':snapshot_differences,
    'coverage':runs,'scope':'Source-proven capability boundaries and archived coverage; unexercised native meeting/transfer mechanisms are not certified.'}
(HERE/'AUDIT.json').write_text(json.dumps(report,indent=2))
print(json.dumps({'source_files':len(manifest),'runs':len(runs),'max_hero_count':max((r['max_director_owned_heroes'] for r in runs),default=None),
    'max_distinct_decision_heroes':max((len(r['decision_hero_ids']) for r in runs),default=None),'changed':changed},indent=2))
