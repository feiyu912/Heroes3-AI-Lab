"""Derive transport/locks/runtime collector; replace NN with schema6 mechanism selector."""
import difflib,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;EXP=HERE.parent.parent
PARENT=EXP/'strategic-learned-economy-native-v2/qualification/fixture-01/collect_fixture.py'
def once(t,a,b):assert t.count(a)==1,(a,t.count(a));return t.replace(a,b,1)
def main():
 original=PARENT.read_text();t=original
 t=once(t,'LOCAL=DEV_TOOLS.parent','LOCAL=DEV_TOOLS')
 t=once(t,"LAB=Path('/root/heroes3-ai-lab');BROKER=HERE/'broker.py'","LAB=Path('/root/heroes3-ai-lab');BROKER=DEV_TOOLS/'selector.py'")
 t=t.replace('free-stock-rescue-stock-mechanism-v2-01','schema6-recruit-neighbor-mechanism-v1')
 t=once(t,'capsule,work,checkpoint=args.capsule,args.out,args.checkpoint','capsule,work=args.capsule,args.out')
 t=once(t,'    checkpoint=checkpoint.resolve();assert checkpoint.is_file()\n','')
 t=once(t,"source,BROKER,HERE/'model_io.py',checkpoint,capsule/'EXECUTION.json'","source,BROKER,capsule/'EXECUTION.json'")
 t=once(t,"classification='new_policy',checkpoint=str(checkpoint),sampling='CPU argmax',sampling_seed=sampling_seed","classification='diagnostic_only',checkpoint=None,sampling='scripted_actual_candidates_no_PPO',sampling_seed=None")
 t=once(t,"LAB_ADV_LEARNED_ECONOMY='build_v1'","LAB_ADV_LEARNED_ECONOMY='build_recruit_v1'")
 t=once(t,"[str(LAB/'venv/bin/python'),str(BROKER),'--mode','new-policy','--agent-dir',str(work/'agent'),'--checkpoint',str(checkpoint),","[str(LAB/'venv/bin/python'),str(BROKER),'--agent-dir',str(work/'agent'),")
 t=once(t,"assert ready['mode']=='new-policy' and ready['device']=='cpu' and ready['model_sha256']==sha(checkpoint)","assert ready['mode']=='schema6-mechanism-only' and ready['device']=='cpu' and ready['neural_network'] is False")
 t=once(t,";p.add_argument('--checkpoint',type=Path,required=True)",'')
 (HERE/'collect_mechanism.py').write_text(t)
 (HERE/'collector.diff').write_text(''.join(difflib.unified_diff(original.splitlines(True),t.splitlines(True),fromfile=str(PARENT),tofile='schema6/collect_mechanism.py')))
 (HERE/'DERIVATION.json').write_text(json.dumps(dict(parent=str(PARENT),parent_sha256=hashlib.sha256(PARENT.read_bytes()).hexdigest(),transport_and_lock_source='Frozen CPU fixture collector; no native execution during derivation',new_native_runs=0,new_gpu_runs=0),indent=2)+'\n')
 print('Schema6 collector derived; execution still requires actual pinned capsule attestation.')
if __name__=='__main__':main()
