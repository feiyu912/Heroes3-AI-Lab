"""Schema6 mechanism-only bootstrap pins. No training qualification bypass exists here."""
import hashlib,importlib.util,json,os
from pathlib import Path
HERE=Path(__file__).resolve().parent;NATIVE=HERE.parent;EXP=NATIVE.parent
BASE=EXP/'strategic-learned-build-exploration-policy-v1';AUDITOR=HERE
CAPSULE=Path('/root/heroes3-ai-lab/evaluations/strategic-learned-recruitment-capsule-02')
MANIFEST_SHA='bec33627673811f3d995fa29bad836f23eee1f47aa70c2f5241af745f6e918c6'
CONTRACT_SHA='1f3a9d3c0777e31787df5e8cd2a2af1614d326a04f9b0f85ac0e83c3e42d15a3'
FIXTURE=HERE
FIXTURE_NAME='schema6-recruit-neighbor-mechanism-v1'
spec=importlib.util.spec_from_file_location('_schema6_mechanism_registry',EXP/'strategic-director-terminal-drain-v4/director_registry_v1.py');registry=importlib.util.module_from_spec(spec);spec.loader.exec_module(registry)
MARKER=registry.MARKER;EPOCH='schema6-recruit-mechanism-only-v1'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def audit_metadata():return dict(terminal_ack_scope='director',termination_registry_semantics='atomic-termination-closed-registry-v3',audit_epoch=EPOCH,pipeline_epoch=EPOCH,action_schema='strategy-candidates-v6',economy_epoch='learned-economy-build-recruit-v1',contract_sha256=CONTRACT_SHA,creature_catalog='actual-native-init-sidecar-sha-required',threat_replan='off',mechanism_only=True)
def validate_capsule(capsule):
 assert Path(capsule).resolve()==CAPSULE.resolve()
 assert sha(NATIVE/'CANDIDATE_MANIFEST.json')==MANIFEST_SHA and sha(NATIVE/'CONTRACT.md')==CONTRACT_SHA
 m=json.loads((NATIVE/'CANDIDATE_MANIFEST.json').read_text());a=json.loads((CAPSULE/'EXECUTION.json').read_text());s=json.loads((CAPSULE/'build-source-manifest.json').read_text())
 assert m['mode']=='build_recruit_v1' and m['build_allowed'] and len(m['files'])==9
 assert a['passed'] and a['accepted_sources_restored'] and a['accepted_binaries_restored'] and not a['rebuild_required']
 assert a['native_runs']==a['optimizer_steps']==0 and a['candidate_manifest_sha256']==MANIFEST_SHA
 assert all(sha(CAPSULE/r)==h for r,h in a['candidate_artifacts'].items())
 for r,e in m['files'].items():assert sha(NATIVE/'candidate'/r)==sha(CAPSULE/'source-snapshot'/r)==s[r]['sha256']==e['candidate_sha256']
 return a
def capsule_inputs(c):
 a=validate_capsule(c);return [CAPSULE/'EXECUTION.json',CAPSULE/'build-source-manifest.json']+[CAPSULE/r for r in sorted(a['candidate_artifacts'])]
def source_inputs():
 support=EXP/'multihero-mechanism-probe-v1/build-driver-frozen-03'
 paths=set(HERE.glob('*.py'));paths.update(support.glob('*.py'))
 paths.update([NATIVE/'CONTRACT.md',NATIVE/'CANDIDATE_MANIFEST.json',HERE/'PLAN.md',FIXTURE/'FIXTURE_MANIFEST.json',FIXTURE/'PLAN.md',FIXTURE/(FIXTURE_NAME+'.vmap'),EXP/'strategic-director-terminal-drain-v4/director_registry_v1.py'])
 paths.update(NATIVE/'candidate'/r for r in json.loads((NATIVE/'CANDIDATE_MANIFEST.json').read_text())['files'])
 return sorted(paths,key=str)
def clean_environment():
 assert os.environ.get('LAB_ADV_THREAT_REPLAN') in [None,'','off'] and not os.environ.get('LAB_ADV_MODE')
 assert os.environ.get('LAB_ADV_LEARNED_ECONOMY') in [None,'','build_recruit_v1']
def validate_native_epoch(*args):raise RuntimeError('Mechanism-only, not training admission')
def validate_cells(*args):raise RuntimeError('Mechanism-only, not a PPO curriculum')
