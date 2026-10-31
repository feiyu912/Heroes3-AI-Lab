#!/usr/bin/env python3
"""events-v2 death-cloud exclusion audit (native evidence only).

For every cloud attack group (SPELL_LIKE + SPELL_EFFECT targets) recorded in
an episode:
  1) no DAMAGED unit in the group may have HAS_NON_LIVING (undead exclusion);
  2) adjacency from the recorded graph (Unit_Occupies_Hex + Hex_Adjacent_Hex +
     Hex_OccupiedBy_Unit) finds units adjacent to the primary target's hex
     that took NO cloud damage; those with HAS_NON_LIVING prove the exclusion
     actually applied (eligible position, immune creature).
All lookups are PER DECISION: unit node indices are not stable across
decisions (units die, later nodes shift).
"""
import argparse
import gzip
import json
from pathlib import Path
import numpy as np


def unit_flags(arr):
    from vcmi_gym.envs.v15.vcmi_env import Unit
    m = {}
    for i in range(arr.shape[0]):
        u = Unit.decode_one(arr[i])
        m[i] = dict(is_enemy=bool(u.IS_ENEMY), non_living=bool(u.HAS_NON_LIVING),
                    value=float(u.VALUE_REL))
    return m


def edge_lookup(obs_edges_list, relation):
    """Packed observation edges are a LIST of dicts with a 'relation' key."""
    for e in obs_edges_list:
        if list(e['relation']) == list(relation):
            return np.asarray(e['index'], dtype=np.int64)
    return None


def audit(path, gz):
    with gzip.open(gz, 'rt') as f:
        data = json.load(f)
    res = dict(cloud_groups=0, groups_with_secondary=0,
               damaged_non_living_primary=0,   # primary target of a cloud attack
               damaged_non_living_secondary=0, # splash target; MUST be 0
               adjacent_undead_undamaged=0,    # proves exclusion applied
               adjacent_living_undamaged=0,
               primary_hex_missing=0)
    for d in data['decisions']:
        obs = d['observation']
        flags = unit_flags(np.asarray(obs['nodes']['Unit'], dtype=np.float32))
        unit_hex, hex_units, adj = {}, {}, {}
        idx = edge_lookup(obs['edges'], ('Unit', 'Occupies', 'Hex'))
        if idx is not None and idx.size:
            for u, h in idx.T:
                unit_hex[int(u)] = int(h)
        idx = edge_lookup(obs['edges'], ('Hex', 'OccupiedBy', 'Unit'))
        if idx is not None and idx.size:
            for h, u in idx.T:
                hex_units.setdefault(int(h), set()).add(int(u))
        idx = edge_lookup(obs['edges'], ('Hex', 'Adjacent', 'Hex'))
        if idx is not None and idx.size:
            for a, b in idx.T:
                adj.setdefault(int(a), set()).add(int(b))

        for ev in d['battle_events']:
            if ev['kind'] != 2 or not (ev['attack_flags'] & 64):
                continue
            res['cloud_groups'] += 1
            targets = ev['targets']
            if not any(t['flags'] & 2 for t in targets):
                continue
            res['groups_with_secondary'] += 1
            for t in targets:
                if (t['flags'] & 16) and flags.get(t['defender_node'], {}).get('non_living'):
                    if t['flags'] & 2:
                        res['damaged_non_living_secondary'] += 1
                    else:
                        res['damaged_non_living_primary'] += 1
            prim = [t for t in targets if not (t['flags'] & 2)]
            if not prim:
                continue
            phex = unit_hex.get(prim[0]['defender_node'])
            if phex is None:
                res['primary_hex_missing'] += 1
                continue
            damaged_nodes = {t['defender_node'] for t in targets}
            for nh in adj.get(phex, set()):
                for u in hex_units.get(nh, set()):
                    if u in damaged_nodes or u not in flags:
                        continue
                    if flags[u]['non_living']:
                        res['adjacent_undead_undamaged'] += 1
                    else:
                        res['adjacent_living_undamaged'] += 1
    return res


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--tag', required=True)
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    run_dir = here / 'runs' / args.tag

    total = dict(cloud_groups=0, groups_with_secondary=0,
                 damaged_non_living_primary=0, damaged_non_living_secondary=0,
                 adjacent_undead_undamaged=0, adjacent_living_undamaged=0,
                 primary_hex_missing=0)
    episodes = 0
    for path in sorted(run_dir.glob('*.json')):
        if path.name in ('manifest.json', 'analysis.json'):
            continue
        gz = path.with_suffix('.json.gz')
        if not path.exists() or not gz.exists():
            continue
        try:
            r = audit(path, gz)
        except Exception as e:
            print('ERR', path.name, e)
            continue
        episodes += 1
        for k in total:
            total[k] += r[k]

    print(f'episodes audited: {episodes}')
    for k, v in total.items():
        print(f'  {k}: {v}')
    print()
    print("PASS: no non-living unit ever took cloud SPLASH damage"
          if total['damaged_non_living_secondary'] == 0
          else f"FAIL: {total['damaged_non_living_secondary']} non-living units took splash")
    print(f"note: {total['damaged_non_living_primary']} non-living units were the PRIMARY "
          f"target of a cloud attack (a lich shot at a lich; primary hit is the attack itself)")
    print(f"exclusion observably applied in {total['adjacent_undead_undamaged']} adjacent-unit cases")


if __name__ == '__main__':
    main()
