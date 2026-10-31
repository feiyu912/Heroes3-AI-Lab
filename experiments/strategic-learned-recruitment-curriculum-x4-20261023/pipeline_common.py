"""Owned-start-army x4 TRAIN curriculum over the frozen schema6 recruitment stack.

The only changed factor relative to the prior-zero training batch is the
actual owned hero's starting army: exactly four times the original stack
counts in the private TRAIN map copy.  Original maps, the opponent armies,
the initialization, the eight cells, the seeds, Adam/PPO and the native
capsule are unchanged.  Difficulty was selected from completed TRAIN-only
calibration games, never from DEV choices or outcomes.
"""
import hashlib, importlib.util, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXP = HERE.parent

CURRICULUM = EXP / 'strategic-active-opponent-curriculum-20261023'
PRIOR_ZERO = EXP / 'strategic-learned-recruitment-run-v2'

def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

curriculum = _load('_frozen_active_opponent_curriculum', CURRICULUM / 'pipeline_common.py')
parent = curriculum.parent

BASE = parent.BASE
LAB = parent.LAB
NATIVE = parent.NATIVE
MARKER = parent.MARKER
AUDITOR = HERE
DEFAULT_CAPSULE = parent.DEFAULT_CAPSULE
DEFAULT_INITIAL = parent.DEFAULT_INITIAL
INITIAL_SHA = parent.INITIAL_SHA
CONTROL_POLICY = parent.CONTROL_POLICY
CONTROL_INITIAL = parent.CONTROL_INITIAL
CONTROL_UPDATED = parent.CONTROL_UPDATED
CONTROL_SHA = parent.CONTROL_SHA
EPOCH = 'strategic-learned-recruitment-curriculum-x4-training-v1'
# Frozen checkpoint-format schema. The x4 curriculum is recorded separately in
# the protocol's curriculum_epoch and in lineage.training_epoch.
MODEL_PROTOCOL_SCHEMA = 'strategic-learned-recruitment-prior-zero-training-v1'
SELECTION = HERE / 'SELECTION.json'
SOURCE_MAPS = ('takeover-v2-train-01-mines', 'takeover-v2-train-02-development')
OPPONENTS = ('EmptyAI', 'Nullkiller2')
SEED_BASE = 2026103900
MULTIPLIER = 4

sha = parent.sha
validate_capsule = parent.validate_capsule
capsule_inputs = parent.capsule_inputs
clean_environment = parent.clean_environment
require_qualification = parent.require_qualification

def map_manifest():
    """Re-validate the full 12-variant manifest and every original/derived SHA."""
    return curriculum.map_manifest()

def selection():
    if not SELECTION.is_file():
        raise ValueError('Completed TRAIN difficulty selection record is absent')
    record = json.loads(SELECTION.read_text())
    result = Path(record['calibration_result'])
    if not result.is_file() or sha(result) != record['calibration_result_sha256']:
        raise ValueError('Calibration RESULT changed after selection')
    if record['selection'].get('selected_multiplier') != MULTIPLIER:
        raise ValueError('Only the calibrated x4 TRAIN difficulty is admitted')
    if record['selection'].get('qualified') is not True:
        raise ValueError('Calibration did not qualify the selected difficulty')
    return record

def _expected_army(entry):
    return [dict(amount=item['amount'] * MULTIPLIER, type=item['type'])
            for item in entry['original_army']]

def variant_by_name(map_name):
    found = [entry for entry in map_manifest()['variants'] if entry['map'] == map_name]
    if len(found) != 1:
        raise ValueError('Unknown or duplicate TRAIN variant name')
    entry = found[0]
    if entry['multiplier'] != MULTIPLIER or entry['original_archive_exact'] is not False:
        raise ValueError('Selected variant is not an actual x4 archive')
    if entry['modified_army'] != _expected_army(entry) or entry['JSON_semantic_changes'] != [
            dict(path=f"/{entry['owned_hero_key']}/options/army/0/amount",
                 before=entry['original_army'][0]['amount'], after=entry['original_army'][0]['amount'] * MULTIPLIER),
            dict(path=f"/{entry['owned_hero_key']}/options/army/1/amount",
                 before=entry['original_army'][1]['amount'], after=entry['original_army'][1]['amount'] * MULTIPLIER)]:
        raise ValueError('Variant semantic diff is not the exact owned-army x4 factor')
    if entry['all_other_objects_semantically_identical'] is not True:
        raise ValueError('Variant changed objects other than the owned army')
    if entry['header_and_terrain_content_and_compressed_payload_exact'] is not True:
        raise ValueError('Variant changed header or terrain')
    if sha(entry['path']) != entry['sha256']:
        raise ValueError('Derived x4 TRAIN map changed')
    return entry

def variant_for(source_map, player):
    found = [entry for entry in map_manifest()['variants']
             if entry['source_map'] == source_map and entry['owned_player'] == player
             and entry['multiplier'] == MULTIPLIER]
    if len(found) != 1:
        raise ValueError('Exactly one x4 variant per source map and owned role is required')
    if found[0]['multiplier'] != MULTIPLIER:
        raise ValueError('Only the calibrated x4 variants are admitted')
    return variant_by_name(found[0]['map'])

X4_VARIANTS = tuple(variant_for(source, player)['map']
                    for source in SOURCE_MAPS for player in (0, 1))
EXPECTED_CELLS = {(variant_for(source, player)['map'], player, opponent)
                  for source in SOURCE_MAPS for player in (0, 1) for opponent in OPPONENTS}

def jobs(seed_base=SEED_BASE):
    if seed_base != SEED_BASE:
        raise ValueError('Only the pre-registered prior-zero-paired seeds 3900..3907 are admitted')
    result = []
    for index, (source, opponent, player) in enumerate(
            (source, opponent, player)
            for source in SOURCE_MAPS for opponent in OPPONENTS for player in (0, 1)):
        entry = variant_for(source, player)
        result.append(dict(map=entry['map'], source_map=source, player=player,
                           multiplier=MULTIPLIER, opponent=opponent,
                           seed=seed_base + index, logical_update=0))
    return result

def audit_metadata():
    return dict(parent.audit_metadata(), pipeline_epoch=EPOCH, TRAIN_only=True,
                training_curriculum='owned-start-army-x4-vs-original-v1',
                selected_multiplier=MULTIPLIER,
                selection_record_sha256=sha(SELECTION))

def source_inputs():
    freeze = parent.SOURCE_FREEZE if hasattr(parent, 'SOURCE_FREEZE') else PRIOR_ZERO / 'SOURCE_FREEZE.json'
    if sha(freeze) != '6c882b314cd69b526644e4730691f4b3e7979780ff3b6f6efce96abb68cbe827':
        raise ValueError('Frozen prior-zero source identity changed')
    protected = json.loads(freeze.read_text())['files']
    if not all(sha(EXP / path.replace('\\', '/')) == digest for path, digest in protected.items()):
        raise ValueError('Protected prior-zero policy/run source changed')
    manifest = map_manifest()
    paths = set(parent.source_inputs())
    paths.update({freeze, SELECTION, HERE / 'PLAN.md', HERE / 'MAP_DERIVATION.json',
                  CURRICULUM / 'PLAN.md', CURRICULUM / 'MAP_MANIFEST.json',
                  CURRICULUM / 'pipeline_common.py'})
    paths.update(HERE.glob('*.py'))
    paths.update(Path(entry['path']) for entry in manifest['variants'] if entry['multiplier'] == MULTIPLIER)
    paths.update(Path(source['path']) for source in manifest['sources'].values())
    return sorted(paths, key=str)

def validate_native_epoch(native, plan, execution):
    for obj in (native, plan, execution):
        if not all(obj.get(key) == value for key, value in audit_metadata().items()):
            raise ValueError('x4 curriculum native epoch metadata differs')
    for key in ('whole_game_valid', 'native_game_completed', 'transport_drained',
                'full_state_recruitment_verified', 'free_transfer_verified',
                'compiled_native_epoch_proven'):
        if native.get(key) is not True:
            raise ValueError('Native audit missing ' + key)
    binding = require_qualification()
    if native.get('candidate_manifest_sha256') != binding['native_manifest_sha256']:
        raise ValueError('Per-game native manifest differs')
    if native.get('catalog_sha256') != binding['catalog_sha256']:
        raise ValueError('Per-game runtime catalog differs')
    if native.get('contract_errors'):
        raise ValueError('Native contract errors')

def validate_cells(episodes):
    if len(episodes) != 8 or len({episode['episode_id'] for episode in episodes}) != 8:
        raise ValueError('Complete eight-cell x4 TRAIN batch required')
    cells = {(episode['job']['map'], episode['job']['owned_player'], episode['job']['opponent'])
             for episode in episodes}
    if cells != EXPECTED_CELLS:
        raise ValueError('Wrong x4 TRAIN map/role/opponent cells')
    if len({episode['checkpoint_sha256'] for episode in episodes}) != 1:
        raise ValueError('Mixed parent checkpoint')
    if len({episode['job']['logical_update'] for episode in episodes}) != 1:
        raise ValueError('Mixed logical update')
    by_name = {entry['map']: entry for entry in map_manifest()['variants']}
    for episode in episodes:
        entry = by_name.get(episode['job']['map'])
        if entry is None or entry['multiplier'] != MULTIPLIER:
            raise ValueError('Episode is not an x4 TRAIN variant')
        if entry['owned_player'] != episode['job']['owned_player']:
            raise ValueError('Episode role does not match its boosted owned hero')
