"""Static derivation and plan checks; never invokes compilation or native execution."""
import ast,difflib,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;PARENT=HERE.parent/'strategic-learned-economy-native-v1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def tree(p):return ast.parse(p.read_text())
def fn(t,n):return next(x for x in t.body if isinstance(x,ast.FunctionDef) and x.name==n)
def dump(x):return ast.dump(x,include_attributes=False)
def main():
 for p in HERE.glob('*.py'):tree(p)
 old=tree(PARENT/'build_capsule.py');new=tree(HERE/'build_capsule.py')
 for name in ['build','remove_added']:assert dump(fn(old,name))==dump(fn(new,name))
 def locked(t):return next(x for x in fn(t,'execute').body if isinstance(x,ast.With))
 assert dump(locked(old))==dump(locked(new)), 'mutation/build/restore locked body must remain exact v1'
 manifest=json.loads((HERE/'CANDIDATE_MANIFEST.json').read_text());plan=json.loads((HERE/'build-plan-01/PLAN.json').read_text())
 assert plan['execute'] is False and plan['nine_payload_inputs_checked'] is True
 assert plan['candidate_manifest_sha256']==sha(HERE/'CANDIDATE_MANIFEST.json')
 assert plan['flow_contract_sha256']==sha(HERE/'FLOW_CONTRACT.json')
 assert plan['candidate_files']=={p:e['candidate_sha256'] for p,e in manifest['files'].items()}
 cpp=(HERE/'candidate/AI/DirectorAI/CDirectorAI.cpp').read_text();parent=(PARENT/'candidate/AI/DirectorAI/CDirectorAI.cpp').read_text()
 start=parent.index('\t\tconst auto * army = town->getUpperArmy();',parent.index('bool CDirectorAI::issueEconomy()'));end=parent.index('\t\tfor(int level =',start);block=parent[start:end]
 assert cpp.count(block)==2 and parent.count(block)==1
 assert cpp.split('bool CDirectorAI::issueEconomy()')[1]==parent.split('bool CDirectorAI::issueEconomy()')[1], 'all original economy and following source must stay exact'
 guard='!pendingQueries.empty() || !queryRequests.empty() || outstandingTyped || preparedTyped) return;'
 newcall='if(learnedBuildEnabled && buildWindow.open && issueFreeArmyTransfer()) return;'
 assert cpp.index(guard)<cpp.index(newcall)<cpp.index('if((!learnedBuildEnabled || !buildWindow.open || cb->getHeroesInfo().empty()) && issueEconomy()) return;')
 (HERE/'build-driver.diff').write_text(''.join(difflib.unified_diff((PARENT/'build_capsule.py').read_text().splitlines(True),(HERE/'build_capsule.py').read_text().splitlines(True),fromfile='v1/build_capsule.py',tofile='v2/build_capsule.py')))
 report=json.loads((HERE/'CPU_REPORT.json').read_text());report.update(python_ast_passed=True,default_plan_executed=True,plan_took_no_locks=True,build_and_restore_locked_body_ast_exact_v1=True,full_original_issueEconomy_and_following_source_exact=True,prewindow_call_after_full_guard=True,manifest_sha256=sha(HERE/'CANDIDATE_MANIFEST.json'),flow_contract_sha256=sha(HERE/'FLOW_CONTRACT.json'),driver_sha256=sha(HERE/'build_capsule.py'),cpp_syntax_or_compile_run=False)
 (HERE/'CPU_REPORT.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(report,indent=2))
if __name__=='__main__':main()
