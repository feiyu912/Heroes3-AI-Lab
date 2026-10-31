"""Derive only physical ROOT/legacy SHA key lookup in an isolated helper."""
import difflib
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
PARENT = PROJECT / 'experiments/battle-terminal-credit-native-20261023/restore_learner.py'
PARENT_SHA = 'e06151039e1665742897e9381cab1f51b3598d51db1e2f050d4315b0de5b7df9'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert sha(PARENT) == PARENT_SHA
    original = PARENT.read_text()
    source = original
    substitutions = {
        'import copy,hashlib,importlib.util,io,json,math,random': 'import copy,hashlib,importlib.util,io,json,math,random,os',
        "ROOT=Path('/mnt/g/Heroes3-AI-Lab')": "ROOT=Path(os.environ['HEROES3_PROJECT_ROOT']).resolve()",
        "bundle['frozen_inputs']['input_sha256'].get(str(p))==sha(p)":
            "bundle['frozen_inputs']['input_sha256'].get('/mnt/g/Heroes3-AI-Lab/research/'+p.name)==sha(p)",
    }
    for before, after in substitutions.items():
        assert source.count(before) == 1
        source = source.replace(before, after, 1)
    output = HERE / 'restore_learner_ubuntu.py'
    with output.open('x') as stream:
        stream.write(source)
    lease_source = HERE.parent / 'leases.py'
    lease_output = HERE / 'leases.py'
    with lease_output.open('xb') as stream:
        stream.write(lease_source.read_bytes())
    (HERE / 'path-adaptation.diff').write_text(''.join(difflib.unified_diff(original.splitlines(True), source.splitlines(True),
        fromfile='frozen/restore_learner.py', tofile='isolated/restore_learner_ubuntu.py')))
    assert sha(PARENT) == PARENT_SHA
    report = dict(passed=True, source_derivation_only=True, parent_path=str(PARENT), parent_sha256=PARENT_SHA,
                  parent_unchanged=True, derived_path=str(output), derived_sha256=sha(output),
                  substitutions=list(substitutions.items()), legacy_frozen_source_keys_preserved=True,
                  lease_source=str(lease_source), lease_source_sha256=sha(lease_source),
                  lease_copy_sha256=sha(lease_output), derive_script_sha256=sha(Path(__file__)),
                  optimizer_steps=0, GPU_operations=0, native_games=0)
    (HERE / 'DERIVATION.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
