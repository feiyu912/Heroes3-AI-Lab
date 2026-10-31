"""New model/source bindings; same already exercised CPU native evaluation."""
import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
PARENT=HERE.parent.parent/'strategic-learned-economy-run-v1/dev-tools'
def once(t,a,b):
    assert t.count(a)==1,(a,t.count(a));return t.replace(a,b,1)
sources={}
for name in ('collect_cpu.py','evaluate_dev.py'):
    path=PARENT/name;t=path.read_text();sources[name]=hashlib.sha256(path.read_bytes()).hexdigest()
    if name=='collect_cpu.py':
        t=once(t,"BASE=LOCAL.parent/'strategic-learned-economy-policy-v1'","BASE=LOCAL.parent/'strategic-learned-build-exploration-policy-v1'")
    else:
        t=once(t,"INITIAL_SHA='0dbbc4735e217e39a55dcd2f398b945bcb9ea6490525c86645843a5f1ac313f6'","INITIAL_SHA='40eccc511fbc61b84b86e75b5aec102781835f2574db809f9a698f9a81db6d97'")
        t=once(t,"TRAINED_SHA='34a6a86ea74d727338388db74e0ab3b9e16ec85e45ef46313757b1ac814538bc'","TRAINED_SHA='d27d282bbcdaf1f1bf47f13b4b44c40ee1cd82639bedd47db90da5fd6c0da1d2'")
        t=once(t,'2026102700+len(jobs)','2026102900+len(jobs)')
        t=once(t,'learned-build-same-window-cpu-dev-v1','learned-build-exploration-same-window-cpu-dev-v1')
    (HERE/name).write_text(t)
(HERE/'PARENT_SOURCES.json').write_text(json.dumps(sources,indent=2)+'\n')
