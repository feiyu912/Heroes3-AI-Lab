"""Version the proven full-assets evaluator for explicit same-binary off/once arms."""
import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'strategic-typed-training-v1/evaluate_game_v2.py'
text=OLD.read_text();old_sha=hashlib.sha256(OLD.read_bytes()).hexdigest()
text=text.replace('from live_jsonl import read as read_jsonl',"from pathlib import Path\nsys.path.insert(0,str(Path(__file__).resolve().parent.parent/'strategic-typed-training-v1'))\nfrom live_jsonl import read as read_jsonl",1)
text=text.replace('HERE=Path(__file__).resolve().parent',"HERE=Path(__file__).resolve().parent.parent/'strategic-typed-training-v1'",1)
text=text.replace('opponent=args.opponent,load_save=', 'opponent=args.opponent,threat_replan=args.threat_replan,load_save=',1)
text=text.replace('LAB_ADV_TYPED_EVENTS=str(work/\'typed.jsonl\'))',"LAB_ADV_TYPED_EVENTS=str(work/'typed.jsonl'),LAB_ADV_THREAT_REPLAN=args.threat_replan)",1)
text=text.replace("choices=['takeover-v2-dev-01-river','takeover-v2-dev-02-reserves'],default='takeover-v2-dev-01-river'","choices=['takeover-v2-train-01-mines','takeover-v2-train-02-development'],default='takeover-v2-train-01-mines'")
needle="    p.add_argument('--logical-update'";assert text.count(needle)==1
text=text.replace(needle,"    p.add_argument('--threat-replan',choices=['off','once'],required=True)\n"+needle)
assert 'LAB_ADV_THREAT_REPLAN=args.threat_replan' in text
p=HERE/'run_game.py';assert not p.exists();compile(text,str(p),'exec');p.write_text(text)
(HERE/'RUNNER_MANIFEST.json').write_text(json.dumps(dict(parent_sha256=old_sha,runner_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
    semantics='Same frozen CPU model and runtime; explicit off/once, training diagnostic maps, full41 compiled scripts',optimizer_steps=0),indent=2))
