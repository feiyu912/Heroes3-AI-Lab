"""CPU-only isolated draft: existing town stock transfer before schema5's spending window."""
import difflib,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
PARENT=HERE.parent/'strategic-learned-economy-native-v1'
CAP=Path('/root/heroes3-ai-lab/evaluations/strategic-learned-economy-build-capsule-01')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def once(text,a,b):assert text.count(a)==1;return text.replace(a,b,1)
def main():
 manifest=json.loads((PARENT/'CANDIDATE_MANIFEST.json').read_text());compiled=json.loads((CAP/'build-source-manifest.json').read_text())
 original={}
 for rel,e in manifest['files'].items():
  p=PARENT/'candidate'/rel
  assert sha(p)==e['candidate_sha256']==compiled[rel]['sha256']
  original[rel]=p.read_text()
 text=dict(original)
 rel='AI/DirectorAI/CDirectorAI.cpp';t=text[rel]
 start=t.index('\t\tconst auto * army = town->getUpperArmy();',t.index('bool CDirectorAI::issueEconomy()'))
 end=t.index('\t\tfor(int level =',start)
 block=t[start:end]
 helper='bool CDirectorAI::issueFreeArmyTransfer()\n{\n\tfor(const auto * town : cb->getTownsInfo())\n\t{\n'+block+'\t}\n\treturn false;\n}\n\n'
 t=once(t,' if((!learnedBuildEnabled || !buildWindow.open || cb->getHeroesInfo().empty()) && issueEconomy()) return;',
  ' if(learnedBuildEnabled && buildWindow.open && issueFreeArmyTransfer()) return;\n if((!learnedBuildEnabled || !buildWindow.open || cb->getHeroesInfo().empty()) && issueEconomy()) return;')
 t=once(t,'bool CDirectorAI::issueEconomy()\n{',helper+'bool CDirectorAI::issueEconomy()\n{')
 text[rel]=t
 rel='AI/DirectorAI/CDirectorAI.h';text[rel]=once(text[rel],'\tbool issueEconomy();','\tbool issueEconomy();\n\tbool issueFreeArmyTransfer();')
 entries={};diff=[]
 for rel,t in text.items():
  p=HERE/'candidate'/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(t)
  e=manifest['files'][rel];entries[rel]=dict(baseline_sha256=e['baseline_sha256'],parent_candidate_sha256=e['candidate_sha256'],candidate_sha256=sha(p))
  diff+=list(difflib.unified_diff(original[rel].splitlines(True),t.splitlines(True),fromfile='learned-economy-native-v1/'+rel,tofile='learned-economy-native-v2/'+rel))
 (HERE/'candidate.diff').write_text(''.join(diff))
 flow=json.loads((HERE/'FLOW_CONTRACT.json').read_text())
 assert flow['action_contract_sha256']==sha(PARENT/'CONTRACT.md')
 write(HERE/'CANDIDATE_MANIFEST.json',dict(schema='director-learned-economy-free-stock-prewindow-v2',parent_manifest_sha256=sha(PARENT/'CANDIDATE_MANIFEST.json'),compiled_parent_source_manifest_sha256=sha(CAP/'build-source-manifest.json'),contract_sha256=sha(PARENT/'CONTRACT.md'),flow_epoch=flow['flow_epoch'],flow_contract_sha256=sha(HERE/'FLOW_CONTRACT.json'),build_driver_sha256=sha(HERE/'build_capsule.py'),prepare_sha256=sha(Path(__file__)),files=entries,status='source-ready-not-native-qualified'))
 write(HERE/'CPU_REPORT.json',dict(passed=True,parent_nine_payload_match_actual_compiled_capsule=True,changed_files=[r for r in text if text[r]!=original[r]],old_transfer_block_preserved_in_issueEconomy=block in text['AI/DirectorAI/CDirectorAI.cpp'].split('bool CDirectorAI::issueEconomy()')[1],free_helper_uses_identical_legacy_block=block in helper,cpp_syntax_or_compile_run=False,native_builds=0,native_games=0,gpu_runs=0,optimizer_steps=0))
 print('Draft prepared: 9 payloads, only Director cpp/header changed; no compilation/native/GPU.')
if __name__=='__main__':main()
