"""New auditor epoch, unchanged capsule03 and same fixed proxy cells."""
from pathlib import Path
HERE=Path(__file__).resolve().parent.parent/'strategic-director-terminal-drain-v4'
OLD=HERE.parent/'strategic-director-terminal-drain-v3'
text=(OLD/'paired_proxy_drain_v3.py').read_text()
start=text.index('    qualification=');end=text.index('    model=TRAIN',start)
text=text[:start]+'''    qualification_proof=HERE/'read-only-requalification-01/AUDIT.json'
    requalification=json.loads(qualification_proof.read_text())
    assert requalification['passed'] and requalification['new_native_games']==0
    assert len(requalification['games'])==4
    assert requalification['audit_epoch']=='director-neutral-makeaction-ack-v4'
    assert all(sha(Path(p))==h for p,h in requalification['source_sha256'].items())
    assert all(sha(Path(p))==h for p,h in requalification['original_batch_input_sha256'].items())
    binding_proof=HERE.parent/'strategic-request-bind-barrier-v2/native-repro-comparison-01/AUDIT.json'
    assert json.loads(binding_proof.read_text())['new_execution_certified']
'''+text[end:]
text=text.replace("sources.extend([qualification/'RESULT.json',qualification/'PLAN.json',binding_proof])", "sources.extend([qualification_proof,binding_proof]+[Path(p) for p in requalification['source_sha256']]+[Path(p) for p in requalification['original_batch_input_sha256']])")
text=text.replace("terminal_ack_scope='director',termination_registry_semantics=", "audit_epoch='director-neutral-makeaction-ack-v4',terminal_ack_scope='director',termination_registry_semantics=")
text=text.replace('closed-registry atomic terminal epoch in BOTH arms.', 'closed-registry atomic native-v3 epoch and narrow neutral ACK auditor-v4 in BOTH arms.')
p=HERE/'paired_proxy_drain_v4.py';assert not p.exists();p.write_text(text);compile(text,str(p),'exec')
print('Prepared; no native game or score produced.')
