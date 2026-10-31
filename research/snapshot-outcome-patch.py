"""Capture the final outcome/isolation changes against pinned source archives."""
import difflib
import tarfile
from pathlib import Path

workspace = Path('/mnt/g/Heroes3-AI-Lab/research')
source = Path('/root/heroes3-ai-lab/src/gym')
groups = {
    'engine.tar.gz': [
        'AI/MMAI/schema/v15/types.h',
        'AI/MMAI/BAI/v15/supplementary_data_v15.h',
        'AI/MMAI/BAI/v15/state_v15.h',
        'AI/MMAI/BAI/v15/state_v15.cpp',
        'lib/VCMIDirs.cpp',
    ],
    'gym.tar.gz': [
        'vcmi_gym/connectors/v15/threadconnector.cpp',
        'vcmi_gym/envs/v15/vcmi_env.py',
    ],
}
chunks = []
for archive, paths in groups.items():
    with tarfile.open(workspace / 'downloads' / archive) as bundle:
        prefix = bundle.getnames()[0].split('/')[0]
        for path in paths:
            original = bundle.extractfile(prefix + '/' + path).read().decode()
            relative = ('vcmi/' if archive == 'engine.tar.gz' else '') + path
            final = (source / relative).read_text()
            chunks.extend(difflib.unified_diff(
                original.splitlines(True), final.splitlines(True),
                fromfile='a/' + relative, tofile='b/' + relative,
            ))
(workspace / 'outcome-isolation.patch').write_text(''.join(chunks))
print('Saved final outcome/isolation patch.')
