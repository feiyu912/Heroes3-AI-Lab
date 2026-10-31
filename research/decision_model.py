"""Small candidate actor/critic models. Teacher and outcomes never enter features."""
import json
from pathlib import Path
import numpy as np
import torch
from torch import nn

from battle_features import FEATURE_VERSION, ENTITY_DIM, CANDIDATE_DIM, features, linked_features


def collate(samples, device='cpu'):
    batch = len(samples)
    ne = max(len(s[0]) for s in samples)
    na = max(len(s[1]) for s in samples)
    entity = np.zeros((batch, ne, ENTITY_DIM), np.float32)
    candidate = np.zeros((batch, na, samples[0][1].shape[1]), np.float32)
    adjacency = np.zeros((batch, ne, ne), np.float32)
    emask = np.zeros((batch, ne), bool)
    amask = np.zeros((batch, na), bool)
    for i, (e, a, g, _) in enumerate(samples):
        entity[i, :len(e)] = e
        candidate[i, :len(a)] = a
        adjacency[i, :len(e), :len(e)] = g
        emask[i, :len(e)] = True
        amask[i, :len(a)] = True
    return tuple(torch.as_tensor(v, device=device) for v in [entity, candidate, adjacency, emask, amask])


class DecisionModel(nn.Module):
    def __init__(self, architecture='mlp', width=128, value_enabled=True):
        super().__init__()
        self.architecture, self.width = architecture, width
        self.value_enabled = value_enabled
        self.entity = nn.Sequential(nn.Linear(ENTITY_DIM, width), nn.ReLU(), nn.Linear(width, width), nn.ReLU())
        self.candidate = nn.Sequential(nn.Linear(CANDIDATE_DIM, width), nn.ReLU(), nn.Linear(width, width), nn.ReLU())
        if architecture == 'attention':
            layer = nn.TransformerEncoderLayer(width, 4, width * 2, dropout=0,
                                                batch_first=True, norm_first=True)
            self.encoder = nn.TransformerEncoder(layer, 2, enable_nested_tensor=False)
        elif architecture in ['gnn', 'linked-gnn']:
            self.message = nn.ModuleList([nn.Linear(width * 2, width) for _ in range(2)])
        elif architecture != 'mlp':
            raise ValueError(architecture)
        self.policy = nn.Sequential(nn.Linear(width * (6 if architecture == 'linked-gnn' else 3), width), nn.ReLU(), nn.Linear(width, 1))
        self.value = nn.Sequential(nn.Linear(width * 2, width), nn.ReLU(), nn.Linear(width, 1)) if value_enabled else None

    def forward(self, entity, candidate, adjacency, emask, amask):
        assert bool(emask.any(1).all()) and bool(amask.any(1).all())
        h = self.entity(entity)
        if self.architecture == 'attention':
            h = self.encoder(h, src_key_padding_mask=~emask)
        elif self.architecture in ['gnn', 'linked-gnn']:
            for layer in self.message:
                h = torch.relu(layer(torch.cat((h, adjacency @ h), -1)))
        mean = (h * emask.unsqueeze(-1)).sum(1) / emask.sum(1, keepdim=True)
        maximum = h.masked_fill(~emask.unsqueeze(-1), -torch.inf).amax(1)
        context = torch.cat((mean, maximum), -1)
        action = self.candidate(candidate[..., :CANDIDATE_DIM])
        inputs = [action, context[:, None].expand(-1, action.shape[1], -1)]
        if self.architecture == 'linked-gnn':
            links = candidate[..., CANDIDATE_DIM:].long()
            for column in range(3):
                indices = links[..., column]
                linked = h.gather(1, indices.clamp(min=0)[..., None].expand(-1, -1, self.width))
                inputs.append(linked * (indices >= 0)[..., None])
        logits = self.policy(torch.cat(inputs, -1)).squeeze(-1)
        value = self.value(context).squeeze(-1) if self.value is not None else context.new_zeros(len(context))
        return logits.masked_fill(~amask, -torch.inf), value


def load_model(path):
    checkpoint = torch.load(path, map_location='cpu', weights_only=True)
    expected = 'lab-candidates-v2-linked' if checkpoint['architecture'] == 'linked-gnn' else FEATURE_VERSION
    assert checkpoint['feature_version'] == expected
    model = DecisionModel(checkpoint['architecture'], checkpoint['width'], checkpoint.get('value_enabled', True))
    model.load_state_dict(checkpoint['state_dict'])
    model.eval()
    return model, checkpoint


def save_model(model, path, **metadata):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    version = 'lab-candidates-v2-linked' if model.architecture == 'linked-gnn' else FEATURE_VERSION
    torch.save(dict(feature_version=version, architecture=model.architecture,
                    width=model.width, value_enabled=model.value_enabled, state_dict=model.state_dict(), **metadata), path)


def load_dataset(root, split):
    data = []
    for meta_path in sorted((Path(root) / split).glob('*.json')):
        metadata = json.loads(meta_path.read_text())
        if 'decisions' not in metadata:
            continue
        with np.load(meta_path.with_suffix('.npz'), allow_pickle=False) as archive:
            for t, decision in enumerate(metadata['decisions']):
                nodes, edges = {}, {}
                prefix = f'{t}/'
                for key in archive.files:
                    if not key.startswith(prefix):
                        continue
                    parts = key.split('/')
                    if parts[1] == 'nodes':
                        nodes[parts[2]] = archive[key]
                    elif parts[1] == 'edges':
                        edges.setdefault(tuple(parts[2].split('|')), {})[parts[3]] = archive[key]
                ids = archive[f'{t}/legal_ids']
                mask = archive[f'{t}/mask']
                assert np.array_equal(np.flatnonzero(mask), np.sort(ids))
                label = int(np.flatnonzero(ids == decision['action'])[0])
                obs = dict(nodes=nodes, edges=edges, active_action_ids=ids)
                data.append(dict(features=features(obs), label=label, value=metadata['outcome_value'],
                                 action_type=decision['action_type'], battle_id=metadata['battle_id'],
                                 state_hash=decision['observation_sha256']))
    assert data, split
    return data
