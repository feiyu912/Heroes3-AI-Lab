"""Generate minimal Python adapters; never execute collection/admission/training."""
from pathlib import Path
import difflib,json,hashlib
HERE=Path(__file__).resolve().parent;BASE=HERE.parent.parent/'strategic-typed-training-v1'
BOOT='''import sys
from pathlib import Path
LOCAL=Path(__file__).resolve().parent
BASE=LOCAL.parent.parent/'strategic-typed-training-v1'
sys.path.append(str(BASE))
from pipeline_common import source_inputs,capsule_inputs,validate_capsule,audit_metadata,validate_native_epoch,validate_cells,clean_environment,AUDITOR,NATIVE,MARKER,EPOCH,BASE
'''
def rewrite(name,changes):
    original=(BASE/name).read_text();text=original
    for before,after in changes:
        assert text.count(before)==1,(name,before,text.count(before));text=text.replace(before,after,1)
    text=BOOT+text
    (HERE/name).write_text(text)
    (HERE/(name+'.diff')).write_text(''.join(difflib.unified_diff(original.splitlines(True),text.splitlines(True),fromfile='frozen/'+name,tofile='mainline/'+name)))
def main():
    rewrite('collect_episode_v5.py',[
      ('HERE=Path(__file__).resolve().parent','HERE=BASE'),
      ('    capsule,work,checkpoint=args.capsule,args.out,args.checkpoint','    clean_environment();assert args.load_save is None,"New training cells start from the Training map"\n    validate_capsule(args.capsule)\n    capsule,work,checkpoint=args.capsule,args.out,args.checkpoint'),
      ('    if args.load_save:\n        original=args.load_save.resolve();head=original.read_bytes()[:15]',
       '    inputs.extend(source_inputs()+capsule_inputs(capsule))\n    if args.load_save:\n        original=args.load_save.resolve();head=original.read_bytes()[:15]'),
      ("winner=None,game_completed=False,hashes=frozen)","winner=None,game_completed=False,hashes=frozen,**audit_metadata())"),
      ("'winner':None,'optimizer_steps':0,'training_samples':0}","'winner':None,'optimizer_steps':0,'training_samples':0,**audit_metadata()}"),
      ("'Ending game after native ACK drain.' in (work/'client.log').read_text(errors='replace'))\n    # A normal", "MARKER in (work/'client.log').read_text(errors='replace'))\n    # A normal"),
      ("result['transport_drained']=bool(result['game_completed'] and 'Ending game after native ACK drain.' in", "result['transport_drained']=bool(result['game_completed'] and MARKER in")])
    rewrite('admit_episode_v5.py',[
      ('HERE=Path(__file__).resolve().parent','HERE=BASE'),
      ("    assert native['whole_game_valid'] and native['native_game_completed'] and not native['contract_errors']",
       "    validate_native_epoch(native,plan,execution)\n    assert native['whole_game_valid'] and native['native_game_completed'] and not native['contract_errors']"),
      ("    native_sources=HERE.parent/'strategic-typed-native-v1'\n    assert all(sha(native_sources/name)==h for name,h in native['auditor_sha256'].items())",
       "    # Exact three-key source resolution is enforced by validate_native_epoch.\n    # audit_game_v6 + director_registry live in director-terminal-drain-v4;\n    # raw_events_v4 remains in the frozen typed-native directory.")])
    print(json.dumps({'prepared':['collect_episode_v5.py','admit_episode_v5.py'],'native_runs':0,'optimizer_steps':0}))
if __name__=='__main__':main()
