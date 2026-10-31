"""Official v15 ONNX inference, using the model's own relation ordering metadata."""
import json
import numpy as np
import onnxruntime as ort


class UpstreamPolicy:
    def __init__(self, path):
        options = ort.SessionOptions()
        options.intra_op_num_threads = 1
        options.inter_op_num_threads = 1
        self.session = ort.InferenceSession(str(path), options, providers=['CPUExecutionProvider'])
        meta = self.session.get_modelmeta().custom_metadata_map
        self.nodes = json.loads(meta['node_order'])
        self.edges = [tuple(e) for e in json.loads(meta['edge_order'])]
        self.side = int(meta['side'])
        assert int(meta['version']) == 15
        self.input_specs = {i.name: i for i in self.session.get_inputs()}
        self.edge_width = int(self.input_specs['edge_attr_flat'].shape[1])

    def inputs(self, obs):
        data = {'x_' + n: np.asarray(obs['nodes'][n], dtype=np.float32) for n in self.nodes}
        indices, attributes, lengths = [], [], []
        for relation in self.edges:
            edge = obs['edges'][relation]
            index = np.asarray(edge['index'], dtype=np.int64)
            attrs = np.asarray(edge['attrs'], dtype=np.float32)
            assert attrs.shape[0] == index.shape[1]
            lengths.append(index.shape[1])
            indices.append(index)
            attributes.append(np.pad(attrs, ((0, 0), (0, self.edge_width - attrs.shape[1]))))
        data.update(edge_index_flat=np.concatenate(indices, axis=1),
                    edge_attr_flat=np.concatenate(attributes, axis=0),
                    edge_lengths=np.asarray(lengths, dtype=np.int32),
                    active_action_ids=np.asarray(obs['active_action_ids'], dtype=np.int64))
        return data

    def predict(self, obs):
        action, probabilities, value, ids = self.session.run(None, self.inputs(obs))
        ids = np.asarray(ids)
        np.testing.assert_array_equal(ids, obs['active_action_ids'])
        assert np.isfinite(probabilities).all() and np.isfinite(value).all()
        assert abs(float(probabilities.sum()) - 1) < 1e-4
        action = int(np.asarray(action).item())
        assert action == int(ids[np.argmax(probabilities)])
        return action, np.asarray(probabilities), float(np.asarray(value).item())
