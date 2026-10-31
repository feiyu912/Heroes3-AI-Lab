#!/usr/bin/env python3
"""Read-only completed v3 native evidence audit. No runner or GPU/optimizer."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import re
from pathlib import Path
import struct
import sys
import zipfile
import zlib

import torch

V2 = Path(__file__).resolve().parent.parent / 'strategic-policy-v2'
sys.path.insert(0, str(V2))
from encoder import validate, encode, collate, STATE_DIM, CANDIDATE_DIM
from model import load_checkpoint_bundle
from legacy import load_legacy_checkpoint


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def readlines(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines()]


def creature_values(lod):
    with lod.open('rb') as stream:
        header = stream.read(92)
        assert header[:3] == b'LOD'
        entries = [struct.unpack('<16sIIII', stream.read(32)) for _ in range(struct.unpack_from('<I', header, 8)[0])]
        entry = next(item for item in entries if item[0].rstrip(b'\0').lower() == b'crtraits.txt')
        stream.seek(entry[1])
        data = stream.read(entry[4] or entry[2])
    if entry[4]:
        data = zlib.decompress(data)
    lines = data.decode('latin1').splitlines()
    assert lines[1].split('\t')[10] == 'AI Value'
    rows = [line.split('\t') for line in lines[2:] if line.split('\t')[0] and len(line.split('\t')) > 10]
    # Core castle/rampart IDs 0..27 are first two factions' CRTRAITS rows after blank separators. Fail closed for
    # other IDs instead of assuming legacy blank-line ordering for every faction.
    values = {index: int(row[10]) for index, row in enumerate(rows[:28])}
    return values, dict(lod_sha256=sha(lod), CRTRAITS_SHA256=hashlib.sha256(data).hexdigest(), AIValues=values)


def visitable(obj):
    mask = obj['template']['mask']
    cells = [(row, col) for row, line in enumerate(mask) for col, value in enumerate(line) if value == 'A']
    assert len(cells) == 1
    row, col = cells[0]
    return [obj['x'] - (len(mask[row])-col-1), obj['y'] - (len(mask)-row-1), obj['l']]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--agent-dir', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    torch.set_num_threads(1)
    agent = args.agent_dir
    smoke_plan = json.loads((agent/'smoke-plan.json').read_text())
    smoke = json.loads((agent/'smoke-result.json').read_text())
    native_dir = Path(smoke['native_result']['run_dir'])
    native_plan = json.loads((native_dir/'plan.json').read_text())
    checked = dict(smoke_plan['code_sha256'], **native_plan['hashes'])
    assert all(sha(path) == digest for path, digest in checked.items())
    checkpoint = Path(smoke_plan['broker_command'][smoke_plan['broker_command'].index('--checkpoint')+1])
    model, bundle, digest = load_checkpoint_bundle(checkpoint)
    ready = json.loads((agent/'broker-ready.json').read_text())
    assert digest == smoke_plan['checkpoint_sha256'] and ready['model_version'] == 'sha256:'+digest
    assert ready['mode'] in ('policy', 'new-policy')
    parent = Path(bundle['lineage']['parent_checkpoint'])
    old, old_collate, parent_sha = load_legacy_checkpoint(parent)
    assert parent_sha == bundle['lineage']['parent_sha256']
    assert bundle['optimizer'] is None and bundle['optimizer_steps_total'] == 0
    trace = readlines(native_dir/'strategy-trace.jsonl')
    before = [row for row in trace if row['event'] == 'before_move']
    decisions = readlines(native_dir/'strategy-decisions.jsonl')
    requests = [validate(json.loads(path.read_text()), index) for index, path in
                enumerate(sorted(agent.glob('request-????????.json')), 1)]
    events = [row for row in readlines(agent/'broker-trace.jsonl') if row['event'] == 'decision_committed']
    assert len(before) == len(decisions) == len(requests) == len(events) == 224
    data_root = native_dir/'data/vcmi'
    map_path = data_root/(native_plan['config']['map']+'.vmap')
    with zipfile.ZipFile(map_path) as archive:
        objects = json.loads(archive.read('objects.json'))
    town_positions = {index: visitable(obj) for index, (_, obj) in enumerate(objects.items()) if obj['type']=='town'}
    values, value_provenance = creature_values(data_root/'Data/H3bitmap.lod')
    castle_config = native_dir/'config/creatures/castle.json'
    assert not re.search(r'"(?:aiValue|AIValue)"\s*:', castle_config.read_text())
    value_provenance['castle_config_sha256'] = sha(castle_config)
    rampart_config = native_dir/'config/creatures/rampart.json'
    assert re.search(r'"centaur"\s*:\s*\{\s*"index"\s*:\s*14', rampart_config.read_text())
    assert not re.search(r'"(?:aiValue|AIValue)"\s*:', rampart_config.read_text())
    value_provenance['rampart_config_sha256'] = sha(rampart_config)
    targets = readlines(native_dir/'strategy-trace.jsonl.targets.jsonl')
    hero_filters = [row for row in targets if row['kind'] == 0 and row['status']=='strength_filter']
    keyed = defaultdict(list)
    for row in hero_filters:
        keyed[(row['day'], row['hero'], tuple(row['from']))].append(row)
    matched_filter_contexts = 0
    filter_examples = []
    counters, max_value_error, max_migration_error = Counter(), 0., 0.
    feature_hashes, supply_examples = [], []
    all_min, all_max = float('inf'), -float('inf')
    def army_value(stacks):
        assert all(creature in values for creature, count in stacks), 'Observed creature not covered by audited CRTRAITS map'
        return sum(values[creature]*count for creature, count in stacks)
    for index, (request, state, decision, event) in enumerate(zip(requests,before,decisions,events), 1):
        hero = next(hero for hero in state['heroes'] if hero['id']==request['hero'])
        assert request['day'] == state['day'] and request['player'] == state['player']
        assert request['from'] == [hero[key] for key in ('x','y','z')]
        assert all(request[key] == state[key] for key in ('gold','wood','ore'))
        assert request['movement']==hero['movement'] and request['own_army_value']==army_value(hero['army'])
        expected_towns = [dict(position=town_positions[town['id']], army_value=army_value(town['army'])) for town in state['towns']]
        assert request['own_towns']==expected_towns
        counters['town_value_recomputations'] += len(expected_towns)
        if len(supply_examples)<3 and any(town['army_value']>0 for town in expected_towns):
            supply_examples.append(dict(request_id=index, day=request['day'], towns=expected_towns,
                trace_towns=[dict(id=town['id'],army=town['army']) for town in state['towns']]))
        assert sha(agent/event['request_file'])==event['request_sha256']
        assert sha(agent/event['action_file'])==event['response_sha256']
        action = int((agent/event['action_file']).read_text())
        assert action==event['action']==decision['selected_candidate']
        assert decision['destination']==request['candidates'][action]['position']
        assert decision['step']==request['candidates'][action]['next']
        key = (request['day'], request['hero'], tuple(request['from']))
        filtered = keyed[key]
        for row in filtered:
            assert row['tile_visible'] == 1
            assert any(threat['position']==row['position'] and threat['approx_army_value']==row['strength']
                       for threat in request['visible_threats'])
            if len(filter_examples)<5:
                filter_examples.append(dict(request_id=index, day=request['day'], own_strength=request['own_army_value'],
                    filtered_strength=row['strength'], position=row['position'],
                    present_in_combat_candidates=any(candidate['kind']==0 and candidate['position']==row['position'] for candidate in request['candidates'])))
        matched_filter_contexts += bool(filtered)
        counters['visible_threat_entries'] += len(request['visible_threats'])
        counters['requests_with_threats'] += bool(request['visible_threats'])
        counters['requests_with_stronger_threats'] += any(threat['approx_army_value']>request['own_army_value'] for threat in request['visible_threats'])
        counters['singleton_requests'] += len(request['candidates'])==1
        encoded = collate([request])
        assert encoded['state'].shape[-1]==STATE_DIM and encoded['candidates'].shape[-1]==CANDIDATE_DIM
        assert torch.isfinite(encoded['state']).all() and torch.isfinite(encoded['candidates']).all()
        state_values, cand_values = encode(request)
        feature_hashes.append(hashlib.sha256(json.dumps([state_values,cand_values],separators=(',',':')).encode()).hexdigest())
        flattened = state_values+[value for candidate in cand_values for value in candidate]
        all_min,all_max = min(all_min,min(flattened)),max(all_max,max(flattened))
        with torch.no_grad():
            logits,predicted = model(**encoded)
            legacy_logits, legacy_value = old(**old_collate([request]))
        assert int(logits.argmax(1))==action
        max_value_error=max(max_value_error,abs(float(predicted[0])-event['value']))
        max_migration_error=max(max_migration_error,float((logits-legacy_logits).abs().max()),float((predicted-legacy_value).abs().max()))
    matched_unique = sum(any(row['day']==request['day'] and row['hero']==request['hero'] and row['from']==request['from'] for request in requests) for row in hero_filters)
    assert max_value_error==0. and max_migration_error<2e-6
    assert all(sha(path) == digest for path,digest in checked.items())
    assert not torch.cuda.is_initialized()
    report=dict(passed=True, game_started=False, optimizer_steps=0, CUDA_initialized=False,
        native_completed=smoke['native_result']['completed'], winner=smoke['native_result']['winner'],
        our_role='blue', ability_gain_certified=False, requests_verified=len(requests), statistics=dict(counters),
        enemy_hero_strength_filter_events=len(hero_filters), filter_events_with_request_context=matched_unique,
        request_contexts_preserving_filtered_hero_information=matched_filter_contexts,
        strength_filter_examples=filter_examples, own_town_value_examples=supply_examples,
        own_town_positions_from_map_template=dict(town_positions), AIValue_provenance=value_provenance,
        own_town_army_value_and_hero_strength_recomputed=True,
        new_model_request_action_value_replay_max_value_error=max_value_error,
        migrated_model_vs_parent_max_output_error=max_migration_error, finite_feature_range=[all_min,all_max],
        per_request_encoded_features_sha256=feature_hashes,
        checkpoint_sha256=sha(checkpoint), lineage=bundle['lineage'],
        checked_inputs=checked, audit_source_sha256=sha(Path(__file__)),
        limitations='Before_move town trace has IDs and exact stacks, not coordinates. Positions are independently mapped via map object ordinal and template A visitable cell, then checked against each request. '
        'Threat provenance also relies on frozen native visibility/callback code; coarse estimates are not hidden exact armies. '
        'Initial appended weights are zero: matching actions cannot by itself establish learned use of new fields. '
        'Feature hashes are audit recomputations, not originally logged broker tensor hashes. '
        'One completed NK loss is engineering evidence, not strategy improvement.')
    (args.out/'AUDIT.json').write_text(json.dumps(report,indent=2))
    (args.out/'audit_native_visible.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps({key:report[key] for key in ('passed','requests_verified','statistics','enemy_hero_strength_filter_events',
        'filter_events_with_request_context','request_contexts_preserving_filtered_hero_information',
        'new_model_request_action_value_replay_max_value_error','migrated_model_vs_parent_max_output_error','finite_feature_range')},indent=2))


if __name__=='__main__':
    main()
