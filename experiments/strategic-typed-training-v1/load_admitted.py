"""Read a sealed admission and verify raw-evidence and output hash chains."""
import hashlib,json
from pathlib import Path
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(directory):
    directory=Path(directory);admission=json.loads((directory/'AUDIT.json').read_text())
    if admission.get('passed') is not True or admission.get('replay_actions_logprobs_values_rng_exact') is not True:
        raise ValueError('Exact CUDA/native admission required')
    if not all(sha(f)==h for f,h in admission['input_sha256'].items()) or not all(sha(directory/f)==h for f,h in admission['output_sha256'].items()):
        raise ValueError('Admitted input/output hash changed')
    episode=json.loads((directory/'episode.json').read_text())
    if sha(episode['raw_audit_path'])!=episode['raw_audit_sha256']:raise ValueError('Raw audit changed')
    raw=json.loads(Path(episode['raw_audit_path']).read_text())
    if raw.get('whole_game_valid') is not True or raw.get('contract_errors'):raise ValueError('Invalid native game')
    samples=[json.loads(s) for s in (directory/'samples.jsonl').read_text().splitlines()]
    if len(samples)!=admission['samples_admitted'] or len(samples)!=episode['decisions']:raise ValueError('Admission count mismatch')
    if len({s['decision_id'] for s in samples})!=len(samples) or len({s['native_request_id'] for s in samples})!=len(samples):
        raise ValueError('Duplicate policy/native binding')
    return samples,[episode],admission
