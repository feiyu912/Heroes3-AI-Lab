"""Reaudit completed mechanism games and bind coverage proof; never starts a game or learner."""
import argparse,hashlib,json,os,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from pipeline_common import CAPSULE,NATIVE,validate_capsule,sha
def main():
 p=argparse.ArgumentParser();p.add_argument('--case',type=Path,action='append',required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 validate_capsule(CAPSULE);a.out.mkdir(parents=True,exist_ok=False);cases=[];groups=[]
 for index,case in enumerate(a.case):
  case=case.resolve();dest=a.out/f'raw-audit-{index:02d}'
  subprocess.run([sys.executable,str(HERE/'audit_game_v6.py'),str(case),str(dest)],check=True,stdout=(a.out/f'audit-{index:02d}.log').open('w'),stderr=subprocess.STDOUT,env=dict(os.environ,CUDA_VISIBLE_DEVICES=''))
  audit=json.loads((dest/'AUDIT.json').read_text());assert audit['whole_game_valid'] and audit['prewindow_evidence_verified']
  groups.extend(audit['prewindow_evidence']['groups']);cases.append(dict(folder=str(case),audit=str(dest/'AUDIT.json'),audit_sha256=sha(dest/'AUDIT.json'),raw_sha256=audit['raw_sha256'],flow_raw_sha256=audit['prewindow_evidence']['raw_sha256'],prewindow_transfers=audit['prewindow_evidence']['prewindow_transfers'],training_samples=0,optimizer_steps=0))
 passed=any(g['prewindow_transfers']>=2 for g in groups) and any(g['rescue_hire_same_turn'] for g in groups)
 report=dict(passed=passed,mechanism_only=True,candidate_manifest_sha256=sha(NATIVE/'CANDIDATE_MANIFEST.json'),flow_contract_sha256=sha(NATIVE/'FLOW_CONTRACT.json'),capsule_directory=str(CAPSULE),capsule_manifest_sha256=sha(CAPSULE/'build-source-manifest.json'),native_artifacts={n:sha(CAPSULE/'bin'/n) for n in ['vcmiclient','vcmiserver','libvcmi.so']},cases=cases,multistack_before_first_policy_proven=any(g['prewindow_transfers']>=2 for g in groups),rescue_hire_then_free_transfer_before_first_policy_proven=any(g['rescue_hire_same_turn'] for g in groups),flow_auditor_dependencies={str(p):sha(p) for p in HERE.glob('*.py')},directly_observed_complete_arrange_payload=False,limitation='Actual ID/player/type/received/server stack mutation/success/ACK directly observed. Donor/recipient and whole-stack quantities uniquely reconstructed from own public stack snapshots and matching compiled helper; slot IDs/what are not directly logged. No hidden-state inspection.',training_samples=0,optimizer_steps=0)
 (a.out/'QUALIFICATION.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ['cases','flow_auditor_dependencies']},indent=2))
 if not passed:raise SystemExit('Strict whole-game audit passed but required multistack/rescue coverage not observed; not qualified')
if __name__=='__main__':main()
