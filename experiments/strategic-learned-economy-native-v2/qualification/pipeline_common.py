"""Mechanism-only bootstrap. Intentionally has no training/admission/optimizer entry."""
import hashlib,importlib.util,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;NATIVE=HERE.parent;EXP=NATIVE.parent
OLD=EXP/'strategic-learned-build-exploration-run-v1';BASE=EXP/'strategic-learned-build-exploration-policy-v1'
spec=importlib.util.spec_from_file_location('_mechanism_legacy_common',OLD/'pipeline_common.py');legacy=importlib.util.module_from_spec(spec);spec.loader.exec_module(legacy)
registry=legacy.registry;MARKER=legacy.MARKER;EPOCH='free-stock-mechanism-only-v2';AUDIT_EPOCH='director-learned-economy-free-stock-prewindow-v2';AUDITOR=HERE
CAPSULE=Path('/root/heroes3-ai-lab/evaluations/strategic-learned-economy-build-capsule-02')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def audit_metadata():
 return dict(terminal_ack_scope='director',termination_registry_semantics='atomic-termination-closed-registry-v3',audit_epoch=AUDIT_EPOCH,pipeline_epoch=EPOCH,action_schema='strategy-candidates-v5',economy_epoch='learned-economy-build-v1',contract_sha256=sha(NATIVE.parent/'strategic-learned-economy-native-v1/CONTRACT.md'),native_flow_epoch='learned-economy-free-existing-stock-prewindow-v2',flow_contract_sha256=sha(NATIVE/'FLOW_CONTRACT.json'),threat_replan='off',mechanism_only=True)
def validate_capsule(capsule):
 assert Path(capsule).resolve()==CAPSULE.resolve()
 m=json.loads((NATIVE/'CANDIDATE_MANIFEST.json').read_text());a=json.loads((CAPSULE/'EXECUTION.json').read_text());s=json.loads((CAPSULE/'build-source-manifest.json').read_text())
 assert sha(NATIVE/'CANDIDATE_MANIFEST.json')=='7404ac1b26b12faeb393d28a2a44083c003ad950cbca5b45a749948e99c59fc9'
 assert sha(NATIVE/'FLOW_CONTRACT.json')=='32ff1ccd70f3a2e0d18b32f9772bf6b5d40a69fcc782b3104a964de0094e65c0'
 assert a['passed'] and a['accepted_binaries_restored'] and a['accepted_sources_restored'] and not a['rebuild_required'] and a['native_runs']==a['optimizer_steps']==0
 assert a['candidate_manifest_sha256']==sha(NATIVE/'CANDIDATE_MANIFEST.json') and a['flow_contract_sha256']==sha(NATIVE/'FLOW_CONTRACT.json')
 assert len(m['files'])==9 and all(sha(CAPSULE/r)==h for r,h in a['candidate_artifacts'].items())
 for r,e in m['files'].items():assert sha(NATIVE/'candidate'/r)==sha(CAPSULE/'source-snapshot'/r)==s[r]['sha256']==e['candidate_sha256']
 return a
def capsule_inputs(c):
 a=validate_capsule(c);return [CAPSULE/'EXECUTION.json',CAPSULE/'build-source-manifest.json']+[CAPSULE/r for r in sorted(a['candidate_artifacts'])]
def source_inputs():
 paths=set(legacy.source_inputs());paths.update(HERE.glob('*.py'));paths.update([NATIVE/'CANDIDATE_MANIFEST.json',NATIVE/'FLOW_CONTRACT.json'])
 paths.update(NATIVE/'candidate'/r for r in json.loads((NATIVE/'CANDIDATE_MANIFEST.json').read_text())['files'])
 return sorted(paths,key=str)
validate_native_epoch=legacy.validate_native_epoch
validate_cells=legacy.validate_cells
clean_environment=legacy.clean_environment
AUDITOR_SOURCES={n:OLD/n for n in ['audit_contract.py','raw_events_v5.py','build_evidence.py']}
AUDITOR_SOURCES.update({'audit_game_v6.py':HERE/'audit_game_v6.py','flow_evidence.py':HERE/'flow_evidence.py','pipeline_common.py':HERE/'pipeline_common.py','director_registry_v1.py':EXP/'strategic-director-terminal-drain-v4/director_registry_v1.py'})
