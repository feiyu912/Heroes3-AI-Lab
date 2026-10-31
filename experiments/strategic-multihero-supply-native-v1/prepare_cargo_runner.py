"""Derive a new runner without revising the recorded first-probe input."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
text=(HERE/'run_native.py').read_text()
text=text.replace("SUPPLY=HERE.parent/'strategic-multihero-supply-v2'", "SUPPLY=HERE.parent/'strategic-multihero-supply-v3'")
text=text.replace("HERE/'PLAN.md'", "HERE/'PLAN_CARGO_V2.md'")
text=text.replace("schema='scripted-supply-native-probe-v1'", "schema='scripted-supply-cargo-native-probe-v2'")
target=HERE/'run_native_cargo_v2.py';assert not target.exists();target.write_text(text);compile(text,str(target),'exec')
print('Prepared new cargo probe runner; zero native starts.')
