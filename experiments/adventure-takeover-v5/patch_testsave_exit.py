"""Apply only the isolated client auto-exit fix; never compiles or starts VCMI."""
import argparse
import hashlib
import json
from pathlib import Path


OLD = 'if(!settings["session"]["testmap"].isNull() && allPlayersEndedGame)'
NEW = ('if((!settings["session"]["testmap"].isNull()'
       ' || !settings["session"]["testsave"].isNull()) && allPlayersEndedGame)')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--source-root', type=Path,
                   default=Path('/root/heroes3-ai-lab/src/vcmi-adv'))
    args = p.parse_args()
    root = args.source_root.resolve()
    if root != Path('/root/heroes3-ai-lab/src/vcmi-adv'):
        raise ValueError('This helper is restricted to the explicitly isolated vcmi-adv tree')
    path = root / 'client/NetPacksClient.cpp'
    before = path.read_bytes()
    text = before.decode('utf-8')
    if NEW in text and OLD not in text:
        changed = False
    elif text.count(OLD) == 1 and NEW not in text:
        text = text.replace(OLD, NEW)
        path.write_bytes(text.encode('utf-8'))
        changed = True
    else:
        raise RuntimeError('Unexpected auto-exit source; refusing ambiguous patch')
    report = {'path': str(path), 'changed': changed, 'before_sha256': sha(before),
              'after_sha256': sha(path.read_bytes()), 'compiled': False,
              'scope': 'Only session.testsave OR condition for native allPlayersEndedGame auto-exit'}
    out = Path(__file__).resolve().parent / ('testsave-exit-patch-' + report['after_sha256'][:12] + '.json')
    if not out.exists():
        out.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
