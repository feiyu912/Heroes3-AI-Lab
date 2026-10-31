"""Bounded CPU import/guard and exact diff review; no resampling or training."""
import ast,difflib,hashlib,importlib.util,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;POLICY=HERE.parent;EXP=POLICY.parent;RUN=EXP/'strategic-learned-free-transfer-run-v1'
sys.path.insert(0,str(RUN));sys.path.insert(0,str(POLICY))
import model_io,pipeline_common,train_update_v3,admit_episode_v5
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    numeric=json.loads((POLICY/'initialization-01/AUDIT.json').read_text())
    model,_,digest=model_io.load_model(POLICY/'initialization-01/free-transfer-initialization.pt','cpu')
    assert digest==numeric['initialization_sha256'] and numeric['logits_and_critic_bitwise_exact_rows']==3000
    funcs=lambda p:{n.name:ast.dump(n,include_attributes=False) for n in ast.parse(p.read_text(encoding='utf-8-sig')).body if isinstance(n,ast.FunctionDef)}
    assert funcs(POLICY/'episode_balanced_ppo.py')==funcs(EXP/'strategic-learned-build-exploration-policy-v1/episode_balanced_ppo.py')
    guards=[]
    for label,fn in [('source_inputs',pipeline_common.source_inputs),('validate_capsule',lambda:pipeline_common.validate_capsule(Path('/not-qualified'))),('require_qualification',pipeline_common.require_qualification)]:
        try:fn()
        except ValueError as error:guards.append(dict(gate=label,rejected=True,error=str(error)))
        else:raise AssertionError(label)
    paths=[];diff=[]
    for current,parent in [(POLICY,EXP/'strategic-learned-build-exploration-policy-v1'),(RUN,EXP/'strategic-learned-build-exploration-run-v1')]:
        for p in sorted(current.glob('*.py')):
            old=parent/p.name
            paths.append(dict(path=str(p),sha256=sha(p),parent=str(old) if old.exists() else None,parent_sha256=sha(old) if old.exists() else None))
            before=old.read_text(encoding='utf-8-sig').splitlines(True) if old.exists() else []
            diff.extend(difflib.unified_diff(before,p.read_text(encoding='utf-8-sig').splitlines(True),fromfile=str(old),tofile=str(p)))
    (HERE/'CHANGES.diff').write_text(''.join(diff))
    report=dict(passed=True,status='reviewable_unqualified_draft_not_frozen',CPU_only=True,native_games=0,GPU_steps=0,optimizer_steps=0,
        initialization_sha256=digest,initialization_numeric_check_reused_not_rerun=True,training_and_admission_imports=True,
        PPO_function_AST_exact=True,native_guards=guards,source_diff_sha256=sha(HERE/'CHANGES.diff'),files=paths,
        pending='Root exact native-v2 capsule/source/proof pins plus actual per-game free-transfer verifier; no native permission is implied by this draft')
    (HERE/'AUDIT.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='files'},indent=2))
if __name__=='__main__':main()
