"""Check actual inherited locks before replacing this process with the native client."""
import json,os,sys
from pathlib import Path
from common import leases,write
proof=leases.verify_pair()
write(Path(os.environ['REFILL_NATIVE_LEASE_PROOF']),proof)
assert Path(sys.argv[1]).name=='vcmiclient'
for entry in json.loads(os.environ['TERMINAL_CREDIT_LEASES']):os.set_inheritable(entry['fd'],True)
os.execv(sys.argv[1],sys.argv[1:])
