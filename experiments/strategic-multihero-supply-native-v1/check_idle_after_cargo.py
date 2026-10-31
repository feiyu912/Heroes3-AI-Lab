"""Read-only idle integrity snapshot after the two partial supply probes."""
from pathlib import Path
source=Path(__file__).resolve().parent.parent/'strategic-request-bind-barrier-v2/check_idle.py'
text=source.read_text().replace('idle-after-proxy-abort-01.json','idle-after-cargo-01.json')
exec(compile(text,str(source)+'-aftercargo','exec'),{'__file__':__file__})
