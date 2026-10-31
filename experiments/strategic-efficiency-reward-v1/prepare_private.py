"""Generate minimal private adapters; frozen originals are never rewritten."""
from pathlib import Path
import difflib
HERE=Path(__file__).resolve().parent;EXPERIMENTS=HERE.parent
def replace_once(text,old,new):
    assert text.count(old)==1,(old,text.count(old));return text.replace(old,new,1)
def output(name,original,text):
    (HERE/name).write_text(text)
    (HERE/(name+'.diff')).write_text(''.join(difflib.unified_diff(original.splitlines(True),text.splitlines(True),fromfile='frozen/'+name,tofile='efficiency/'+name)))
def main():
    original=(EXPERIMENTS/'strategic-typed-training-v1/episode_balanced_ppo.py').read_text();text=original
    text=replace_once(text,'from collections import Counter, defaultdict','from collections import Counter, defaultdict\nfrom targets import validate_derived_sample, EPOCH, FORMULA')
    text=replace_once(text,"schema='strategic-typed-episode-balanced-choice-ppo-v1'","schema=EPOCH")
    text=replace_once(text,"reward='Completed native terminal win +1/loss -1 only; invalid batch must abort before update.'","reward=FORMULA")
    text=replace_once(text,"        if isinstance(reward, bool) or reward not in (-1., 1.):\n            raise ValueError('Only completed native +/-1 returns accepted; null timeout is not a loss')","        validate_derived_sample(sample)")
    output('efficiency_ppo.py',original,text)
    original=(EXPERIMENTS/'strategic-learning-mainline-20261020/native-pipeline/train_update_v3.py').read_text();text=original
    text=replace_once(text,"LOCAL=Path(__file__).resolve().parent","LOCAL=Path(__file__).resolve().parent.parent/'strategic-learning-mainline-20261020/native-pipeline'\nsys.path.append(str(LOCAL))")
    text=replace_once(text,'from load_admitted import load','from targets import load_targets, sources as target_sources, EPOCH as REWARD_EPOCH, SCHEMA as REWARD_SCHEMA, FORMULA, INITIAL_SHA, SEED, verify_targets')
    text=replace_once(text,'from episode_balanced_ppo import PROTOCOL,ppo_update,optimizer_steps','from efficiency_ppo import PROTOCOL,ppo_update,optimizer_steps')
    text=replace_once(text,"    sources=source_inputs()+[Path(__file__).resolve(),LOCAL/'run_pipeline.py']","    sources=[Path(p) for p in target_sources()]+[LOCAL/'run_pipeline.py']")
    text=replace_once(text,'schema=EPOCH,purpose=purpose','schema=REWARD_EPOCH,purpose=purpose')
    text=replace_once(text,"group.add_argument('--initialize',type=Path);group.add_argument('--resume',type=Path)","group.add_argument('--initialize',type=Path)\n    p.add_argument('--arm',choices=['control','treatment'],required=True);p.add_argument('--targets',type=Path,required=True)")
    text=replace_once(text,'default=2026102801','default=2026102300')
    text=replace_once(text,"    a.out.mkdir(parents=True,exist_ok=False);samples=[];episodes=[];admissions=[]","    a.resume=None\n    assert a.seed==SEED and sha(a.initialize)==INITIAL_SHA,'Registered identical parent and RNG seed required'\n    targets=verify_targets(a.targets)\n    expected=[e['admission_directory'] for e in targets['episodes']]\n    assert len(a.admission)==8 and {str(p.resolve()) for p in a.admission}==set(expected),'Exact shared eight admissions required'\n    a.admission=[Path(p) for p in expected]  # Identical rows under identical RNG in both arms.\n    a.out.mkdir(parents=True,exist_ok=False);samples=[];episodes=[];admissions=[]")
    text=replace_once(text,'rows,manifest,report=load(directory)','rows,manifest,report=load_targets(directory,a.targets,a.arm,verified=targets)')
    text=replace_once(text,'config=protocol(a.capsule,a.purpose,a.seed);config_sha=digest_json(config)',"config=protocol(a.capsule,a.purpose,a.seed)\n        config['derived_reward']=dict(schema=REWARD_SCHEMA,epoch=REWARD_EPOCH,formula=FORMULA,arm=a.arm,targets_sha256=sha(a.targets/'TARGETS.json'),shared_batch_sha256=targets['shared_batch_sha256'])\n        config_sha=digest_json(config)")
    text=replace_once(text,"'training_epoch':EPOCH","'training_epoch':REWARD_EPOCH,'reward_arm':a.arm")
    text=replace_once(text,"training_wins=sum(e['reward']==1 for e in episodes)","training_wins=sum(e['native_reward']==1 for e in episodes)")
    text=replace_once(text,"training_losses=sum(e['reward']==-1 for e in episodes)","training_losses=sum(e['native_reward']==-1 for e in episodes)")
    output('train_efficiency.py',original,text)
if __name__=='__main__':main()
