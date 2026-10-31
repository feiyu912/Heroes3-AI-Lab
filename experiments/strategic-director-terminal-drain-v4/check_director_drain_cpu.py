"""Artificial CPU-only registry/proof tests; never a native game certificate."""
import argparse
import copy
import json
import tempfile
from pathlib import Path
import director_registry_v1 as ledger
import audit_replan_v3 as replan


def fake_log():
    return '\n'.join([
        'DirectorNativeRequestRegistered id=1 player=0 pack_type=42 type=8MoveHero',
        'DirectorTypedEvent '+json.dumps(dict(event='native_action_sent',native_request_id=1,player=0)),
        'NativeRequestAck id=1 player=0 pack_type=42 success=1',
        'DirectorNativeRequestAck id=1 player=0 pack_type=42 success=1',
        'DirectorTypedEvent '+json.dumps(dict(event='game_over',player=0,completed=True)),
        'TerminalPeerRequestCancellation ids=[7,8]',
        ledger.MARKER,
        'NativeRequestAck id=7 player=1 pack_type=42 success=1',
        'NativeRequestTermination pending_ids=[8]'])+'\n'


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    rejected=[]
    def reject(name,action):
        try:action()
        except (ValueError,AssertionError,KeyError,TypeError):rejected.append(name)
        else:raise AssertionError('Accepted invalid artificial fixture: '+name)
    raw=fake_log();proof=ledger.verify(raw,0)
    assert proof['foreign_waits_pending_at_termination']==1 and proof['director_requests_cancelled']==0
    assert len(proof['foreign_acks_between_intention_and_termination'])==1
    empty=raw.replace('TerminalPeerRequestCancellation ids=[7,8]\n','').replace('NativeRequestTermination pending_ids=[8]','NativeRequestTermination pending_ids=[]')
    assert ledger.verify(empty,0)['foreign_waits_pending_at_termination']==0
    assert ledger.whole_game_pass(True,True,True,0)
    assert not ledger.whole_game_pass(True,True,True,-15)
    assert not ledger.whole_game_pass(True,False,False,0)
    assert not ledger.whole_game_pass(True,True,False,0)
    assert not ledger.whole_game_pass(False,True,True,0)
    assert not ledger.whole_game_pass(True,True,True,False)
    cases={
        'missing_registered_request':raw.replace('DirectorNativeRequestRegistered id=1 player=0 pack_type=42 type=8MoveHero\n',''),
        'missing_actual_director_ack':raw.replace('DirectorNativeRequestAck id=1 player=0 pack_type=42 success=1\n',''),
        'missing_unconditional_actual_owned_ack':raw.replace('\nNativeRequestAck id=1 player=0 pack_type=42 success=1\n','\n'),
        'wrong_registration_owner':raw.replace('Registered id=1 player=0','Registered id=1 player=1'),
        'wrong_ack_owner':raw.replace('DirectorNativeRequestAck id=1 player=0','DirectorNativeRequestAck id=1 player=1'),
        'wrong_native_pack_type':raw.replace('DirectorNativeRequestAck id=1 player=0 pack_type=42','DirectorNativeRequestAck id=1 player=0 pack_type=8'),
        'false_actual_director_ack':raw.replace('DirectorNativeRequestAck id=1 player=0 pack_type=42 success=1','DirectorNativeRequestAck id=1 player=0 pack_type=42 success=0'),
        'duplicate_registration':raw+'DirectorNativeRequestRegistered id=1 player=0 pack_type=42 type=8MoveHero\n',
        'duplicate_ack':raw+'DirectorNativeRequestAck id=1 player=0 pack_type=42 success=1\n',
        'missing_scoped_marker':raw.replace(ledger.MARKER,'All players have ended the game. Ending game after native ACK drain.'),
        'duplicate_scoped_marker':raw+ledger.MARKER+'\n',
        'missing_native_terminal':raw.replace('"completed": true','"completed": false'),
        'missing_actual_termination':raw.replace('NativeRequestTermination pending_ids=[8]\n',''),
        'owned_id_in_intention':raw.replace('Cancellation ids=[7,8]','Cancellation ids=[1,7,8]'),
        'owned_id_in_actual_termination':raw.replace('pending_ids=[8]','pending_ids=[1,8]'),
        'termination_id_not_intended':raw.replace('pending_ids=[8]','pending_ids=[9]'),
        'foreign_difference_without_actual_ack':raw.replace('NativeRequestAck id=7 player=1 pack_type=42 success=1\n',''),
        'foreign_difference_ack_wrong_owner':raw.replace('NativeRequestAck id=7 player=1','NativeRequestAck id=7 player=0'),
        'already_acked_id_still_terminated':raw.replace('pending_ids=[8]','pending_ids=[7,8]'),
        'registered_type_name_not_numeric_pack_id':raw.replace('pack_type=42 type=8MoveHero','type=8MoveHero'),
        'fake_typed_send_without_registered_id':raw.replace('"native_request_id": 1','"native_request_id": 2'),
        'generic_ack_different_from_director_ack':raw.replace('\nNativeRequestAck id=1 player=0 pack_type=42','\nNativeRequestAck id=1 player=0 pack_type=99'),
    }
    for name,bad in cases.items():reject(name,lambda bad=bad:ledger.verify(bad,0))
    with tempfile.TemporaryDirectory(prefix='fake-director-drain-cpu-only-') as temporary:
        root=Path(temporary)
        for name in replan.CORE_RAW_FILES:(root/name).write_text('FAKE CPU FIXTURE; NOT A GAME\n')
        (root/'client.log').write_text(raw)
        (root/'PLAN.json').write_text(json.dumps(dict(owned_player=0,terminal_ack_scope='director',termination_registry_semantics='atomic-termination-closed-registry-v3',audit_epoch=ledger.AUDIT_EPOCH,fixture=True)))
        core=dict(whole_game_valid=True,native_game_completed=True,transport_drained=True,contract_errors=[],
                  terminal_ack_scope='director',owned_player=0,director_registry_proof=proof,
                  termination_registry_semantics='atomic-termination-closed-registry-v3',
                  audit_epoch=ledger.AUDIT_EPOCH,input_audit_epoch=ledger.AUDIT_EPOCH,read_only_legacy_reaudit=False,
                  compiled_native_epoch_proven=True,candidate_manifest_sha256=replan.sha(Path(__file__).with_name('CANDIDATE_MANIFEST.json')),
                  raw_sha256={name:replan.sha(root/name) for name in replan.CORE_RAW_FILES},
                  auditor_sha256={name:replan.sha(path) for name,path in replan.CORE_AUDITORS.items()})
        replan.verify_proof_bindings(root,core)  # Narrow hash/registry predicate only.
        wrong=copy.deepcopy(core);wrong['terminal_ack_scope']='all'
        reject('old_scope_core_proof',lambda:replan.verify_proof_bindings(root,wrong))
        wrong=copy.deepcopy(core);wrong['termination_registry_semantics']='atomic-termination-v2'
        reject('old_open_registry_epoch',lambda:replan.verify_proof_bindings(root,wrong))
        wrong=copy.deepcopy(core);wrong['director_registry_proof']['registered_count']=99
        reject('changed_registry_core_proof',lambda:replan.verify_proof_bindings(root,wrong))
        wrong=copy.deepcopy(core);wrong['raw_sha256']['client.log']='0'*64
        reject('other_game_core_proof',lambda:replan.verify_proof_bindings(root,wrong))
        wrong=copy.deepcopy(core);wrong['auditor_sha256']['director_registry_v1.py']='0'*64
        reject('wrong_registry_auditor_source',lambda:replan.verify_proof_bindings(root,wrong))
        wrong=copy.deepcopy(core);wrong['owned_player']=1
        reject('wrong_core_owner',lambda:replan.verify_proof_bindings(root,wrong))
    args.out.mkdir(parents=True,exist_ok=False)
    result=dict(passed=True,fixture=True,real_execution_certified=False,native_games=0,GPU_operations=0,
                optimizer_steps=0,training_samples=0,positive_narrow_predicates=4,rejection_checks=rejected,
                whole_game_negative_cases=['killed_exit_minus15','event_prefix_without_terminal','no_transport_drain','invalid_execution_contract','boolean_is_not_exitcode'],
                source_sha256={str(path):replan.sha(path) for path in
                               [Path(__file__),Path(ledger.__file__),Path(replan.__file__),Path(__file__).with_name('audit_game_v6.py')]},
                limitation='Artificial registry/hash predicates only. Full native execution, native outcome and process exit0 are not supplied by these fixtures.')
    (args.out/'AUDIT.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))


if __name__=='__main__':main()
