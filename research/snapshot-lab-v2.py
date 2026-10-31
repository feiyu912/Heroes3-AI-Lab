"""Save reproducible combined native changes without replacing previous evidence."""
import difflib
import hashlib
import json
from pathlib import Path
import tarfile
import subprocess

workspace = Path('/mnt/g/Heroes3-AI-Lab/research')
source = Path('/root/heroes3-ai-lab/src/gym')
groups = {
    'engine.tar.gz': [
        'AI/BattleAI/BattleAI.cpp', 'AI/BattleAI/BattleEvaluator.h',
        'AI/MMAI/BAI/v15/BAI_v15.cpp', 'AI/MMAI/schema/v15/types.h',
        'AI/MMAI/BAI/v15/supplementary_data_v15.h',
        'AI/MMAI/BAI/v15/state_v15.h', 'AI/MMAI/BAI/v15/state_v15.cpp',
        'lib/VCMIDirs.cpp',
    ],
    'gym.tar.gz': ['vcmi_gym/connectors/v15/threadconnector.cpp',
                   'vcmi_gym/envs/v15/vcmi_env.py'],
}
chunks = []
for archive, paths in groups.items():
    with tarfile.open(workspace / 'downloads' / archive) as bundle:
        prefix = bundle.getnames()[0].split('/')[0]
        for path in paths:
            original = bundle.extractfile(prefix + '/' + path).read().decode()
            relative = ('vcmi/' if archive == 'engine.tar.gz' else '') + path
            final = (source / relative).read_text()
            chunks.extend(difflib.unified_diff(original.splitlines(True), final.splitlines(True),
                                               fromfile='a/' + relative, tofile='b/' + relative))
patch = workspace / 'lab-v2-native.patch'
patch.write_text(''.join(chunks))
manifest = dict(date='2026-10-14',
                engine_commit='e956242503f465ae6ec0a62a3aeb2c4ea179db5c',
                gym_commit='11241d496db95541766498373e23245a67847a97',
                protocol='lab-terminal-outcome-v1 + lab-teacher-v1; matching rebuilt connector required',
                selected_workers=12,
                dependencies=subprocess.check_output(['/root/heroes3-ai-lab/venv/bin/python', '-m', 'pip', 'freeze'], text=True).splitlines(),
                files=[dict(path=str(p.relative_to(workspace)), sha256=hashlib.sha256(p.read_bytes()).hexdigest())
                       for p in sorted(workspace.glob('*')) if p.suffix in ['.py', '.sh', '.patch']])
(workspace / 'runtime-manifest-v2.json').write_text(json.dumps(manifest, indent=2))
print('Saved lab-v2-native.patch and runtime-manifest-v2.json')
