import hashlib
import json
from pathlib import Path
import shutil
import torch

root=Path('/mnt/g/Heroes3-AI-Lab');r=root/'research'
selection=json.loads((r/'challenge-final-selection.json').read_text())
result=json.loads((r/'CHALLENGE_RESULTS.json').read_text())
source=Path(selection['checkpoint']);folder=root/'models/challenge-v4';folder.mkdir(parents=True,exist_ok=True)
target=folder/'policy.pt';shutil.copyfile(source,target)
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert digest(source)==digest(target)
state=torch.load(target,map_location='cpu',weights_only=True)
continuation_mode=state.get('continuation_mode',state.get('finetuning_mode','heads'))
manifest=dict(checkpoint=str(target),source_checkpoint=str(source),sha256=digest(target),selection=selection,
    test=result['fresh_results'],origin=(state.get('source','Official v15 recovered weights') if selection['policy']=='recovered' else 'Lab BC/PPO model'),
    workers=24,scope=result['scope'],resume_available='optimizer_state_dict' in state,
    weights_reloadable=True,derivation=state.get('derivation'),
    continuation_optimizer='saved' if 'optimizer_state_dict' in state else 'fresh')
(folder/'manifest.json').write_text(json.dumps(manifest,indent=2))
previous=json.loads((r/'training-state.json').read_text(encoding='utf-8-sig'))
previous.update(workers=24,rollout=32,policy=selection['policy'],checkpoint=str(source),
    validation_report=selection['validation_report'],upstream_validation_report=selection['upstream_validation_report'],
    completed_updates=state.get('completed_updates',0),resume_available='optimizer_state_dict' in state,
    seed=state.get('seed',state.get('config',{}).get('seed',20261018)),opponents=state.get('config',{}).get('opponents',['BattleAI','MMAI_MODEL']),
    trainer_family='graph' if continuation_mode in ['last','all'] else selection['policy'],
    finetuning_mode=continuation_mode,selected_derivation=state.get('derivation'),training_config=state.get('config',{}),
    training_scenarios=state.get('config',{}).get('scenario_file',str(r/'scenarios-v2.json')),
    selection=selection['selection'],training_report='/mnt/g/Heroes3-AI-Lab/research/CHALLENGE_RESULTS.json',
    note='24 workers selected explicitly by user. Validation-selected competitive policy; fresh test excluded from selection. New battles start on continuation, not exact in-battle replay.')
(r/'training-state.json').write_text(json.dumps(previous,indent=2))
print('Selected policy saved with verified SHA256; continuation uses24 and correct policy family')
