"""Hash the complete public graph, including geometry/damage relations."""
import numpy as np


def update(digest,observation):
    def array(name,value):
        value=np.asarray(value)
        digest.update(name.encode());digest.update(str((value.dtype.str,value.shape)).encode())
        digest.update(np.ascontiguousarray(value).tobytes())
    for name,value in sorted(observation['nodes'].items()):array('node:'+name,value)
    for relation,edge in sorted(observation['edges'].items()):
        index=edge['index'];attrs=edge['attrs']
        if index.shape[1]:
            # Graph edges are unordered; compare semantic relations rather than
            # allocator-dependent insertion order of otherwise equal edges.
            keys=[attrs[:,j] for j in reversed(range(attrs.shape[1]))]+[index[1],index[0]]
            order=np.lexsort(keys);index=index[:,order];attrs=attrs[order]
        array('edge-index:'+'|'.join(relation),index)
        array('edge-attrs:'+'|'.join(relation),attrs)
    array('active_action_ids',observation['active_action_ids'])
