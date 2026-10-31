"""Catalog-byte compatibility is separate from native qualification admission."""
import functools
from common import CATALOG,CATALOG_SHA,HERE,module,require_native_admission,sha
CONTRACT_SHA='1f3a9d3c0777e31787df5e8cd2a2af1614d326a04f9b0f85ac0e83c3e42d15a3'
def require_qualification():
 a=require_native_admission()
 return dict(a,catalog_path=str(CATALOG),catalog_sha256=CATALOG_SHA)
@functools.lru_cache(maxsize=1)
def qualified_catalog():
 assert sha(CATALOG)==CATALOG_SHA
 encoder=module('_refill_registered_catalog_codec',HERE/'encoder.py')
 catalog=encoder.load_catalog(CATALOG,CATALOG_SHA)
 assert len(catalog['ids'])==150
 # This preserves checkpoint vocabulary only. Every execution entrypoint
 # separately requires the new root admission and actual runtime catalog.
 return catalog
