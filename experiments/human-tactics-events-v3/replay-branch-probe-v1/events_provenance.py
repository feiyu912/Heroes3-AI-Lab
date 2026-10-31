"""Freeze exact reused runtime and new runner inputs; do not mutate old code."""
import hashlib
import json
from pathlib import Path

RUNTIME = Path('/root/heroes3-ai-lab-events-v2')


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def freeze(case, scenario_file):
    here = Path(__file__).resolve().parent
    paths = set(here.glob('*.py')) | {Path(scenario_file), here / 'run-events-lab.sh'}
    paths.add(here / 'PLAN.md')
    paths.update(RUNTIME / 'src/gym/vcmi' / n for n in (
        'AI/MMAI/BAI/v15/BAI_v15.cpp', 'AI/BattleAI/BattleEvaluator.cpp',
        'AI/BattleAI/BattleExchangeVariant.cpp', 'AI/BattleAI/BattleAI.cpp'))
    paths.update(RUNTIME / 'src/gym/vcmi/rel/bin' / n for n in
                 ('libvcmi.so', 'libmlclient.so', 'libmlserverplugin.so', 'vcmiserver'))
    paths.update(RUNTIME / 'src/gym/vcmi_gym/connectors/rel' / n for n in
                 ('connector_v15.so', 'exporter_v15.so'))
    paths.add(RUNTIME / 'data/vcmi/Mods/ML/Content/heroes.json')
    paths.add(RUNTIME / 'onnxruntime/lib/libonnxruntime.so')
    path = Path(case.get('map_path', str(RUNTIME / 'data/vcmi/Maps' / case['map'])))
    assert digest(path) == case['sha256']
    paths.add(path)
    return {str(p): digest(p) for p in sorted(paths)}


def verify(frozen):
    for p, expected in frozen.items():
        assert digest(p) == expected, 'Frozen artifact changed: ' + p
