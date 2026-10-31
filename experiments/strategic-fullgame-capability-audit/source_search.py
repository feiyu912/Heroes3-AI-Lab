"""Read-only search of isolated runtime native source; no builds or games."""
import sys
from pathlib import Path
root=Path('/root/heroes3-ai-lab/src/vcmi-adv')
terms=sys.argv[1:]
for folder in ('lib','client','server'):
    for path in (root/folder).rglob('*'):
        if path.suffix not in ('.cpp','.h'):continue
        for number,line in enumerate(path.read_text(errors='replace').splitlines(),1):
            if any(term in line for term in terms):print(f'{path.relative_to(root)}:{number}: {line}')
