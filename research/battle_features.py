"""NumPy-only v15 feature extraction for isolated simulator workers."""
import numpy as np

FEATURE_VERSION = 'lab-candidates-v1'
ENTITY_TYPES = ('Global', 'Player', 'Unit', 'Hex')
ENTITY_DIM = 39
CANDIDATE_DIM = 186


def features(obs):
    ids = np.asarray(obs['active_action_ids'], dtype=np.int64)
    assert len(ids) and len(set(ids.tolist())) == len(ids)
    entities, offsets = [], {}
    for kind, name in enumerate(ENTITY_TYPES):
        values = obs['nodes'][name]
        offsets[name] = sum(len(v) for v in entities)
        padded = np.zeros((len(values), ENTITY_DIM), dtype=np.float32)
        padded[:, :values.shape[1]] = values
        padded[:, 35 + kind] = 1
        entities.append(padded)
    entities = np.concatenate(entities)
    adjacency = np.zeros((len(entities), len(entities)), dtype=np.float32)
    for (src, _, dst), edge in obs['edges'].items():
        if src in offsets and dst in offsets:
            index = edge['index']
            adjacency[index[1] + offsets[dst], index[0] + offsets[src]] = 1
    adjacency += np.eye(len(entities), dtype=np.float32)
    adjacency /= adjacency.sum(1, keepdims=True).clip(min=1)
    candidates = np.zeros((len(ids), CANDIDATE_DIM), dtype=np.float32)
    candidates[:, :7] = obs['nodes']['Action'][ids]
    lookup = {int(action): i for i, action in enumerate(ids)}
    relations = [(('Action', 'By', 'Unit'), 7, False),
                 (('Action', 'EndsAt', 'Hex'), 42, False),
                 (('Unit', 'IsMeleedBy', 'Action'), 77, True),
                 (('Unit', 'IsShotBy', 'Action'), 112, True),
                 (('Action', 'Blocks', 'Unit'), 147, False)]
    for key, offset, reverse in relations:
        edge = obs['edges'][key]
        action_idx = 1 if reverse else 0
        entity_name = key[0] if reverse else key[2]
        counts = np.zeros(len(ids), dtype=np.float32)
        for j, action in enumerate(edge['index'][action_idx]):
            row = lookup.get(int(action))
            if row is None:
                continue
            target = int(edge['index'][1 - action_idx, j])
            values = obs['nodes'][entity_name][target]
            candidates[row, offset:offset + len(values)] += values
            counts[row] += 1
            if reverse:
                damage_offset = 182 if key[1] == 'IsMeleedBy' else 184
                candidates[row, damage_offset:damage_offset + 2] += edge['attrs'][j]
        candidates[:, offset:offset + 35] /= counts[:, None].clip(min=1)
    assert np.isfinite(entities).all() and np.isfinite(candidates).all()
    return entities, candidates, adjacency, ids


def linked_features(obs):
    entities, candidates, adjacency, ids = features(obs)
    offsets = {}
    offset = 0
    for name in ENTITY_TYPES:
        offsets[name] = offset
        offset += len(obs['nodes'][name])
    links = np.full((len(ids), 3), -1, dtype=np.float32)
    lookup = {int(action): i for i, action in enumerate(ids)}
    for key, column, reverse in [(('Action', 'By', 'Unit'), 0, False),
                                 (('Unit', 'IsMeleedBy', 'Action'), 1, True),
                                 (('Unit', 'IsShotBy', 'Action'), 1, True),
                                 (('Action', 'EndsAt', 'Hex'), 2, False)]:
        index = obs['edges'][key]['index']
        action_axis = 1 if reverse else 0
        target_name = key[0] if reverse else key[2]
        for j, action in enumerate(index[action_axis]):
            row = lookup.get(int(action))
            if row is not None and links[row, column] < 0:
                links[row, column] = offsets[target_name] + int(index[1-action_axis, j])
    # One primary target/landing link; multi-target attributes remain in base features.
    return entities, np.concatenate((candidates, links), 1), adjacency, ids


