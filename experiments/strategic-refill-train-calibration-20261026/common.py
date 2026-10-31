"""Registered TRAIN cells and explicit Ubuntu paths; prepare does not grant execution."""
import hashlib, importlib.util, json, os
from pathlib import Path
HERE=Path(__file__).resolve().parent
EXP=HERE.parent
PROJECT=EXP.parent
PROFILE=Path('/home/kaicheng/Documents/Codex/2026-10-24/hello/outputs/Heroes3-Native-20261025')
LAB=PROFILE/'heroes3-ai-lab'
RESOURCE=Path('/home/kaicheng/Documents/Codex/2026-10-24/hello/outputs/WSL迁出-20261025/files/root/heroes3-ai-lab/evaluations')
CAPSULE_ROOT=Path('/home/kaicheng/Documents/Codex/2026-10-24/hello/outputs/Heroes3-Refill-Capsules-20261025-01')
INITIAL=EXP/'strategic-learned-recruitment-policy-v3/initialization-02/recruitment-initialization.pt'
INITIAL_SHA='1510149ef1c2c896e3125e6468e9e58234a8bfc9e4278ad239f9d6840e1c62a1'
CATALOG=EXP/'strategic-refill-paired-build-20261026/native-01/candidate-positive/agent/creature-catalog.json'
CATALOG_SHA='031d9200e3efa40e2dd82363547d6f39e8f1381296f000d8b83b158ca663eb1e'
MAP_MANIFEST=EXP/'strategic-active-opponent-learning-20261024/MAP_MANIFEST.json'
MAP_MANIFEST_SHA='88eae3414ec9d7d7dae9bd8390eb4bf3a6ae5dd59fcb87e807d7d45a51702327'
EPOCH='refill-single-factor-fixed-TRAIN-calibration-v1'
REGISTERED={2026104402:('takeover-v2-train-01-mines',0),2026104403:('takeover-v2-train-01-mines',1),2026104406:('takeover-v2-train-02-development',0),2026104407:('takeover-v2-train-02-development',1)}
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as stream:
  for block in iter(lambda:stream.read(1<<20),b''):h.update(block)
 return h.hexdigest()
def load(p):return json.loads(Path(p).read_text())
def write(p,v):Path(p).write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n')
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
mechanism=module('_calibration_capsule_support',EXP/'strategic-refill-retention-qualification-20261025/common.py')
support=mechanism.support
registry=mechanism.registry
leases=mechanism.leases
CONTRACT=mechanism.CONTRACT
validate_capsule=mechanism.validate_capsule
verify_native_fds=mechanism.verify_native_fds
def resolve_legacy(path):
 value=str(path)
 for prefix,root in (('/mnt/g/Heroes3-AI-Lab',PROJECT),('/root/heroes3-ai-lab',LAB)):
  if value==prefix or value.startswith(prefix+'/'):return root/value[len(prefix):].lstrip('/')
 raise ValueError('Unregistered legacy path: '+value)
def variant(seed):
 assert sha(MAP_MANIFEST)==MAP_MANIFEST_SHA
 name,player=REGISTERED[seed]
 found=[e for e in load(MAP_MANIFEST)['variants'] if (e['source_map'],e['owned_player'],e['multiplier'])==(name,player,4)]
 assert len(found)==1
 e=dict(found[0]);e['original_manifest_path']=e['path'];e['path']=str(resolve_legacy(e['path']))
 assert sha(e['path'])==e['sha256']
 return e
def sampling_seed(seed,map_name,player,opponent='Nullkiller2',logical_update=0):
 material=json.dumps(dict(seed=seed,map=map_name,player=player,opponent=opponent,logical_update=logical_update),sort_keys=True).encode()
 return int.from_bytes(hashlib.sha256(material).digest()[:8],'little')%(2**63-1)
def validate_job(arm,seed,checkpoint=INITIAL):
 assert arm in ('baseline','candidate') and seed in REGISTERED
 assert Path(checkpoint).resolve()==INITIAL.resolve() and sha(checkpoint)==INITIAL_SHA
 assert sha(CATALOG)==CATALOG_SHA
 return variant(seed)
def verify_freeze():
 f=load(HERE/'SOURCE_FREEZE.json')
 for path,expected in f['files'].items():assert sha(path)==expected,'Frozen calibration input changed: '+path
 return f
def require_native_admission():
 verify_freeze()
 path=HERE/'NATIVE_ADMISSION.json'
 assert path.is_file(),'Root qualification admission absent; native/GPU execution is closed'
 a=load(path)
 assert a['schema']=='refill-fixed-TRAIN-native-admission-v1' and a['passed'] is True
 assert a['source_freeze_sha256']==sha(HERE/'SOURCE_FREEZE.json') and a['full_boundaries_qualified'] is True
 assert a['purpose']=='bounded-first-wholegame-and-TRAIN-calibration' and a['PPO_allowed'] is False
 assert a['checkpoint_sha256']==INITIAL_SHA and a['catalog_sha256']==CATALOG_SHA
 assert a['evidence_sha256'] and all(sha(p)==h for p,h in a['evidence_sha256'].items())
 for arm in ('baseline','candidate'):
  c=CAPSULE_ROOT/arm;validate_capsule(c,arm)
  assert a['capsules'][arm]==dict(manifest_sha256=sha(c/'build-source-manifest.json'),attestation_sha256=sha(c/'BUILD_ATTESTATION.json'),binary_sha256=load(c/'binary-sha256.json'))
 return a
