"""Bind the sole preselected new update1 to the existing fixed paired evaluator."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

here = Path(__file__).resolve().parent
run = here.parent
parent = run.parent / 'strategic-learned-build-exploration-run-v1/continuation-dev-tools'
sys.path.insert(0, str(run.parent / 'strategic-learned-free-transfer-policy-v1'))
from model_io import read

p = argparse.ArgumentParser()
p.add_argument('--checkpoint', type=Path, required=True)
a = p.parse_args()
bundle, digest = read(a.checkpoint)
assert bundle['training_updates'] == 1 and bundle['progress']['completed']
assert bundle['protocol']['schema'] == 'strategic-learned-free-transfer-training-v1'

def replace(text, old, new):
    assert text.count(old) == 1, old
    return text.replace(old, new)

source_hashes = {}
for name in ('collect_cpu.py', 'evaluate_dev.py'):
    source = parent / name
    text = source.read_text()
    source_hashes[name] = hashlib.sha256(source.read_bytes()).hexdigest()
    if name == 'collect_cpu.py':
        text = replace(text, "BASE=LOCAL.parent/'strategic-learned-build-exploration-policy-v1'",
                       "BASE=LOCAL.parent/'strategic-learned-free-transfer-policy-v1'")
        old = "    (work/'build-packs.jsonl').touch(exist_ok=False)"
        text = replace(text, old, "    env['LAB_ADV_THREAT_REPLAN']='off'\n" + old)
    else:
        text = replace(text, "INITIAL_SHA='40eccc511fbc61b84b86e75b5aec102781835f2574db809f9a698f9a81db6d97'",
                       "INITIAL_SHA='83319be8bde5d94eea839b1a889821449a7c1492c65da7ca6cde2deb63aab25a'")
        text = replace(text, "TRAINED_SHA='24b8c3f3d5ddacd61e48bd87a526c1fd59b2a83eafbdacfe44bd5ddcfb5d3e6d'",
                       f"TRAINED_SHA='{digest}'")
        text = replace(text, 'evaluations/strategic-learned-economy-build-capsule-01',
                       'evaluations/strategic-learned-economy-build-capsule-02')
        text = replace(text, '2026103300+len(jobs)', '2026103800+len(jobs)')
        text = replace(text, 'learned-build-exploration-update4-same-window-cpu-dev-v1',
                       'learned-free-stock-update1-same-window-cpu-dev-v1')
    target = here / name
    assert not target.exists()
    target.write_text(text)
(here / 'PLAN.md').write_text('Preselected sole update1 versus initialization83319, fixed16DEV/seed3800, same capsule02 and off mode. See ../PLAN.md. No finaltest, training or model selection.\n')
(here / 'BINDING.json').write_text(json.dumps(dict(parent_sources=source_hashes,
    candidate_checkpoint=str(a.checkpoint.resolve()), candidate_sha256=digest,
    preselected_training_updates=1), indent=2) + '\n')
