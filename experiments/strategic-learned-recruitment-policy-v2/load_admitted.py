"""Read a sealed admission and verify raw-evidence and output hash chains."""
import hashlib,json
from pathlib import Path
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(directory):
    directory=Path(directory);admission=json.loads((directory/'AUDIT.json').read_text())
    if admission.get('passed') is not True or admission.get('replay_actions_logprobs_values_rng_exact') is not True:
        raise ValueError('Exact CUDA/native admission required')
    from qualification import require_qualification
    b=require_qualification()
    if admission.get('catalog_sha256')!=b['catalog_sha256']:raise ValueError('Actual runtime catalog differs')
    if admission.get('full_state_recruitment_verified') is not True or admission.get('free_transfer_verified') is not True:raise ValueError('Full actual recruit/transfer evidence required')
    if admission.get('pipeline_epoch')!='strategic-learned-recruitment-training-v1' or admission.get('economy_epoch')!='learned-economy-build-recruit-v1':raise ValueError('Schema6 economy admission epoch required')
    if not all(sha(f)==h for f,h in admission['input_sha256'].items()) or not all(sha(directory/f)==h for f,h in admission['output_sha256'].items()):
        raise ValueError('Admitted input/output hash changed')
    episode=json.loads((directory/'episode.json').read_text())
    if sha(episode['raw_audit_path'])!=episode['raw_audit_sha256']:raise ValueError('Raw audit changed')
    raw=json.loads(Path(episode['raw_audit_path']).read_text())
    raw_directory=Path(raw['raw'])
    if not raw.get('raw_sha256') or not raw.get('source_sha256'):raise ValueError('Complete original raw/source hash chains required')
    if not all(sha(raw_directory/name)==h for name,h in raw['raw_sha256'].items()):raise ValueError('Original native raw evidence changed after admission')
    if not all(sha(path)==h for path,h in raw['source_sha256'].items()):raise ValueError('Original native source inputs changed after admission')
    collection_plan=json.loads((raw_directory/'PLAN.json').read_text())
    if not all(sha(path)==h for path,h in collection_plan['hashes'].items()):raise ValueError('Original collection input changed after admission')
    if raw.get('whole_game_valid') is not True or raw.get('contract_errors'):raise ValueError('Invalid native game')
    if raw.get('audit_epoch')!='director-learned-recruitment-v1':raise ValueError('Wrong native free-stock audit epoch')
    if (admission.get('full_state_recruitment_verified') is not True or admission.get('threat_replan')!='off'
            or raw.get('full_state_recruitment_verified') is not True or raw.get('native_flow_epoch')!='learned-economy-build-recruit-v1'):raise ValueError('Missing qualified recruit/transfer evidence')
    samples=[json.loads(s) for s in (directory/'samples.jsonl').read_text().splitlines()]
    if len(samples)!=admission['samples_admitted'] or len(samples)!=episode['decisions']:raise ValueError('Admission count mismatch')
    if len({s['decision_id'] for s in samples})!=len(samples) or len({s['native_request_id'] for s in samples})!=len(samples):
        raise ValueError('Duplicate policy/native binding')
    from encoder import validate
    for sample in samples:validate(sample['request'])
    if sum(s['action_type']=='build' for s in samples)!=admission['policy_builds'] or admission['policy_builds']!=raw['counts']['policy_builds']:raise ValueError('Build evidence count differs')
    if sum(s['action_type']=='recruit' for s in samples)!=admission['policy_recruits'] or admission['policy_recruits']!=raw['actual_recruits_checked']:raise ValueError('Actual recruitment count differs')
    return samples,[episode],admission



