"""Freeze and verify the actual policies, scenario definitions and map files."""
import hashlib
import json
from pathlib import Path


def digest(path):
    result=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):result.update(chunk)
    return result.hexdigest()


def freeze(args):
    paths={Path(args.scenario_file)}
    runtime=Path('/root/heroes3-ai-lab/src/gym')
    paths.update(runtime/'vcmi/rel/bin'/name for name in ['libvcmi.so','libmlclient.so','libmlserverplugin.so'])
    paths.update(runtime/'vcmi_gym/connectors/rel'/name for name in ['connector_v15.so','exporter_v15.so'])
    paths.add(Path('/root/heroes3-ai-lab/onnxruntime/lib/libonnxruntime.so'))
    paths.add(Path('/root/heroes3-ai-lab/data/vcmi/Mods/ML/Content/heroes.json'))
    code=Path(__file__).parent
    paths.update(code/name for name in ['evaluate-battles.py','evaluation_provenance.py','evaluate-policy.py','lab-env.py','decision_model.py',
        'battle_features.py','recovered-graph.py','run-lab.sh','prepare-worker.py','observation_digest.py'])
    if any(p in ['model','recovered'] for p in args.policies):paths.add(Path(args.checkpoint))
    if 'upstream' in args.policies:
        paths.update(Path(args.upstream_model_dir)/(role+'.onnx') for role in ['attacker','defender'])
    if args.opponent=='MMAI_MODEL':
        assert args.opponent_model_template or args.opponent_model_dir,'A pinned native opponent model path is required'
        for role in ['attacker','defender']:
            name=args.opponent_model_template.format(role=role) if args.opponent_model_template else str(Path(args.opponent_model_dir)/(role+'.onnx'))
            path=Path('/root/heroes3-ai-lab/data/vcmi/Data')/name[5:] if name.startswith('DATA/') else Path(name)
            paths.add(path)
    cases=json.loads(Path(args.scenario_file).read_text())
    for index in args.scenarios:
        case=cases[index];path=Path('/root/heroes3-ai-lab/data/vcmi/Maps')/case['map']
        checksum=digest(path)
        if case.get('sha256'):assert checksum==case['sha256'],f'Map differs from scenario manifest: {path}'
        paths.add(path)
    return {str(p):digest(p) for p in sorted(paths)}


def verify(frozen):
    for path,expected in frozen.items():
        assert digest(path)==expected,f'Evaluation artifact changed during run: {path}'
