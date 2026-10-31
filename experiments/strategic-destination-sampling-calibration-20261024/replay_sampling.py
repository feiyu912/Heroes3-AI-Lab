import sys
from pathlib import Path
LOCAL=Path(__file__).resolve().parent
BASE=LOCAL;RUN=LOCAL.parent/'strategic-active-opponent-learning-20261024';sys.path.append(str(RUN))
sys.path.append(str(BASE))
from pipeline_common import validate_job,training_variant,source_inputs,capsule_inputs,validate_capsule,audit_metadata,validate_native_epoch,validate_cells,clean_environment,AUDITOR,NATIVE,MARKER,EPOCH,BASE
"""Admit only complete raw-certified episodes after exact CUDA sampling replay."""
import argparse,hashlib,json,math
from pathlib import Path
from collect_episode import owned_resources,sha,write
from onpolicy_broker import OnPolicyBroker
HERE=LOCAL

def main():
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--native-audit',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    run=a.run.resolve();native=json.loads(a.native_audit.read_text());plan=json.loads((run/'PLAN.json').read_text());execution=json.loads((run/'EXECUTION.json').read_text())
    validate_job(argparse.Namespace(arm=plan['arm'],opponent=plan['opponent'],logical_update=plan['logical_update'],seed=plan['seed'],map=plan['map'],player=plan['owned_player'],checkpoint=Path(plan['checkpoint'])))
    validate_native_epoch(native,plan,execution)
    assert native.get('full_state_recruitment_verified') is True and native.get('free_transfer_verified') is True and plan.get('threat_replan')=='off'
    assert native['whole_game_valid'] and native['native_game_completed'] and not native['contract_errors']
    assert native['native_game_completed'] and native['transport_drained'] and execution['input_sha_unchanged'] and execution['client_exit']==0
    assert execution.get('transport_drained') is True or native.get('wrapper_terminal_observation_corrected') is True
    assert native['owned_player']==plan['owned_player'] and plan['sampling']=='manual within-move T0.25 CUDA multinomial'
    assert all(sha(run/name)==h for name,h in native['raw_sha256'].items())
    assert all(sha(Path(path))==h for path,h in plan['hashes'].items())
    # New native auditor/manifest/source resolution is strict in validate_native_epoch.
    ready=json.loads((run/'agent/broker-ready.json').read_text());checkpoint=Path(plan['checkpoint'])
    assert ready['model_sha256']==sha(checkpoint) and ready['device']=='cuda' and ready['mode']=='onpolicy_cuda_move_temperature_v1'
    proposals=[json.loads(s) for s in (run/'agent/typed-broker.jsonl').read_text().splitlines()]
    normalized=[json.loads(s) for s in (a.native_audit.parent/'events.jsonl').read_text().splitlines()]
    assert normalized==[json.loads(s) for s in (run/'typed.jsonl').read_text().splitlines()],'Audit normalized events differ from actual raw typed mirror'
    sent={e['decision_id']:e for e in normalized if e['event']=='native_action_sent' and e['decision_id'] is not None}
    assert len(sent)==sum(e['event']=='native_action_sent' and e['decision_id'] is not None for e in normalized),'Duplicate native policy dispatch'
    assert len(sent)==len(proposals)==native['counts']['new_policy_decisions']
    variant=training_variant(plan['map'],plan['owned_player'],plan['opponent'],plan['arm'])
    assert plan['map_variant']==variant and plan['multiplier']==variant['multiplier']
    assert sha(run/('data/vcmi/Maps/adv/'+plan['map']+'.vmap'))==variant['sha256']
    from collections import Counter
    from qualification import require_qualification
    binding=require_qualification()
    catalog=json.loads(Path(binding['catalog_path']).read_text())
    ids={e['canonical_key']:e['creature_id'] for e in catalog['entries']}
    first=json.loads((run/'strategy-trace.jsonl').read_text().splitlines()[0])
    assert first['event']=='turn_start' and first['day']==1 and first['player']==plan['owned_player'] and len(first['heroes'])==1
    expected=Counter()
    for stack in variant['modified_army']:expected[ids[stack['type']]]+=stack['amount']
    actual=Counter()
    for cid,amount in first['heroes'][0]['army']:actual[cid]+=amount
    assert actual==expected,'Actual initial owned army differs from the registered treatment'
    material=json.dumps(dict(seed=plan['seed'],map=plan['map'],player=plan['owned_player'],opponent=plan['opponent'],logical_update=plan['logical_update']),sort_keys=True).encode()
    assert plan['sampling_seed']==int.from_bytes(hashlib.sha256(material).digest()[:8],'little')%(2**63-1)
    job={k:plan[k] for k in ['seed','map','owned_player','opponent','logical_update','arm','multiplier']};job['checkpoint_sha256']=ready['model_sha256']
    episode_id=hashlib.sha256(json.dumps(job,sort_keys=True).encode()).hexdigest()
    own_colour='red' if plan['owned_player']==0 else 'blue';reward=1. if native['winner']==own_colour else -1.
    assert native['winner'] in ('red','blue')
    rows=[]
    with owned_resources():
        import torch
        state=torch.load(run/'agent/sampling-state.pt',map_location='cpu',weights_only=True)
        assert state['schema']=='strategic-move-temperature-calibration-sampling-state-v1' and state['move_temperature']==0.25 and state['new_PPO_admissions']==0
        assert state['device']=='cuda' and state['decisions']==len(proposals) and state['checkpoint_sha256']==ready['model_sha256'] and state['sampling_seed']==plan['sampling_seed']
        replay=OnPolicyBroker(checkpoint,plan['sampling_seed'])
        assert torch.equal(replay.initial_state.cpu(),state['initial_state'])
        for number,old in enumerate(proposals,1):
            raw=(run/f'agent/request-{number:08d}.json').read_bytes();new=replay.propose(raw,number)
            assert old['device']=='cuda' and old['sampling']=='torch.multinomial_generator'
            for key in ['request','action','old_logprob','old_value','response','request_sha256','model_sha256','build_candidate_count','build_probability','recruit_candidate_count','recruit_probability','economy_epoch','raw_logits','effective_logits','raw_probabilities','effective_probabilities','raw_operation_probabilities','effective_operation_probabilities','distribution_epoch','move_temperature','manual_exploration_setting','manual_setting_is_learning','diagnostic_only','new_PPO_admissions']:
                assert old[key]==new[key],(number,key,old[key],new[key])
            response=old['response'];binding=sent[number]
            assert binding['candidate']==old['request']['candidates'][old['action']]
            assert all(binding[k]==response[k] for k in ['decision_id','player','hero','own_turn','op','request_sha256','selected_index'])
            assert math.isfinite(old['old_logprob']) and math.isfinite(old['old_value'])
            rows.append(dict(episode_id=episode_id,valid=True,execution_verified=True,request=old['request'],action=old['action'],
                action_type=response['op'],old_logprob=old['old_logprob'],old_value=old['old_value'],**{'return':reward},
                decision_id=number,native_request_id=binding['native_request_id'],request_sha256=response['request_sha256'],policy_sha256=ready['model_sha256']))
        assert torch.equal(replay.generator.get_state().cpu(),state['final_state'])
        assert replay.choices==len(proposals)
    assert all(sha(Path(path))==h for path,h in plan['hashes'].items())
    manifest=dict(episode_id=episode_id,valid=True,reward=reward,decisions=len(rows),native_consumption_verified=True,
        native=dict(completed=True,inputs_unchanged=True),raw_audit_path=str(a.native_audit.resolve()),raw_audit_sha256=sha(a.native_audit),
        sampling_replay_exact=True,checkpoint_sha256=ready['model_sha256'],sampling_seed=plan['sampling_seed'],job=job)
    capsule=Path(plan['capsule'])
    runtime=dict(capsule_manifest_sha256=sha(capsule/'build-source-manifest.json'),native_artifacts={n:sha(capsule/'bin'/n) for n in ['vcmiclient','vcmiserver','libvcmi.so']})
    manifest['runtime']=runtime
    manifest['transport_drained']=True
    manifest['pipeline_epoch']=EPOCH
    manifest['economy_epoch']='learned-economy-build-recruit-v1'
    manifest['native_flow_epoch']='learned-economy-build-recruit-v1'
    manifest['threat_replan']='off'
    manifest['catalog_sha256']=native['catalog_sha256']
    manifest['policy_recruits']=sum(r['action_type']=='recruit' for r in rows)
    assert manifest['policy_recruits']==native['actual_recruits_checked']
    manifest['policy_builds']=sum(r['action_type']=='build' for r in rows)
    # No samples/episode admission files are ever written by this diagnostic.
    a.out.mkdir(parents=True,exist_ok=False)
    manifest.update(diagnostic_only=True,new_PPO_admissions=0,manual_exploration_setting=True,manual_setting_is_learning=False)
    write(a.out/'DIAGNOSTIC.json',manifest)
    report=dict(passed=True,samples_admitted=0,decisions_replayed=len(rows),new_PPO_admissions=0,manual_exploration_setting=True,manual_setting_is_learning=False,policy_moves=sum(r['action_type']=='move' for r in rows),
        pipeline_epoch=EPOCH,economy_epoch='learned-economy-build-recruit-v1',policy_builds=manifest['policy_builds'],
        native_flow_epoch='learned-economy-build-recruit-v1',threat_replan='off',full_state_recruitment_verified=True,free_transfer_verified=True,catalog_sha256=native['catalog_sha256'],policy_recruits=manifest['policy_recruits'],
        policy_end_turns=sum(r['action_type']=='end_turn' for r in rows),automatic_end_turns_excluded=native['counts']['automatic_end_turns'],
        sampling_device='cuda',replay_actions_logprobs_values_rng_exact=True,optimizer_steps=0,
        native_episode_winner=native['winner'],ability_improvement_claim=False,
        input_sha256={str(f):sha(f) for f in [a.native_audit,run/'agent/sampling-state.pt',run/'agent/typed-broker.jsonl',Path(__file__)]},
        output_sha256={n:sha(a.out/n) for n in ['DIAGNOSTIC.json']})
    write(a.out/'AUDIT.json',report);print(json.dumps(report,indent=2))
if __name__=='__main__':main()




