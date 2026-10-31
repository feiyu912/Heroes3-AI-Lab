"""Frozen train-only schedules and immutable expert/reference dependencies."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import zipfile
import numpy as np

HERE=Path(__file__).resolve().parent
LAB=HERE.parents[1]
RESEARCH=LAB/'research'
CONSERVATIVE=HERE.parent/'conservative-ppo-v1'
BRANCH=Path('/mnt/g/Heroes3-AI-Lab-worktrees/human-expert-learning-v1/tools/human_expert')
PUBLIC='/root/heroes3-ai-lab/models/recovered-v15/initial-pair.pt'
COMMIT='5e3a7152d3ea8d3cc4626f4802480c3e50ac1fbf'
CACHE={}
sys.path.insert(0,str(RESEARCH))
sys.path.insert(0,str(CONSERVATIVE))


def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def digest(path):
    path=Path(path);stat=path.stat();key=(str(path),stat.st_size,stat.st_mtime_ns)
    if key not in CACHE:
        h=hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda:stream.read(1048576),b''):h.update(block)
        CACHE[key]=h.hexdigest()
    return CACHE[key]


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);sys.modules[name]=result;spec.loader.exec_module(result)
    return result


def git_commit():
    # Windows worktree gitdir is absolute Windows syntax; resolve without git writes.
    raw=(BRANCH.parents[1]/'.git').read_text().strip().split('gitdir: ',1)[1].replace('\\','/')
    gitdir=Path('/mnt/'+raw[0].lower()+raw[2:]) if len(raw)>2 and raw[1]==':' else Path(raw)
    head=(gitdir/'HEAD').read_text().strip()
    if head.startswith('ref: '):
        common=(gitdir/(gitdir/'commondir').read_text().strip()).resolve()
        return (common/head[5:]).read_text().strip()
    return head


def dependencies():
    paths=list(HERE.glob('*.py'))+[CONSERVATIVE/'reference_ppo.py',CONSERVATIVE/'cpu-math-check.json',
        BRANCH/'bootstrap.py',BRANCH/'opponents.py',LAB/'experiments/human-tactics-v1/experts.py',
        LAB/'experiments/expert-knowledge-v1/graph_observation_codec.py',
        RESEARCH/'recovered-graph.py',RESEARCH/'masked_ppo.py',RESEARCH/'decision_model.py',
        RESEARCH/'battle_features.py',RESEARCH/'full_graph_policy.py',RESEARCH/'gpu_opponent.py',
        RESEARCH/'vector_env.py',RESEARCH/'lab-env.py',RESEARCH/'run-lab.sh',RESEARCH/'prepare-worker.py']
    runtime=Path('/root/heroes3-ai-lab/src/gym')
    paths += [runtime/'vcmi/rel/bin'/name for name in ['libvcmi.so','libmlclient.so','libmlserverplugin.so']]
    paths += [runtime/'vcmi_gym/connectors/rel'/name for name in ['connector_v15.so','exporter_v15.so']]
    paths += [runtime/'vcmi_gym/envs/v15'/name for name in ['vcmi_env.py','pyconnector.py','decode.py']]
    paths += [Path('/root/heroes3-ai-lab/onnxruntime/lib/libonnxruntime.so'),
              Path('/root/heroes3-ai-lab/data/vcmi/Mods/ML/Content/heroes.json')]
    return {str(path):digest(path) for path in sorted(set(paths))}


def build_phases(seed=2026101604):
    ordinary=RESEARCH/'diverse-curriculum.json'
    tactical=LAB/'experiments/human-tactics-v1/scenarios.json'
    ordinary_cases=[case for case in read(ordinary) if case['split']=='train']
    tactical_cases=[case for case in read(tactical) if case['split']=='train']
    assert ordinary_cases and tactical_cases
    families=sorted({case['tactic_id'] for case in tactical_cases})
    assert families==['death-cloud','dragon-breath','retaliation-bait']
    phases=[]
    for phase in range(2):
        rng=np.random.default_rng(seed+phase*1777);rows=[]
        for category,count,pool,opponent in [('ordinary',12,ordinary_cases,'BattleAI'),
             ('expert',8,tactical_cases,'MMAI_GPU'),('history',4,ordinary_cases,'MMAI_MODEL')]:
            for index in range(count):
                role='attacker' if index%2==0 else 'defender'
                if category=='expert':
                    # Six workers guarantee each family x role; the extra pair rotates.
                    family=families[index//2] if index<6 else families[phase%len(families)]
                    candidates=[case for case in pool if case['tactic_id']==family]
                    case=candidates[int(rng.integers(len(candidates)))]
                else:
                    case=pool[int(rng.integers(len(pool)))]
                map_path=Path('/root/heroes3-ai-lab/data/vcmi/Maps')/case['map']
                sha=digest(map_path)
                assert not case.get('sha256') or case['sha256']==sha
                config=dict(map=case['map'],role=role,seed=seed+phase*1000+len(rows),opponent=opponent,
                    feature_version='upstream-graph-v15',step_cost=0.,loss_shaping=0.,max_steps=400,
                    initial_reset_once=True,worker_root='/root/heroes3-ai-lab/workers/expert-mixed-v1/'+str(phase)+'-'+str(len(rows)))
                if category=='history':
                    config['opponent_model']='DATA/MMAI/models/lab-upstream-'+('defender' if role=='attacker' else 'attacker')+'.onnx'
                rows.append(dict(category=category,tactic_id=case.get('tactic_id'),scenario_id=case['id'],split=case['split'],
                    source_file=str(ordinary if category!='expert' else tactical),map_sha256=sha,config=config))
        phases.append(rows)
    return phases,{str(ordinary):digest(ordinary),str(tactical):digest(tactical)}


def prepare_plan(path,checkpoint=PUBLIC,finalized=False,learning_rate=1e-5,updates=32,reference_checkpoint=PUBLIC):
    assert git_commit()==COMMIT
    phases,sources=build_phases()
    public_onnx={str(Path('/root/heroes3-ai-lab/data/vcmi/Data/MMAI/models')/('lab-upstream-'+role+'.onnx')):
        digest(Path('/root/heroes3-ai-lab/data/vcmi/Data/MMAI/models')/('lab-upstream-'+role+'.onnx')) for role in ['attacker','defender']}
    plan=dict(schema='expert-mixed-ppo-plan-v1',initial_checkpoint=str(checkpoint),initial_sha256=digest(checkpoint),
        reference_checkpoint=str(reference_checkpoint),reference_sha256=digest(reference_checkpoint),branch_commit=COMMIT,dependency_sha256=dependencies(),
        scenario_sources=sources,public_onnx_sha256=public_onnx,phases=phases,workers=24,
        updates=updates,rollout=32,phase_updates=16,seed=2026101604,learning_rate=learning_rate,gamma=1.,gae_lambda=.95,
        step_cost=0.,shaping=.5,entropy_coef=.005,reference_coef=.1,finetuning_mode='heads',
        categories=dict(ordinary=12,expert=8,history=4),reference='Independent frozen reference pair; default public, never ExpertOpponent.pair',
        source_quality='Q2 biased weak script opponent; no expert BC or human replay imported',
        finalized_for_execution=finalized,
        limitations='Prepared method, no training yet; mixed data and objective choices are not a single-factor ablation. Worker formation follows existing loose settings, not tight tactical fixtures.')
    assert updates==32 and 0<learning_rate<=1e-4, 'Current prepared curriculum has two 16-update phases only'
    rule_audit={}
    for phase in phases:
        for row in phase:
            path_=Path('/root/heroes3-ai-lab/data/vcmi/Maps')/row['config']['map']
            with zipfile.ZipFile(path_) as archive:
                heroes=[obj for obj in json.loads(archive.read('objects.json')).values() if obj.get('type')=='hero']
            assert len(heroes)==4
            for hero in heroes:
                options=hero['options']
                assert options['primarySkills']==dict(attack=0,defence=0,knowledge=0,spellpower=0)
                assert options['experience']==0 and options['secondarySkills']==[]
            rule_audit[str(path_)]=dict(neutral_heroes=4,primary_and_secondary_zero=True)
    settings=(RESEARCH/'lab-env.py').read_text()
    assert 'random_obstacles=0' in settings and 'mana_min=0' in settings and 'mana_max=0' in settings
    defaults=Path('/root/heroes3-ai-lab/src/gym/vcmi_gym/envs/v15/vcmi_env.py').read_text()
    assert 'tight_formation_chance: int = 0' in defaults and 'random_primary_skills: int = 0' in defaults
    plan['rules_audit']=dict(maps=rule_audit,worker_random_obstacles=0,mana_min=0,mana_max=0,
        formation='Existing worker default loose; tight_formation_chance not forwarded',
        active_magic_supported=False,arbitrary_hex_positions_supported=False)
    path=Path(path)
    if path.exists():assert read(path)==plan,'Existing immutable plan differs; choose a new plan filename, never silently replace initialization'
    else:
        path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('x') as stream:json.dump(plan,stream,indent=2)
    return plan


def verify_plan(plan):
    assert plan['branch_commit']==git_commit()==COMMIT
    assert digest(plan['initial_checkpoint'])==plan['initial_sha256']
    assert digest(plan['reference_checkpoint'])==plan['reference_sha256']
    for group in ['dependency_sha256','scenario_sources','public_onnx_sha256']:
        for path,sha in plan[group].items():assert digest(path)==sha,'Frozen input changed: '+path
    for phase in plan['phases']:
        assert len(phase)==24
        for category,count in plan['categories'].items():
            rows=[row for row in phase if row['category']==category]
            assert len(rows)==count
            assert sum(row['config']['role']=='attacker' for row in rows)==count//2
        for family in ['death-cloud','dragon-breath','retaliation-bait']:
            for role in ['attacker','defender']:
                assert sum(row['category']=='expert' and row['tactic_id']==family and row['config']['role']==role for row in phase)>=1
        for row in phase:
            assert row['split']=='train'
            assert digest(Path('/root/heroes3-ai-lab/data/vcmi/Maps')/row['config']['map'])==row['map_sha256']
    assert read(CONSERVATIVE/'cpu-math-check.json')['passed']


class FrozenExpert:
    def __init__(self,plan):
        verify_plan(plan)
        sys.path.insert(0,str(BRANCH))
        self.policy=module('mixed_branch_opponents',BRANCH/'opponents.py')
        self.delegate=self.policy.ExpertOpponent(strategy='breath')
        self.plan=plan
        self.version=self.policy.VERSION

    def __call__(self,observations):
        assert self.delegate.strategy=='breath' and self.policy.VERSION==self.version
        actions=self.delegate(observations)
        assert len(actions)==len(observations)
        assert all(action in obs['active_action_ids'] for action,obs in zip(actions,observations))
        return actions

    def verify(self):
        assert self.delegate.strategy=='breath' and self.policy.VERSION==self.version
        verify_plan(self.plan)


class FragmentTracker:
    """Owned sampled steps since last environment termination/truncation."""
    def __init__(self,count):self.steps=[0]*count

    def observe(self,transitions):
        assert len(transitions)==len(self.steps)
        for index,state in enumerate(transitions):
            self.steps[index]=0 if state['terminated'] or state['truncated'] else self.steps[index]+1

    def close_summary(self,rows,reason):
        assert len(rows)==len(self.steps) and reason in ['rotation','finish']
        fragments=[]
        for index,(row,steps) in enumerate(zip(rows,self.steps)):
            if steps:
                fragments.append(dict(worker=index,category=row['category'],role=row['config']['role'],
                    sampled_owned_steps=steps,scenario_id=row['scenario_id']))
        result=dict(reason=reason,discarded_ongoing_fragments=len(fragments),
            sampled_owned_steps_in_fragments=sum(fragment['sampled_owned_steps'] for fragment in fragments),
            fragments=fragments,environment_truncations_added=0,rewards_or_outcomes_changed=False)
        self.steps=[0]*len(self.steps)
        return result
