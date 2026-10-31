"""Fixed final update4 after the predeclared same-optimizer continuation."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent;PARENT=HERE.parent/'dev-tools';sources={}
for name in ('collect_cpu.py','evaluate_dev.py'):
    p=PARENT/name;t=p.read_text();sources[name]=hashlib.sha256(p.read_bytes()).hexdigest()
    if name=='evaluate_dev.py':
        a="TRAINED_SHA='d27d282bbcdaf1f1bf47f13b4b44c40ee1cd82639bedd47db90da5fd6c0da1d2'"
        assert t.count(a)==1;t=t.replace(a,"TRAINED_SHA='24b8c3f3d5ddacd61e48bd87a526c1fd59b2a83eafbdacfe44bd5ddcfb5d3e6d'")
        a='2026102900+len(jobs)';assert t.count(a)==1;t=t.replace(a,'2026103300+len(jobs)')
        t=t.replace('learned-build-exploration-same-window-cpu-dev-v1','learned-build-exploration-update4-same-window-cpu-dev-v1')
    (HERE/name).write_text(t)
(HERE/'PARENT_SOURCES.json').write_text(json.dumps(sources,indent=2)+'\n')
