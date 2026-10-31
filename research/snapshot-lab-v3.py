"""Version the final lab changes and artifacts without overwriting V2 evidence."""
from pathlib import Path
import difflib
import hashlib
import json
import subprocess
import tarfile

root = Path('/mnt/g/Heroes3-AI-Lab')
research = root / 'research'
source = Path('/root/heroes3-ai-lab/src/gym')
groups = {'engine.tar.gz': [
    'AI/BattleAI/BattleAI.cpp', 'AI/BattleAI/BattleEvaluator.h',
    'AI/MMAI/BAI/v15/BAI_v15.cpp', 'AI/MMAI/schema/v15/types.h',
    'AI/MMAI/BAI/v15/supplementary_data_v15.h', 'AI/MMAI/BAI/v15/state_v15.h',
    'AI/MMAI/BAI/v15/state_v15.cpp', 'lib/VCMIDirs.cpp'],
    'gym.tar.gz': ['vcmi_gym/connectors/v15/threadconnector.cpp', 'vcmi_gym/envs/v15/vcmi_env.py']}
chunks = []
for archive, paths in groups.items():
    with tarfile.open(research / 'downloads' / archive) as bundle:
        prefix = bundle.getnames()[0].split('/')[0]
        for path in paths:
            original = bundle.extractfile(prefix + '/' + path).read().decode()
            relative = ('vcmi/' if archive == 'engine.tar.gz' else '') + path
            final = (source / relative).read_text()
            chunks.extend(difflib.unified_diff(original.splitlines(True), final.splitlines(True),
                                               fromfile='a/'+relative, tofile='b/'+relative))
(research / 'lab-v3-native.patch').write_text(''.join(chunks))
manifest = dict(date='2026-10-14', engine_commit='e956242503f465ae6ec0a62a3aeb2c4ea179db5c',
                gym_commit='11241d496db95541766498373e23245a67847a97',
                selected_workers=12, feature_schema='lab-candidates-v1/vcmi-v15',
                native_protocol='terminal-outcome-v1 + teacher-v1 + seeded-random-v1; matching rebuilt connector',
                cpu_dependencies=subprocess.check_output(['/root/heroes3-ai-lab/venv/bin/python','-m','pip','freeze'],text=True).splitlines(),
                gpu_dependencies=subprocess.check_output(['/root/heroes3-ai-lab/gpu-venv/bin/python','-m','pip','freeze'],text=True).splitlines(),
                files=[dict(path=str(p.relative_to(root)),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
                       for p in sorted(list(research.glob('*')) + list(root.glob('*.md')) + list(root.glob('*.ps1')))
                       if p.is_file() and p.suffix in ['.py','.sh','.ps1','.patch','.json','.md']
                       and p.name != 'runtime-manifest-v3.json'],
                model=json.loads((root/'models/selected-v3/manifest.json').read_text()),
                notes=['GPU trainer isolated from NumPy-only simulator workers',
                       'Exact callback random seed=engine seed+100000; independent replay passed',
                       'Old milestones preserved; early legacy checkpoints may lack CUDA RNG state',
                       'Runtime round limit30; wrapper step cap400; raw per-unit stats and hero spell actions incomplete'])
(research/'runtime-manifest-v3.json').write_text(json.dumps(manifest,indent=2))
print('Saved final reproducible native patch, dependencies and artifact hashes')
