"""Copy exact helpers into this isolated executable package; no old mutations."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent.parent;OLD=ROOT/'experiments/battle-training-continuation-20261020';DEV=ROOT/'experiments/battle-dev-repair-20261023';REF=ROOT/'experiments/battle-episode-boundary-20261023'
sources={}
def copy(source,name,changes=()):
    text=source.read_text()
    for before,after in changes:assert before in text,(name,before);text=text.replace(before,after)
    (HERE/name).write_text(text);sources[name]=dict(source=str(source),sha256=hashlib.sha256(source.read_bytes()).hexdigest())
copy(OLD/'restore_learner.py','restore_learner.py',[
('/root/heroes3-ai-lab/evaluations/battle-diverse60-native-02/models/1792504676114060650/update-30.pt','/mnt/g/Heroes3-AI-Lab/experiments/battle-training-continuation-20261020/monitor-independent-01/user-pause-01/control-update-60.pt'),
('dcaab92162b9c5b4cb9e5d9773067a320fe9b81fe91c1907449d4a7f8374cdaa','443863dd26ea0daaed17cd01ab3dd44a6a16544efac73c96a89839f5b72c0e20')])
copy(ROOT/'research/vector_env.py','recorded_vector.py',[("import importlib.util","import copy\nimport importlib.util"),("outcome = obs.get('terminal_outcome') if term else None","native_step_return=copy.deepcopy(dict(obs=obs,reward=_,terminated=bool(term),truncated=bool(trunc),info=info))\n            outcome = obs.get('terminal_outcome') if term else None"),("outcome=outcome))","outcome=outcome,native_step_return=native_step_return))"),("Path(__file__).with_name('lab-env.py')","Path('/mnt/g/Heroes3-AI-Lab/research/lab-env.py')")])
copy(REF/'credit_extension.py','credit_reference.py')
copy(OLD/'support.py','legacy_support.py')
copy(DEV/'evaluate_policy_steps.py','evaluate_policy_steps.py',[("def main():","def main():\n    from leases import verify_pool\n    verify_pool()")])
copy(DEV/'step_evidence.py','step_evidence.py')
copy(DEV/'run_dev.py','dev_utils.py')
copy(DEV/'legacy_audit.py','dev_raw_auditor.py',[("parent30","parent60"),("2026103600","2026107600")])
copy(DEV/'probability-replay-01/replay.py','replay_dev.py',[("ROOT=Path(__file__).resolve().parents[3]","ROOT=Path(__file__).resolve().parent.parent.parent")])
(HERE/'DERIVATION.json').write_text(json.dumps(sources,indent=2)+'\n')
