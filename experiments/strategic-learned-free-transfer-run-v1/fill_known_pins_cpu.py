"""Read-only native capsule inspection; fills known draft pins without authorizing execution."""
import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;NATIVE=HERE.parent/'strategic-learned-economy-native-v2'
CAP=Path('/root/heroes3-ai-lab/evaluations/strategic-learned-economy-build-capsule-02')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    path=HERE/'DRAFT_BINDINGS.json';b=json.loads(path.read_text());assert b['native_run_allowed'] is False
    manifest=json.loads((NATIVE/'CANDIDATE_MANIFEST.json').read_text());att=json.loads((CAP/'EXECUTION.json').read_text());source=json.loads((CAP/'build-source-manifest.json').read_text())
    assert sha(NATIVE/'CANDIDATE_MANIFEST.json')=='7404ac1b26b12faeb393d28a2a44083c003ad950cbca5b45a749948e99c59fc9'
    assert sha(NATIVE/'FLOW_CONTRACT.json')=='32ff1ccd70f3a2e0d18b32f9772bf6b5d40a69fcc782b3104a964de0094e65c0'
    assert att['passed'] and att['accepted_binaries_restored'] and not att['rebuild_required']
    for rel,h in att['candidate_artifacts'].items():assert sha(CAP/rel)==h
    for rel,entry in manifest['files'].items():
        assert sha(NATIVE/'candidate'/rel)==sha(CAP/'source-snapshot'/rel)==source[rel]['sha256']==entry['candidate_sha256']
    b.update(native_candidate_directory=str(NATIVE),native_contract_sha256=manifest['contract_sha256'],
        native_manifest_schema=manifest['schema'],native_manifest_sha256=sha(NATIVE/'CANDIDATE_MANIFEST.json'),
        native_exact_payload_paths_and_sha256={r:e['candidate_sha256'] for r,e in manifest['files'].items()},
        flow_contract_sha256=sha(NATIVE/'FLOW_CONTRACT.json'),native_flow_epoch='learned-economy-free-existing-stock-prewindow-v2',
        native_audit_epoch='director-learned-economy-free-stock-prewindow-v2',qualified_capsule_directory=str(CAP),
        qualified_capsule_manifest_sha256=sha(CAP/'build-source-manifest.json'),
        qualified_native_binary_sha256={n:sha(CAP/'bin'/n) for n in ('vcmiclient','vcmiserver','libvcmi.so')})
    b.setdefault('flow_auditor_dependencies',{})
    assert b['native_run_allowed'] is False
    path.write_text(json.dumps(b,indent=2)+'\n')
    report=dict(passed_CPU_capsule_integrity=True,native_games=0,GPU_steps=0,optimizer_steps=0,
        native_run_allowed=False,prewindow_qualification_pending=True,actual_flow_parser_pending=True,
        capsule=str(CAP),capsule_manifest_sha256=b['qualified_capsule_manifest_sha256'],native_artifacts=b['qualified_native_binary_sha256'],
        candidate_manifest_sha256=b['native_manifest_sha256'],flow_contract_sha256=b['flow_contract_sha256'],bindings_sha256=sha(path))
    out=HERE/'capsule-pins-cpu-01';out.mkdir(exist_ok=False);(out/'AUDIT.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
