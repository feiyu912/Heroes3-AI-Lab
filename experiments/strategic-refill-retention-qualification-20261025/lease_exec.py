"""Verify inherited lock descriptions, then replace this process with native client."""
import json,os,sys
from pathlib import Path
from common import leases,write
entries=json.loads(os.environ['TERMINAL_CREDIT_LEASES'])
proof=leases.verify_pair()
write(Path(os.environ['REFILL_NATIVE_LEASE_PROOF']),proof)
assert sys.argv[1:] and Path(sys.argv[1]).name=='vcmiclient'
for entry in entries:os.set_inheritable(entry['fd'],True)
os.execv(sys.argv[1],sys.argv[1:])
