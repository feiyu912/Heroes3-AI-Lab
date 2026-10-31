"""Reaudit actual mechanism raw then bind immutable native/catalog provenance."""
import argparse,importlib.util,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'strategic-learned-recruitment-policy-v2'))
from qualification import sha,BINDING,require_qualification
def main():
    p=argparse.ArgumentParser();p.add_argument('--raw',type=Path,required=True);p.add_argument('--native',type=Path,required=True)
    p.add_argument('--auditor',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();assert not BINDING.exists(),'Binding already exists; preserve registered epoch'
    spec=importlib.util.spec_from_file_location('_actual_catalog_qualifier',a.auditor)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    actual=m.audit_game(a.raw,a.native,mechanism=True)
    assert actual['passed'] and actual['same_turn_build_recruit_move_recruit_return_end_verified'] and actual['catalog_runtime_bound']
    plan=json.loads((a.raw/'PLAN.json').read_text());capsule=Path(plan['capsule'])
    source={str(Path(p).resolve()):h for p,h in actual['source_sha256'].items()}
    evidence={str((a.raw/p).resolve()):h for p,h in actual['raw_sha256'].items()}
    catalog=(a.raw/'agent/creature-catalog.json').resolve()
    assert evidence[str(catalog)]==actual['catalog_sha256']
    report=dict(actual,mechanism_only=True,training_samples=0,native_manifest_sha256=actual['compiled_manifest_sha256'],
        capsule_manifest_sha256=sha(capsule/'build-source-manifest.json'),native_artifacts={n:sha(capsule/'bin'/n) for n in ('vcmiclient','vcmiserver','libvcmi.so')},evidence_sha256=evidence)
    a.out.mkdir(parents=True,exist_ok=False);report_path=(a.out/'MECHANISM_QUALIFICATION.json').resolve()
    report_path.write_text(json.dumps(report,indent=2)+'\n')
    binding=dict(schema='recruitment-native-qualification-binding-v1',catalog_path=str(catalog),catalog_sha256=actual['catalog_sha256'],
        native_directory=str(a.native.resolve()),native_manifest_sha256=actual['compiled_manifest_sha256'],capsule_directory=str(capsule.resolve()),
        capsule_manifest_sha256=report['capsule_manifest_sha256'],native_artifacts=report['native_artifacts'],mechanism_report=str(report_path),mechanism_report_sha256=sha(report_path),
        per_game_auditor=str(a.auditor.resolve()),per_game_auditor_sha256=sha(a.auditor),evidence_sha256=evidence,
        auditor_dependencies={**source,str(a.auditor.resolve()):sha(a.auditor)})
    BINDING.write_text(json.dumps(binding,indent=2)+'\n');require_qualification()
    print(json.dumps(dict(passed=True,binding=str(BINDING),catalog_sha256=actual['catalog_sha256'],optimizer_steps=0)))
if __name__=='__main__':main()
