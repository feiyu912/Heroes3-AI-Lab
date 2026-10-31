"""Version the committed-line observer fix without editing frozen training inputs."""
import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
sources=[HERE/n for n in ['collect_episode_v4.py','admit_episode_v4.py','train_update_v2.py','live_jsonl.py']]
before={str(p):sha(p) for p in sources};outputs={}
text=(HERE/'collect_episode_v4.py').read_text()
text=text.replace('from pathlib import Path\n','from pathlib import Path\nfrom live_jsonl import read as read_jsonl\n',1)
text=text.replace("inputs=[Path(__file__),source,BROKER", "inputs=[Path(__file__),HERE/'live_jsonl.py',source,BROKER",1)
old="path=work/'typed.jsonl';rows=[json.loads(s) for s in path.read_text().splitlines()] if path.exists() else []"
assert text.count(old)==1;text=text.replace(old,"rows=read_jsonl(work/'typed.jsonl')")
old="final_events=[json.loads(s) for s in (work/'typed.jsonl').read_text().splitlines()] if (work/'typed.jsonl').exists() else []"
assert text.count(old)==1;text=text.replace(old,"final_events=read_jsonl(work/'typed.jsonl',final=True)")
outputs['collect_episode_v5.py']=text
text=(HERE/'admit_episode_v4.py').read_text().replace('from collect_episode_v4 import','from collect_episode_v5 import')
outputs['admit_episode_v5.py']=text
text=(HERE/'train_update_v2.py').read_text().replace('from collect_episode_v4 import','from collect_episode_v5 import')
text=text.replace("'train_update_v2.py'","'train_update_v3.py'").replace("'collect_episode_v4.py'","'collect_episode_v5.py'").replace("'admit_episode_v4.py'","'admit_episode_v5.py','live_jsonl.py'")
text=text.replace("schema='typed-certified-single-env-ppo-training-v1'","schema='typed-certified-single-env-ppo-training-v2'")
needle="        update=0;collection_states={}"
assert text.count(needle)==1
text=text.replace(needle,"""        # Bind the actual admitted collector/observer to this protocol epoch.
        # Runtime identity alone cannot certify unchanged sampling tooling.
        for admission in admissions:
            paths=[Path(p) for p in admission['report']['input_sha256'] if p.endswith('/sampling-state.pt')]
            assert len(paths)==1
            collection_plan=json.loads((paths[0].parent.parent/'PLAN.json').read_text())
            for name in ['collect_episode_v5.py','live_jsonl.py','onpolicy_broker_v2.py','model_io.py']:
                path=str(HERE/name)
                assert collection_plan['hashes'].get(path)==config['sources'][path],'Collector/source epoch differs'
            admission_source=str(HERE/'admit_episode_v5.py')
            assert admission['report']['input_sha256'].get(admission_source)==config['sources'][admission_source],'Admission epoch differs'
        update=0;collection_states={}""")
outputs['train_update_v3.py']=text
for name,text in outputs.items():
    p=HERE/name;assert not p.exists();compile(text,str(p),'exec');p.write_text(text)
assert before=={str(p):sha(p) for p in sources}
report=dict(passed=True,unchanged_inputs=before,new_files={n:sha(HERE/n) for n in outputs},
    optimizer_steps=0,native_games=0,semantics='Committed JSONL observation only; new training protocol also binds actual admitted collector/admission sources. Old checkpoints cannot silently resume across this epoch.')
p=HERE/'collector-v5-preparation.json';assert not p.exists();p.write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
