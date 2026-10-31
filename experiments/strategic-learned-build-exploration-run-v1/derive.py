"""New source/policy epoch over the unchanged qualified schema5 native runtime."""
import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;EXP=HERE.parent
PARENT=EXP/'strategic-learned-economy-run-v1'
def once(t,a,b):
    assert t.count(a)==1,(a,t.count(a));return t.replace(a,b,1)
def main():
    files=('pipeline_common.py','collect_episode_v5.py','audit_contract.py','raw_events_v5.py','build_evidence.py','audit_game_v6.py','run_pipeline.py')
    parent={}
    for name in files:
        path=PARENT/name;t=path.read_text();parent[name]=hashlib.sha256(path.read_bytes()).hexdigest()
        if name=='pipeline_common.py':
            t=once(t,"BASE=EXPERIMENTS/'strategic-learned-economy-policy-v1'","BASE=EXPERIMENTS/'strategic-learned-build-exploration-policy-v1'")
            t=once(t,"EPOCH='strategic-learned-economy-build-training-v1'","EPOCH='strategic-learned-build-exploration-training-v1'")
            t=once(t,"DEFAULT_INITIAL=BASE/'cpu-01/build-initialization.pt'","DEFAULT_INITIAL=EXPERIMENTS/'strategic-learned-build-exploration-v1/calibration-01/build-offset-initialization.pt'")
            t=once(t,"INITIAL_SHA='0dbbc4735e217e39a55dcd2f398b945bcb9ea6490525c86645843a5f1ac313f6'","INITIAL_SHA='40eccc511fbc61b84b86e75b5aec102781835f2574db809f9a698f9a81db6d97'")
            t=once(t,"folders=(HERE,BASE,SUPPORT,EXPERIMENTS/'strategic-typed-training-v1',","folders=(HERE,BASE,SUPPORT,EXPERIMENTS/'strategic-learned-economy-policy-v1',EXPERIMENTS/'strategic-learned-build-exploration-v1',EXPERIMENTS/'strategic-typed-training-v1',")
        elif name=='collect_episode_v5.py':
            t=once(t,"BASE=LOCAL.parent/'strategic-learned-economy-policy-v1'","BASE=LOCAL.parent/'strategic-learned-build-exploration-policy-v1'")
        elif name=='audit_contract.py':
            t=once(t,'"strategic-learned-economy-policy-v1"','"strategic-learned-build-exploration-policy-v1"')
        elif name=='run_pipeline.py':
            t=once(t,'default=2026102600','default=2026102800')
            t=once(t,'First build batch must use the explicit schema5 migration initialization','Exploration batch must use the registered build-offset initialization')
        (HERE/name).write_text(t)
    (HERE/'PARENT_SOURCES.json').write_text(json.dumps(parent,indent=2)+'\n')
if __name__=='__main__':main()
