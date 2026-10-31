"""New boundary epoch layered on the unchanged qualified transport/capsule gates."""
import importlib.util,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parent.parent;V1=HERE.parent/'strategic-refill-retention-qualification-20261025'
sys.path.insert(0,str(V1))
import common as parent
from common import PROFILE,RESOURCE,LEASE_SOURCE,REGISTRY_SOURCE,SUPPORT_SOURCE,CONTRACT,CONTRACT_SHA,leases,support,registry,load,sha,write,validate_capsule,verify_native_fds

def fixture(case):
 m=load(HERE/'FIXTURE_MANIFEST.json');f=m['fixtures'][case]
 assert sha(f['path'])==f['sha256'] and sha(m['source'])==m['source_sha256']
 assert sha(m['native_water_metadata'])==m['native_water_metadata_sha256']
 return m,f

def verify_source_freeze():
 parent.verify_source_freeze();pin=load(HERE/'SOURCE_FREEZE.json')
 assert pin['schema']=='refill-boundaries-source-freeze-v1'
 for filename,expected in pin['files'].items():assert sha(filename)==expected,'Boundary source changed: '+filename
 return pin

def old_selector():
 spec=importlib.util.spec_from_file_location('_frozen_refill_selector',V1/'selector.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
