"""events-v2 provenance: freeze/verify artifacts of the ISOLATED runtime.

Derivative of the frozen research/evaluation_provenance.py (reused read-only
by the main pipeline). Semantics identical; paths root at the events-v2
runtime so the original lab artifacts are neither required nor touched.
"""
import hashlib
import json
from pathlib import Path

RUNTIME = Path('/root/heroes3-ai-lab-events-v2')


def digest(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def freeze(args):
    paths = {Path(args.scenario_file)}
    runtime = RUNTIME / 'src/gym'
    paths.update(runtime / 'vcmi/rel/bin' / name
                 for name in ['libvcmi.so', 'libmlclient.so', 'libmlserverplugin.so'])
    paths.update(runtime / 'vcmi_gym/connectors/rel' / name
                 for name in ['connector_v15.so', 'exporter_v15.so'])
    paths.add(RUNTIME / 'onnxruntime/lib/libonnxruntime.so')
    paths.add(RUNTIME / 'data/vcmi/Mods/ML/Content/heroes.json')
    code = Path(__file__).parent
    paths.update(code / name for name in [
        'run_episode_events.py', 'events_provenance.py', 'experts_events.py',
        'generate_scenarios.py', 'apply_native_patch.py'])
    if any(p in ['model', 'recovered'] for p in args.policies):
        paths.add(Path(args.checkpoint))
    cases = json.loads(Path(args.scenario_file).read_text())
    for index in args.scenarios:
        case = cases[index]
        path = RUNTIME / 'data/vcmi/Maps' / case['map']
        checksum = digest(path)
        if case.get('sha256'):
            assert checksum == case['sha256'], f'Map differs from scenario manifest: {path}'
        paths.add(path)
    return {str(p): digest(p) for p in sorted(paths)}


def verify(frozen):
    for path, expected in frozen.items():
        assert digest(path) == expected, f'Evaluation artifact changed during run: {path}'
