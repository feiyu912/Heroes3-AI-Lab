"""Restore JSON graph dimensions from the actual native v15 schema."""
import numpy as np
from vcmi_gym.envs.v15.pyconnector import EDGE_TYPES, NODE_TYPES


def unpack(data, side):
    nodes = {}
    for name, values in data['nodes'].items():
        width = int(NODE_TYPES[name]['size'])
        array = np.asarray(values, np.float32)
        assert width > 0 and array.size % width == 0
        nodes[name] = array.reshape(-1, width)
    edges = {}
    for edge in data['edges']:
        relation = tuple(edge['relation'])
        index = np.asarray(edge['index'], np.int64).reshape(2, -1)
        width = int(EDGE_TYPES[relation]['size'])
        attrs = np.asarray(edge['attrs'], np.float32).reshape(index.shape[1], width)
        assert all((index[axis] >= 0).all() and (index[axis] < len(nodes[name])).all()
                   for axis, name in [(0, relation[0]), (1, relation[2])])
        edges[relation] = dict(index=index, attrs=attrs)
    ids = np.asarray(data['active_action_ids'], np.int64)
    assert len(ids) and len(set(ids.tolist())) == len(ids)
    assert (ids >= 0).all() and (ids < len(nodes['Action'])).all()
    assert side in [0, 1]
    return dict(nodes=nodes, edges=edges, active_action_ids=ids, lab_side=side)
