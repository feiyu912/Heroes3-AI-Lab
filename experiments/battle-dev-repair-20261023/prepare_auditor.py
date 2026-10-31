"""Isolated adapters to prior independent raw reviewers; no original edits."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent.parent
old=ROOT/'experiments/battle-training-continuation-20261020/final-independent-01/audit_final.py'
text=old.read_text();before="returned['next_obs']['terminal_outcome']==g['terminal_outcome']";assert before in text
text=text.replace(before,"json.loads(json.dumps(returned['next_obs']['terminal_outcome']))==g['terminal_outcome']")
(HERE/'legacy_audit.py').write_text(text)
source=ROOT/'experiments/battle-resume-20261023/audit_final.py';text=source.read_text()
replacements=[
 ('import curriculum,restore_learner as restore,support',"sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'battle-resume-20261023'))\nimport curriculum,restore_learner as restore,support"),
 ("p.add_argument('--run',type=Path,required=True);","p.add_argument('--run',type=Path,required=True);p.add_argument('--dev-run',type=Path,required=True);"),
 ("result=read(a.run/'RESULT.json')","result=read(a.dev_run/'RESULT.json')"),
 ("HERE=Path(__file__).resolve().parent;ROOT=HERE.parent.parent","REPAIR=Path(__file__).resolve().parent;HERE=REPAIR.parent/'battle-resume-20261023';ROOT=HERE.parent.parent"),
 ("HERE.parent/'battle-training-continuation-20261020/final-independent-01/audit_final.py'","REPAIR/'legacy_audit.py'"),
 ("dev=old.review_dev(a.run,adapted,paths)","dev=old.review_dev(a.dev_run,adapted,paths)"),
 ("independent_raw96games_recomputed=True,","independent_raw96games_recomputed=True,recovered_old_games=result['recovered_games'],new_native_DEV_games=result['new_native_games'],")]
for before,after in replacements:
    assert before in text,before;text=text.replace(before,after)
(Path(__file__).parent/'audit_final.py').write_text(text)
(Path(__file__).parent/'AUDITOR_DERIVATION.json').write_text(json.dumps({str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [old,source]},indent=2)+'\n')
