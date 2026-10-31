"""Seed the actual v15 connector random callback, not the CLI-only agent."""
from pathlib import Path
import tarfile

root = Path('/root/heroes3-ai-lab/src/gym')
with tarfile.open('/mnt/g/Heroes3-AI-Lab/research/downloads/engine.tar.gz') as archive:
    prefix = archive.getnames()[0].split('/')[0]
    for name in ['agent-v15.h', 'agent-v15.cpp']:
        relative = 'ML/user_agents/' + name
        path = root / 'vcmi' / relative
        if 'randomGenerator' in path.read_text():
            path.write_bytes(archive.extractfile(prefix + '/' + relative).read())
path = root / 'vcmi_gym/connectors/v15/threadconnector.cpp'
text = path.read_text()
old = '        std::random_device rd;\n        std::mt19937 gen(rd());'
new = '''        static thread_local std::mt19937 gen{[] {
            const char * seed = std::getenv("LAB_RANDOM_POLICY_SEED");
            return seed ? static_cast<std::mt19937::result_type>(std::stoul(seed)) : 0u;
        }()};'''
if old in text:
    assert text.count(old) == 1
    text = text.replace(old, new)
    text = text.replace('#include <random>', '#include <random>\n#include <cstdlib>')
    path.write_text(text)
else:
    assert new in text
print('Actual v15 random legal-action callback now uses a persistent seeded generator')
