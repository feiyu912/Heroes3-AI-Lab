"""Materialize exact TRAIN selection/seeds/weights; does not run environments."""
import collections,hashlib,importlib.util,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent.parent;OLD=ROOT/'experiments/battle-training-continuation-20261020/curriculum.py'
s=importlib.util.spec_from_file_location('_approved_curriculum',OLD);curriculum=importlib.util.module_from_spec(s);s.loader.exec_module(curriculum)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
source=ROOT/'research/diverse-curriculum.json';registration=curriculum.registered(source);phases=[];weights=collections.Counter()
for phase in range(4):
    rows=[]
    for row in registration['phases'][phase]:
        item=dict(row,seed=2026106800+phase*1000+row['slot'],drain_sampling_seed=2026106980+phase*16+row['slot'],admitted_transitions=64,suffix_native_transitions=64,suffix_loss_weight=0)
        path=Path('/root/heroes3-ai-lab/data/vcmi/Maps')/row['map'];assert sha(path)==row['map_sha256']
        assert row['scenario_index']<192;weights[(row['scenario_index'],row['role'],row['opponent'])]+=64;rows.append(item)
    phases.append(rows)
assert len(weights)==64 and set(weights.values())=={64} and len({k[0] for k in weights})==16
report=dict(passed=True,stage='CPU registration only',common_parent_sha256='443863dd26ea0daaed17cd01ab3dd44a6a16544efac73c96a89839f5b72c0e20',registration_seed=2026102016,phases=phases,per_arm=dict(admitted=4096,suffix_native=4096,total_native=8192,planned_Adam=1024),all64_case_role_opponent_cells_weight64=True,unique_TRAIN_cases=16,DEV_read=False,source_sha256={str(p):sha(p) for p in [Path(__file__),OLD,source,HERE/'PLAN.md']},new_native_games=0,GPU_operations=0,optimizer_steps=0)
(HERE/'REGISTERED_CURRICULUM.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(passed=True,TRAIN_cases=16,cells=64,admitted=4096,suffix=4096)))
