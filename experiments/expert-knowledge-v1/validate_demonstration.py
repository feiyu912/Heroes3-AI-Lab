"""Validate JSON/JSONL/gzip demonstrations without loading a model or game."""
import argparse
import gzip
import json
from pathlib import Path
import sys

from audit_human_pilot import digest


def load(path):
    opener = gzip.open if str(path).endswith('.gz') else open
    with opener(path, 'rt', encoding='utf-8') as stream:
        if str(path).removesuffix('.gz').endswith('.jsonl'):
            rows = [json.loads(line) for line in stream if line.strip()]
            assert rows and rows[0].get('record_type') == 'episode', 'JSONL must start with episode header'
            assert all(row.get('record_type') == 'decision' for row in rows[1:]), 'Unexpected JSONL record type'
            header = rows[0]
            return dict(schema=header['schema'], source=header['source'], episode=header['episode'],
                        decisions=[{k:v for k,v in row.items() if k != 'record_type'} for row in rows[1:]])
        return json.load(stream)


def adapt_legacy(data):
    row = data['episode']
    policy = row.get('policy')
    assert policy in ['expert', 'teacher'], 'A model-baseline trajectory is not an expert demonstration'
    outcome = row.get('terminal_outcome')
    normalized = dict(schema='expert-demonstration-v1',
        source=dict(kind='script' if policy == 'expert' else 'search', trajectory_origin='engine_execution',
                    verified=False, creator='local-vcmi-coverage/search-candidate',
                    version=data['decisions'][0]['expert_version'] if data.get('decisions') else None,
                    source_reference=None, permission='local-generated-no-human-media', verification_evidence=None),
        episode=dict(battle_id=row['battle_id'], tactic_id=row['tactic_id'], scenario_seed=row['seed'],
                     actor_side=int(row['role'] == 'defender'),
                     rules_version='gym11241d496db95541766498373e23245a67847a97/engine-e956242503f465ae6ec0a62a3aeb2c4ea179db5c',
                     outcome=dict(terminated=row['terminated'], truncated=row['truncated'], terminal_outcome=outcome),
                     permanent_army_loss=row.get('permanent_army_loss_by_creature'),
                     quality_tier='Q2', verification_evidence=None), decisions=[])
    for record in data['decisions']:
        normalized['decisions'].append({key:record[key] for key in
            ['observation','legal_actions','expert_action','actor_side','tactic_id','battle_id','scenario_seed','expert_version']})
        normalized['decisions'][-1].update(action_origin='engine_executed', action_value=None)
    return normalized


def evidence(reference, scope, battle_id, required_checks, base, failures):
    if not isinstance(reference, dict) or not reference.get('path') or not reference.get('sha256'):
        failures.append(scope + ': no evidence artifact')
        return
    path = Path(reference['path'])
    if not path.is_absolute():
        path = base/path
    try:
        if digest(path) != reference['sha256']:
            failures.append(scope + ': evidence SHA mismatch')
            return
        report = json.loads(path.read_text())
        if report.get('schema') != 'expert-evidence-v1' or report.get('scope') != scope or report.get('passed') is not True:
            failures.append(scope + ': evidence schema/scope/pass mismatch')
        if report.get('battle_id') != battle_id:
            failures.append(scope + ': evidence belongs to different battle')
        for check in required_checks:
            if report.get('checks', {}).get(check) is not True:
                failures.append(scope + ': unproven check ' + check)
    except (OSError, ValueError, TypeError) as error:
        failures.append(scope + ': unreadable evidence ' + repr(error))


def validate(data, base):
    errors, unknown, strict = [], [], []
    def require(condition, message):
        if not condition:
            errors.append(message)
    def schema_check(value, schema, location):
        types = schema.get('type')
        if types:
            types = [types] if isinstance(types,str) else types
            matches = {'object':isinstance(value,dict),'array':isinstance(value,list),
                       'string':isinstance(value,str),'integer':type(value) is int,
                       'number':type(value) in [int,float],'boolean':type(value) is bool,'null':value is None}
            if not any(matches.get(name,False) for name in types):
                errors.append(location+': schema type mismatch')
                return
        if 'const' in schema:
            require(value == schema['const'], location+': schema const mismatch')
        if 'enum' in schema:
            require(value in schema['enum'], location+': schema enum mismatch')
        if isinstance(value,dict):
            for key in schema.get('required',[]):
                require(key in value, location+': missing '+key)
            for key,child in value.items():
                if key in schema.get('properties',{}):
                    schema_check(child,schema['properties'][key],location+'.'+key)
                elif schema.get('additionalProperties') is False:
                    errors.append(location+': unexpected '+key)
        if isinstance(value,list):
            require(len(value) >= schema.get('minItems',0), location+': too few items')
            if schema.get('uniqueItems'):
                require(len({json.dumps(item,sort_keys=True) for item in value}) == len(value),location+': repeated items')
            for index,item in enumerate(value):
                schema_check(item,schema.get('items',{}),location+'['+str(index)+']')
        if isinstance(value,str):
            require(len(value) >= schema.get('minLength',0), location+': too short')
            if 'pattern' in schema:
                import re
                require(re.search(schema['pattern'],value) is not None,location+': pattern mismatch')
    schema_check(data,json.loads((Path(__file__).parent/'expert_demonstration_schema.json').read_text()),'bundle')
    require(data.get('schema') == 'expert-demonstration-v1', 'Unknown demonstration schema')
    source, episode, decisions = data.get('source', {}), data.get('episode', {}), data.get('decisions', [])
    require(source.get('kind') in ['script','search','human_structured'], 'Unsupported source kind; video inference is not a trajectory')
    origin = source.get('trajectory_origin')
    require(origin in ['engine_execution','human_recorded','experimental_reconstruction'], 'Unknown trajectory origin')
    require(isinstance(source.get('verified'), bool), 'source.verified must be explicit boolean')
    if source.get('kind') == 'human_structured':
        require(origin == 'human_recorded', 'Reconstructed/engine trajectories cannot be original human operations')
    else:
        require(origin != 'human_recorded', 'Script/search trajectory cannot claim original human operations')
    for key in ['creator','version','source_reference','permission','verification_evidence']:
        require(key in source, 'Missing source field: ' + key)
    for key in ['battle_id','tactic_id','scenario_seed','actor_side','rules_version','outcome',
                'permanent_army_loss','quality_tier','verification_evidence']:
        require(key in episode, 'Missing episode field: ' + key)
        if episode.get(key) is None and key != 'verification_evidence':
            unknown.append('episode.'+key)
    require(bool(episode.get('battle_id')), 'Missing battle ID')
    require(episode.get('actor_side') in [0,1,None], 'Invalid actor side')
    require(episode.get('quality_tier') in ['Q0','Q1','Q2','Q3','Q4'], 'Invalid quality tier')
    require(isinstance(decisions,list) and bool(decisions), 'No decision records')
    complete_legal = True
    for index, record in enumerate(decisions):
        prefix = 'decision-'+str(index)+': '
        for key in ['observation','legal_actions','expert_action','actor_side','tactic_id','battle_id',
                    'scenario_seed','expert_version','action_origin','action_value']:
            require(key in record, prefix+'missing '+key)
        for key in ['actor_side','tactic_id','battle_id','scenario_seed']:
            require(record.get(key) == episode.get(key), prefix+'episode mismatch at '+key)
        require(record.get('action_origin') in ['engine_executed','human_recorded','unknown'], prefix+'video-guessed or unsupported action origin')
        if origin == 'human_recorded':
            require(record.get('action_origin') == 'human_recorded', prefix+'human trace lacks recorded human action')
        elif record.get('action_origin') == 'human_recorded':
            errors.append(prefix+'engine/reconstructed trace mislabeled human action')
        observation, legal, action = record.get('observation'), record.get('legal_actions'), record.get('expert_action')
        if observation is None or legal is None or action is None or record.get('action_origin') == 'unknown':
            complete_legal = False
            unknown.append(prefix+'observation/action/legal evidence incomplete')
            continue
        require(isinstance(observation,dict), prefix+'observation must be object')
        require(isinstance(legal,list) and bool(legal), prefix+'legal actions must be nonempty list')
        if not isinstance(observation,dict) or not isinstance(legal,list):
            complete_legal = False
            continue
        require(all(type(value) is int for value in legal), prefix+'legal IDs must be integers')
        require(len(legal) == len(set(legal)), prefix+'duplicate legal action')
        require(observation.get('active_action_ids') == legal, prefix+'legal IDs differ from observation mask')
        require(type(action) is int and action in legal, prefix+'expert action not legal')
        for key in ['nodes','edges']:
            require(key in observation, prefix+'missing graph '+key)
        if record.get('expert_version') is None:
            unknown.append(prefix+'expert version unknown')
    endpoint = episode.get('outcome')
    terminal = endpoint.get('terminal_outcome') if isinstance(endpoint,dict) else None
    normal = bool(endpoint and endpoint.get('terminated') is True and endpoint.get('truncated') is False
                  and terminal and terminal.get('result_type') == 0 and terminal.get('winner') in [0,1])
    if normal:
        try:
            winner, initial, casualties = terminal['winner'], terminal['initial_armies'], terminal['casualties']
            for creature,count in initial[1-winner].items():
                require(casualties[str(1-winner)].get(creature,0) == count, 'Normal loser has survivors')
            require(sum(count-casualties[str(winner)].get(creature,0) for creature,count in initial[winner].items()) > 0,
                    'Normal winner has no survivors')
            require(episode['permanent_army_loss'] == casualties[str(episode['actor_side'])], 'Permanent loss differs from raw casualties')
        except (KeyError,TypeError,IndexError):
            errors.append('Normal outcome lacks complete casualty evidence')
    exploratory = not errors and not unknown and complete_legal and normal and episode.get('quality_tier') in ['Q2','Q3','Q4'] and not source.get('synthetic_test_fixture')
    if source.get('synthetic_test_fixture'):
        strict.append('Synthetic validator fixture cannot enter training')
    if not source.get('verified'):
        strict.append('Source not verified; source kind/name alone grants no expert quality')
    if episode.get('quality_tier') not in ['Q3','Q4']:
        strict.append('Below Q3; exploratory Q2 must not be called verified expert learning')
    if not normal:
        strict.append('No complete normal terminal outcome; BC Q3 forbidden')
    if unknown or not complete_legal:
        strict.append('Unknown required training evidence')
    if source.get('kind') == 'human_structured' and not all(source.get(k) for k in ['creator','source_reference','permission']):
        strict.append('Human source lacks identity/reference/permission')
    evidence(source.get('verification_evidence'), 'source', episode.get('battle_id'),
             ['source_traceable','permission_confirmed','not_video_inference'], base, strict)
    evidence(episode.get('verification_evidence'), 'tactic', episode.get('battle_id'),
             ['rules_compatible','replay_legal','normal_outcome','action_quality_compared',
              'counterplay_tested','random_variants_tested'], base, strict)
    return dict(structurally_valid=not errors, legal_actions_complete=complete_legal,
                normal_terminal=normal, bc_exploratory_eligible=exploratory,
                bc_q3_eligible=exploratory and not strict, errors=errors, unknown=unknown,
                q3_denials=strict, samples=len(decisions), source_kind=source.get('kind'),
                trajectory_origin=origin, quality_tier=episode.get('quality_tier'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('input')
    parser.add_argument('--mode',choices=['audit','bc-exploratory','bc-q3'],default='audit')
    parser.add_argument('--output')
    parser.add_argument('--normalized-output')
    args = parser.parse_args()
    path = Path(args.input).resolve()
    try:
        data = load(path)
        legacy = data.get('schema') != 'expert-demonstration-v1' and 'episode' in data and 'decisions' in data
        legacy_errors = []
        if legacy:
            import audit_human_pilot as audit
            registry = {case['id']:case for case in audit.read(audit.PILOT/'scenarios.json')}
            canonical = audit.read(audit.PILOT/'runs'/(data['episode']['battle_id']+'.json'))
            assert all(canonical.get(key) == value for key,value in data['episode'].items()), 'Legacy inner episode differs from canonical report'
            assert canonical['demonstration_sha256'] == digest(path), 'Legacy archive differs from canonical SHA'
            audit.audit_episode(canonical, registry, 'legacy-ingestion')
            legacy_errors = list(audit.ERRORS)
            data = adapt_legacy(data)
        result = validate(data,path.parent)
        result['errors'].extend(legacy_errors)
        if legacy_errors:
            result.update(structurally_valid=False,bc_exploratory_eligible=False,bc_q3_eligible=False)
        result.update(input=str(path),input_sha256=digest(path),legacy_adapted=legacy,mode=args.mode,
                      evidence_limit='This gate verifies records and hashed audit attestations; it does not itself simulate/replay the battle or authenticate a human identity.')
        key = {'audit':'structurally_valid','bc-exploratory':'bc_exploratory_eligible','bc-q3':'bc_q3_eligible'}[args.mode]
        result['passed'] = result[key]
        if args.normalized_output:
            assert result['structurally_valid'], 'Do not export malformed or mislabeled records'
            destination = Path(args.normalized_output)
            assert not destination.exists(), 'Preserve previous normalized data'
            destination.write_text(json.dumps(data,ensure_ascii=False)+'\n')
    except (OSError,ValueError,AssertionError,KeyError,TypeError,IndexError) as error:
        result = dict(passed=False,input=str(path),mode=args.mode,errors=[repr(error)])
    if args.output:
        Path(args.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False))
    sys.exit(0 if result['passed'] else 2)


if __name__ == '__main__':
    main()
