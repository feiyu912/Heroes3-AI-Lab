"""Synthetic CPU checks of the narrow -1 MakeAction exception; no game proof."""
import argparse
import hashlib
import json
from pathlib import Path
import director_registry_v1 as ledger
from check_director_drain_cpu import fake_log


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    rejected=[]
    def reject(name,raw):
        try:ledger.verify(raw,0)
        except (ValueError,KeyError,TypeError):rejected.append(name)
        else:raise AssertionError('Accepted artificial invalid owner/packet: '+name)
    base=fake_log()
    neutral='Sending a request "10MakeAction". It\'ll have an ID=90.\nNativeRequestAck id=90 player=-1 pack_type=198 success=1\n'
    good=base.replace('TerminalPeerRequestCancellation ids=[7,8]',neutral+'TerminalPeerRequestCancellation ids=[7,8]')
    proof=ledger.verify(good,0)
    assert proof['verified_neutral_makeaction_ack_count']==1 and proof['registered_count']==1
    assert proof['registered_ids']==[1] and proof['director_requests_cancelled']==0
    for owner in ['-2','-3','-4','-5','-99','8','255','-0','-01','+1']:
        reject('unverified_owner_'+owner,good.replace('id=90 player=-1','id=90 player='+owner))
    reject('neutral_unverified_packet',good.replace('id=90 player=-1 pack_type=198','id=90 player=-1 pack_type=42'))
    reject('neutral_wrong_actual_request_type',good.replace('request "10MakeAction"','request "8MoveHero"'))
    reject('neutral_without_actual_send',good.replace('Sending a request "10MakeAction". It\'ll have an ID=90.\n',''))
    reject('neutral_send_after_ack',good.replace(neutral,'NativeRequestAck id=90 player=-1 pack_type=198 success=1\nSending a request "10MakeAction". It\'ll have an ID=90.\n'))
    reject('neutral_claimed_owned_registration',good.replace('Registered id=1 player=0','Registered id=1 player=-1'))
    reject('neutral_claimed_owned_ack',good.replace('DirectorNativeRequestAck id=1 player=0','DirectorNativeRequestAck id=1 player=-1'))
    reject('owned_ack_replaced_by_neutral',good.replace('NativeRequestAck id=1 player=0 pack_type=42','NativeRequestAck id=1 player=-1 pack_type=198'))
    args.out.mkdir(parents=True,exist_ok=False)
    result=dict(passed=True,fixture=True,real_execution_certified=False,native_games=0,GPU_operations=0,
                optimizer_steps=0,training_samples=0,positive_neutral_ack_case=True,rejected=rejected,
                source_sha256={str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in [Path(__file__),Path(ledger.__file__)]})
    (args.out/'AUDIT.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))


if __name__=='__main__':main()
