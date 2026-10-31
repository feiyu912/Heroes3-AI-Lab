"""Read-only plan by default. --execute is for root's scheduled native run."""
import argparse
import json
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--execute', action='store_true', help='Start native games; root scheduling required')
    args = ap.parse_args()
    here = Path(__file__).resolve().parent
    from events_provenance import digest, freeze, verify
    manifest=json.loads((here/'FROZEN_SOURCES.json').read_text())
    assert all(digest(here/name)==value for name,value in manifest.items()), 'Prepared source changed'
    scenarios = here/'scenarios.json'
    cases = json.loads(scenarios.read_text())
    frozen = {}
    for index in (0, 1):
        assert cases[index]['split'] == 'train'
        frozen.update(freeze(cases[index], scenarios))
    verify(frozen)
    assert not (here/'runs/train').exists(), 'Refuse output reuse'
    print(json.dumps(dict(mode='execute' if args.execute else 'plan-only',
        games=16, seeds=[2026111801,2026111802], roles=['attacker','defender'],
        policies=['teacher','positive-exchange'], scenarios=[0,1],
        optimizer_steps=0, bc_eligible=False, frozen_artifacts=frozen), indent=2), flush=True)
    if args.execute:
        from run_pilot import main as run
        run()
        from audit_native import main as audit
        audit()


if __name__ == '__main__':
    main()
