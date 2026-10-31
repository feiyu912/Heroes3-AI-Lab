"""Derive unchanged per-game/raw/NN gates; change only registered DEV seed epoch."""
from pathlib import Path
import hashlib,json,shutil
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'battle-terminal-credit-native-20261023'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    assert not (HERE/'dev_raw_auditor.py').exists()
    parents={}
    for name in ('evaluate_policy_steps.py','step_evidence.py','dev_utils.py','dev_raw_auditor.py','replay_dev.py','leases.py'):
        src=OLD/name;parents[str(src)]=sha(src);text=src.read_text()
        if name=='dev_raw_auditor.py':
            assert text.count('2026107600')==1;text=text.replace('2026107600','2026109400')
        (HERE/name).write_text(text)
    (HERE/'DERIVATION.json').write_text(json.dumps(dict(parent_sha256=parents,raw_gate_changes=['expected seed base7600 to preregistered9400 only'],per_game_and_full_CPU_replay_unchanged=True,new_native_games=0,optimizer_steps=0),indent=2))
    print(json.dumps(dict(prepared=True,new_native_games=0,optimizer_steps=0)))
if __name__=='__main__':main()
