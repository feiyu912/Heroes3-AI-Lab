"""New named read-only accepted artifact/resource snapshot; old audit unchanged."""
from pathlib import Path
source=Path(__file__).resolve().parent.parent/'strategic-request-bind-barrier-v2/check_idle.py'
text=source.read_text().replace('idle-after-proxy-abort-01.json','idle-after-paired-03.json')
exec(compile(text,str(source)+'-paired03','exec'),{'__file__':__file__})
