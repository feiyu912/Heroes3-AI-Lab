"""Guard absent human colors in isolated only-AI debug starts. No compilation."""
import hashlib
import json
from pathlib import Path

ROOT = Path('/root/heroes3-ai-lab/src/vcmi-adv')
OLD = '\t\tsetPlayer(myFirstColor());'
NEW = ('\t\tconst auto humanColor = myFirstColor();\n'
       '\t\tif(humanColor.isValidPlayer())\n'
       '\t\t\tsetPlayer(humanColor);')


def main():
    path = ROOT / 'client/CServerHandler.cpp'
    before = path.read_bytes()
    text = before.decode('utf-8')
    if NEW in text and OLD not in text:
        changed = False
    elif text.count(OLD) == 1 and NEW not in text:
        text = text.replace(OLD, NEW)
        path.write_bytes(text.encode('utf-8'))
        changed = True
    else:
        raise RuntimeError('Unexpected debug-start source; refusing ambiguous patch')
    after = path.read_bytes()
    assert NEW in after.decode('utf-8')
    assert 'while(myFirstColor() != PlayerColor::CANNOT_DETERMINE)' in after.decode('utf-8')
    digest = lambda data: hashlib.sha256(data).hexdigest()
    result = {'path': str(path), 'changed': changed, 'before_sha256': digest(before),
              'after_sha256': digest(after), 'compiled': False,
              'scope': 'Only debugStartTest valid-human guard; normal human waiting remains',
              'server_precheck_modified': False}
    report = Path(__file__).parent / ('testsave-human-guard-' + result['after_sha256'][:12] + '.json')
    if not report.exists():
        report.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
