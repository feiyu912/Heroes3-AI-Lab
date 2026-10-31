"""Read-only acceptance snapshot check before explicitly authorized clean smoke."""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
root=HERE.parent.parent/'strategic-economy-v4/acceptance-06'
execution=json.loads((root/'EXECUTION.json').read_text())
assert execution['status']=='completed' and len(execution['episodes'])==12
assert execution['engineering_games']==4 and execution['nk_games']==8
assert all(e['mechanism_gate_passed'] and Path(e['audit']).is_file() for e in execution['episodes'])
protocol=json.loads((root/'PROTOCOL.json').read_text())
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()
changed=[name for name,value in protocol['frozen'].items() if sha(name)!=value]
assert not changed,changed
clean=HERE.parent.parent/'strategic-policy-v2/checkpoints/threat-supply-clean-prior-v3.pt'
assert sha(clean)=='6ced669638242eff327c2b29c3ab635528f07167a7959a2170985f2dc304e2c9'
record=dict(acceptance=str(root),completed_episodes=12,mechanism_gates=12,all_registered_inputs_unchanged=True,
    acceptance_execution_sha256=sha(root/'EXECUTION.json'),acceptance_protocol_sha256=sha(root/'PROTOCOL.json'),
    accepted_native_hashes={name:value for name,value in protocol['frozen'].items() if '/vcmi-adv-build/bin/'in name and Path(name).name in ('libvcmi.so','vcmiclient','vcmiserver')},
    cleanprior_sha256=sha(clean),parent_and_tactics_explicit_pool_release_received=True,
    note='This check starts no process, lock or GPU; parent authorization is recorded from the active chat, not inferred from elapsed time.')
output=HERE/'ACCEPTANCE06_LAUNCH_CHECK.json'
assert not output.exists()
output.write_text(json.dumps(record,indent=2));print(json.dumps(record,indent=2))
