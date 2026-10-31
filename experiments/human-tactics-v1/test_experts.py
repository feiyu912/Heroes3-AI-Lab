"""Independent tactical safety examples before using the policy for rollouts."""
from types import SimpleNamespace
from experts import coverage_score
from lab_io import atomic_json
from pathlib import Path

units = [SimpleNamespace(IS_ENEMY=1, VALUE_REL=100),
         SimpleNamespace(IS_ENEMY=1, VALUE_REL=80),
         SimpleNamespace(IS_ENEMY=0, VALUE_REL=250)]
assert coverage_score([0, 1], units) == 180
assert coverage_score([0, 1, 2], units) == -70
assert coverage_score([0, 0, 1], units) == 180
assert coverage_score([2], units) == -250
atomic_json(Path(__file__).with_name('expert-unit-check.json'), dict(passed=True,
    checks=['friendly fire reverses a tempting two-target attack', 'two-hex targets deduplicated',
            'enemy-only secondary target increases coverage'],
    scope='Arithmetic safety fixtures only; real legal action and outcome tests still required before expert strength claims'))
print('Coverage safety fixtures passed; no strength claim')
