"""Derive isolated TRAIN calibration tools. Never executes native, CUDA or PPO."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent / 'strategic-active-opponent-learning-20261024'
POLICY = HERE.parent / 'strategic-active-opponent-policy-v4'
DIAGNOSTIC = HERE.parent / 'strategic-sampler-calibration-diagnostic-20261024'


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def once(text, before, after):
    assert text.count(before) == 1, (before[:100], text.count(before))
    return text.replace(before, after, 1)


def emit(name, text):
    p = HERE / name
    if p.exists():
        if p.read_text() == text: return
        assert not (HERE / 'SOURCE_FREEZE.json').exists(), 'Sealed derived file differs: ' + name
    # Only owned, unsealed generated files may be regenerated during review.
    p.write_text(text)


def main():
    parent_freeze = PARENT / 'SOURCE_FREEZE.json'
    assert sha(parent_freeze) == 'c19ac372d22b3156172f02a65f8ad1ef4dc635a15737775eb8cf98c3b31467f7'
    diagnostic_freeze = DIAGNOSTIC / 'SOURCE_FREEZE.json'
    for freeze in (parent_freeze, diagnostic_freeze):
        assert all(sha(p) == h for p, h in json.loads(freeze.read_text())['files'].items())
    for name in ('leases.py', 'audit_game_v6.py'):
        emit(name, (PARENT / name).read_text())
    common = (DIAGNOSTIC / 'pipeline_common.py').read_text()
    common = once(common, "EPOCH='strategic-sampler-calibration-TRAIN-diagnostic-v1'",
                  "EPOCH='strategic-destination-sampling-TRAIN-calibration-v1'")
    common = once(common, 'TRAIN_only=True,sampler_diagnostic_only=True)',
                  'TRAIN_only=True,sampler_diagnostic_only=True,manual_exploration_setting=True,manual_setting_is_learning=False,move_temperature=0.25,new_PPO_admissions=0)')
    common = once(common, "HERE/'COLLECTOR_DERIVATION.json'", "HERE/'DERIVATION.json'")
    common = once(common, "    if not native['whole_game_valid'] or not native['native_game_completed'] or not native['transport_drained']:raise ValueError('Invalid diagnostic game')", '''    b=require_qualification()
    for key in ('whole_game_valid','native_game_completed','transport_drained','full_state_recruitment_verified','free_transfer_verified','compiled_native_epoch_proven'):
        if native.get(key) is not True:raise ValueError('Native audit missing '+key)
    if native.get('candidate_manifest_sha256')!=b['native_manifest_sha256'] or native.get('catalog_sha256')!=b['catalog_sha256'] or native.get('contract_errors'):
        raise ValueError('Native manifest/catalog/contract binding differs')''')
    common += '''
REGISTERED_JOBS = {
    2026104402: ('takeover-v2-train-01-mines', 0),
    2026104403: ('takeover-v2-train-01-mines', 1),
    2026104406: ('takeover-v2-train-02-development', 0),
    2026104407: ('takeover-v2-train-02-development', 1),
}

def validate_job(args):
    if args.arm != 'curriculum' or args.opponent != 'Nullkiller2' or args.logical_update != 0:
        raise ValueError('Only the four registered initial-model NK x4 calibration cells')
    if REGISTERED_JOBS.get(args.seed) != (args.map, args.player):
        raise ValueError('Unregistered calibration map/role/seed')
    if sha(args.checkpoint.resolve()) != INITIAL_SHA:
        raise ValueError('Fixed initial1510149e required, never an updated model')
'''
    common = once(common, 'def source_inputs():', 'def source_inputs():\n    diagnostic_freeze=HERE.parent/\'strategic-sampler-calibration-diagnostic-20261024/SOURCE_FREEZE.json\'\n    if sha(diagnostic_freeze)!=' + repr(sha(diagnostic_freeze)) + ':raise ValueError(\'Frozen sampling diagnostic changed\')\n    if not all(sha(p)==h for p,h in json.loads(diagnostic_freeze.read_text())[\'files\'].items()):raise ValueError(\'Frozen diagnostic sources changed\')')
    common = once(common, 'parent.source_inputs()+[freeze,', 'parent.source_inputs()+[freeze,diagnostic_freeze,')
    emit('pipeline_common.py', common)

    collector = (PARENT / 'collect_episode_v5.py').read_text()
    collector = once(collector, 'from pipeline_common import training_variant,', 'from pipeline_common import validate_job,training_variant,')
    collector = once(collector, "LAB=Path('/root/heroes3-ai-lab');BROKER=HERE/'onpolicy_broker_v2.py'",
                     "LAB=Path('/root/heroes3-ai-lab');BROKER=LOCAL/'onpolicy_broker.py'")
    collector = once(collector, '    clean_environment();assert args.load_save is None,',
                     '    validate_job(args)\n    clean_environment();assert args.load_save is None,')
    collector = once(collector, "    with owned_resources() as lease_fds,", "    resources('before_native')\n    with owned_resources() as lease_fds,")
    collector = once(collector, "    result['transport_drained']=bool(result['game_completed'] and result['client_exit']==0 and", "    resources('after_native')\n    result['transport_drained']=bool(result['game_completed'] and result['client_exit']==0 and")
    collector = once(collector, "ready['mode']=='onpolicy_cuda'", "ready['mode']=='onpolicy_cuda_move_temperature_v1'")
    collector = once(collector, "sampling='onpolicy CUDA multinomial'", "sampling='manual within-move T0.25 CUDA multinomial'")
    # Runtime resources are checked only after --prepare-only has returned.
    collector = once(collector, '\ndef run(args):', '''
def resources(phase):
    m={k:int(v.split()[0]) for k,v in (line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines())}
    if m['MemAvailable']<=2048*1024 or m['SwapTotal']-m['SwapFree']>=256*1024:
        raise RuntimeError('Resource gate: available RAM >2GiB and swap <256MiB required: '+phase)

def run(args):''')
    emit('collect_episode.py', collector)

    broker = (POLICY / 'onpolicy_broker_v2.py').read_text()
    broker = once(broker, "HERE=Path(__file__).resolve().parent;TYPED=HERE;LAB=Path('/root/heroes3-ai-lab')",
                  "LOCAL=Path(__file__).resolve().parent;HERE=LOCAL.parent/'strategic-active-opponent-policy-v4';TYPED=HERE;LAB=Path('/root/heroes3-ai-lab')\nsys.path.append(str(HERE))\nfrom movement_exploration import effective_distribution,TEMPERATURE,EPOCH")
    broker = once(broker, '            logp=legal.log_softmax(-1)',
                  "            effective,raw_logp,logp,raw_mass,effective_mass=effective_distribution(legal,request['candidates'],TEMPERATURE)")
    broker = once(broker, "                    economy_epoch=wire.encoder.EPOCH,", '''                    raw_logits=legal.detach().cpu().tolist(),effective_logits=effective.detach().cpu().tolist(),
                    raw_probabilities=raw_logp.exp().detach().cpu().tolist(),effective_probabilities=logp.exp().detach().cpu().tolist(),
                    raw_operation_probabilities={k:float(v) for k,v in raw_mass.items()},
                    effective_operation_probabilities={k:float(v) for k,v in effective_mass.items()},
                    distribution_epoch=EPOCH,move_temperature=TEMPERATURE,manual_exploration_setting=True,
                    manual_setting_is_learning=False,diagnostic_only=True,new_PPO_admissions=0,
                    economy_epoch=wire.encoder.EPOCH,''')
    broker = once(broker, "mode='onpolicy_cuda'", "mode='onpolicy_cuda_move_temperature_v1'")
    broker = once(broker, "schema='learned-build-single-env-sampling-state-v1'", "schema='strategic-move-temperature-calibration-sampling-state-v1',distribution_epoch=EPOCH,move_temperature=TEMPERATURE,manual_exploration_setting=True,manual_setting_is_learning=False,new_PPO_admissions=0")
    emit('onpolicy_broker.py', broker)
    replay = (POLICY / 'admit_episode_v5.py').read_text()
    replay = once(replay, 'from collect_episode_v5 import', 'from collect_episode import')
    replay = once(replay, 'from pipeline_common import training_variant,', 'from pipeline_common import validate_job,training_variant,')
    replay = once(replay, 'from onpolicy_broker_v2 import', 'from onpolicy_broker import')
    replay = once(replay, "plan['sampling']=='onpolicy CUDA multinomial'", "plan['sampling']=='manual within-move T0.25 CUDA multinomial'")
    replay = once(replay, '    validate_native_epoch(native,plan,execution)', "    validate_job(argparse.Namespace(arm=plan['arm'],opponent=plan['opponent'],logical_update=plan['logical_update'],seed=plan['seed'],map=plan['map'],player=plan['owned_player'],checkpoint=Path(plan['checkpoint'])))\n    validate_native_epoch(native,plan,execution)")
    replay = once(replay, "ready['mode']=='onpolicy_cuda'", "ready['mode']=='onpolicy_cuda_move_temperature_v1'")
    replay = once(replay, "        assert state['device']=='cuda'", "        assert state['schema']=='strategic-move-temperature-calibration-sampling-state-v1' and state['move_temperature']==0.25 and state['new_PPO_admissions']==0\n        assert state['device']=='cuda'")
    replay = once(replay, "'recruit_probability','economy_epoch']:", "'recruit_probability','economy_epoch','raw_logits','effective_logits','raw_probabilities','effective_probabilities','raw_operation_probabilities','effective_operation_probabilities','distribution_epoch','move_temperature','manual_exploration_setting','manual_setting_is_learning','diagnostic_only','new_PPO_admissions']:")
    replay = once(replay, "    a.out.mkdir(parents=True,exist_ok=False)", "    # No samples/episode admission files are ever written by this diagnostic.\n    a.out.mkdir(parents=True,exist_ok=False)")
    replay = once(replay, "    (a.out/'samples.jsonl').write_text(''.join(json.dumps(r,separators=(',',':'))+'\\n' for r in rows))\n    write(a.out/'episode.json',manifest)", "    manifest.update(diagnostic_only=True,new_PPO_admissions=0,manual_exploration_setting=True,manual_setting_is_learning=False)\n    write(a.out/'DIAGNOSTIC.json',manifest)")
    replay = once(replay, 'report=dict(passed=True,samples_admitted=len(rows),', 'report=dict(passed=True,samples_admitted=0,decisions_replayed=len(rows),new_PPO_admissions=0,manual_exploration_setting=True,manual_setting_is_learning=False,')
    replay = once(replay, "['samples.jsonl','episode.json']", "['DIAGNOSTIC.json']")
    emit('replay_sampling.py', replay)
    inputs = [PARENT / 'collect_episode_v5.py', POLICY / 'onpolicy_broker_v2.py',
              POLICY / 'admit_episode_v5.py', PARENT / 'leases.py', PARENT / 'audit_game_v6.py', DIAGNOSTIC / 'pipeline_common.py',
              parent_freeze, diagnostic_freeze]
    derivation = dict(parent_inputs={str(p): sha(p) for p in inputs},
        changes=['TRAIN-only four fixed initial1510149e NK x4 cells; no new admission',
                 'only conditional distribution within original distinct move candidates uses T=0.25',
                 'one inherited private CUDA multinomial draw per request; effective oldlogprob and unchanged critic',
                 'preserve raw/effective logits, probabilities, operation masses and manual-not-learning metadata',
                 'same schema6 capsule02/native identity, audit gates, locks and process cleanup',
                 'RAM>2GiB/swap<256MiB gate; --prepare-only returns before leases or GPU'],
        no_candidate_merge=True, no_PPO_or_expert_admission=True, source_freeze_created=False,
        existing_frozen_sources_modified=False, native_runs=0, GPU_operations=0, optimizer_steps=0)
    emit('DERIVATION.json', json.dumps(derivation, indent=2) + '\n')
    print(json.dumps(dict(prepared=True, native_runs=0, GPU_operations=0, optimizer_steps=0,
                          source_freeze_created=False)))


if __name__ == '__main__': main()
