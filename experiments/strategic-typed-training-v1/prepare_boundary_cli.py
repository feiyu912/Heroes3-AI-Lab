"""Add a fresh-output CLI without altering the already executed frozen launcher."""
import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;source=HERE/'run_boundary_v5.py';before=hashlib.sha256(source.read_bytes()).hexdigest()
text=source.read_text().replace('import hashlib,json,subprocess','import argparse,hashlib,json,subprocess',1)
old="OUT=LAB/'evaluations/typed-native-cuda-boundary-v5-01'"
new="""parser=argparse.ArgumentParser(description='Reproduce engineering boundary in a NEW directory; existing evidence is never overwritten')
parser.add_argument('--out',type=Path,required=True)
OUT=parser.parse_args().out.resolve()"""
assert text.count(old)==1;text=text.replace(old,new)
text=text.replace("frozen={str(HERE/n):sha(HERE/n) for n in names}","frozen={str(HERE/n):sha(HERE/n) for n in names};frozen[str(Path(__file__))]=sha(Path(__file__))")
text=text.replace("('request-*.json','response-*.json')","('request-*.json','action-*.json')")
p=HERE/'run_boundary_v5_cli.py';assert not p.exists();compile(text,str(p),'exec');p.write_text(text)
assert hashlib.sha256(source.read_bytes()).hexdigest()==before
(HERE/'boundary-cli-preparation.json').write_text(json.dumps(dict(original_unchanged_sha256=before,
    new_cli_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),native_games=0,optimizer_steps=0,
    scope='Fresh output argument and actual action-file glob; unchanged frozen learner/collector/algorithm'),indent=2))
