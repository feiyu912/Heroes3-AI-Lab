"""Compare the public upstream policy against the B64 anchor on identical development cells.

Answers one question only: on which (scenario, role, seed) cells does the public model win
while B64 loses, i.e. is there recoverable headroom below the 95% target.
"""
import json
from collections import defaultdict
from pathlib import Path

OUT = Path(__file__).resolve().parent / 'expert-mixed-b64-run-v2'


def load(name):
    path = OUT / f'{name}-development.json'
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding='utf-8-sig'))


def index(report):
    return {(r['scenario'], r['role'], r['seed']): bool(r['success']) for r in report['battles']}


def main():
    result = {}
    for opponent in ['BattleAI', 'MMAI_MODEL']:
        public = load(f'public-original-{opponent}')
        b64 = load(f'b64-baseline-{opponent}')
        if public is None or b64 is None:
            continue
        p, b = index(public), index(b64)
        assert set(p) == set(b)
        cells = defaultdict(lambda: dict(public=0, b64=0, games=0))
        for key in p:
            cells[key[:2]]['public'] += p[key]
            cells[key[:2]]['b64'] += b[key]
            cells[key[:2]]['games'] += 1
        recoverable = []
        for (scenario, role), v in sorted(cells.items()):
            gap = v['public'] - v['b64']
            if gap > 0:
                recoverable.append(dict(scenario=scenario, role=role, public=v['public'],
                                        b64=v['b64'], games=v['games'], headroom=gap))
        result[opponent] = dict(
            public_wins=sum(p.values()), b64_wins=sum(b.values()), games=len(p),
            public_only=sum(1 for k in p if p[k] and not b[k]),
            b64_only=sum(1 for k in p if b[k] and not p[k]),
            both_win=sum(1 for k in p if p[k] and b[k]),
            both_lose=sum(1 for k in p if not p[k] and not b[k]),
            recoverable_cells=sorted(recoverable, key=lambda r: -r['headroom']),
            recoverable_games=sum(r['headroom'] for r in recoverable))
    (OUT / 'public-vs-b64-cells.json').write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
    for opponent, v in result.items():
        print(opponent, {k: v[k] for k in ('public_wins', 'b64_wins', 'games', 'public_only', 'b64_only',
                                           'both_win', 'both_lose', 'recoverable_games')})
        print('  top recoverable cells:', v['recoverable_cells'][:8])


if __name__ == '__main__':
    main()
