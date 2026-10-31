"""Strict CPU parser for actual Director request drain and foreign wait termination.

Parsing a synthetic log does not certify a native game. The caller must separately
verify source/runtime identity, the full raw execution contract and normal exit0.
"""
import json
import re

MARKER = 'All players have ended the game. Ending game after Director request ACK drain.'
AUDIT_EPOCH = 'director-neutral-makeaction-ack-v4'
ANSI = re.compile(r'\x1b\[[0-9;]*m')
REG = re.compile(r'DirectorNativeRequestRegistered id=(\d+) player=(\d+) pack_type=(\d+) type=(\S+)$')
DACK = re.compile(r'DirectorNativeRequestAck id=(\d+) player=(\d+) pack_type=(\d+) success=([01])$')
ACK = re.compile(r'(?<!Director)NativeRequestAck id=(\d+) player=(-?\d+) pack_type=(\d+) success=([01])$')
SENT = re.compile(r'Sending a request "(\S+)"\. It.ll have an ID=(\d+)\.')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def whole_game_pass(contract_valid,native_completed,transport_drained,client_exit):
    """A valid event prefix never substitutes for normal whole-game completion."""
    return (contract_valid is True and native_completed is True and
            transport_drained is True and type(client_exit) is int and client_exit==0)


def snapshot(line, prefix):
    raw = line.split(prefix,1)[1].strip()
    ids = json.loads(raw)
    require(isinstance(ids,list) and all(type(value) is int and value>0 for value in ids),
            'Malformed terminal request ID snapshot')
    require(len(set(ids))==len(ids),'Duplicate ID in terminal request snapshot')
    return ids


def verify(raw, owned):
    require(type(owned) is int and owned in (0,1),'Invalid owned Director player')
    registered, director_acks, real_acks, native_sent = {}, {}, {}, {}
    request_types,neutral_acks = {},[]
    intents, terminations, marker_lines, terminal_lines = [], [], [], []
    for number, text in enumerate(raw.splitlines(),1):
        line = ANSI.sub('',text)
        request=SENT.search(line)
        if request:
            identity=int(request[2])
            require(identity>0 and identity not in request_types,'Duplicate actual client request ID')
            request_types[identity]=dict(type=request[1],line=number)
        if 'DirectorNativeRequestRegistered ' in line:
            m = REG.search(line)
            require(m is not None,'Malformed Director registration')
            identity,player,pack_type = map(int,m.groups()[:3])
            require(identity>0 and player==owned and identity not in registered,'Wrong owner/duplicate Director registration')
            registered[identity] = dict(line=number,player=player,pack_type=pack_type,type=m[4])
        elif 'DirectorNativeRequestAck ' in line:
            m = DACK.search(line)
            require(m is not None,'Malformed Director actual ACK')
            identity,player,pack_type,success = map(int,m.groups())
            require(identity>0 and identity not in director_acks and player==owned and success==1,
                    'Wrong owner/duplicate/unsuccessful Director ACK')
            director_acks[identity] = dict(line=number,player=player,pack_type=pack_type,success=success)
        elif 'NativeRequestAck ' in line:
            m = ACK.search(line)
            require(m is not None,'Malformed actual native ACK')
            identity,player,pack_type,success = map(int,m.groups())
            require(identity>0 and identity not in real_acks,'Duplicate actual native ACK')
            require(m[2]==str(player),'Noncanonical actual ACK player code')
            require(player in range(8) or player==-1,'Unverified actual ACK player code')
            if player==-1:
                require(pack_type==198 and identity in request_types and
                        request_types[identity]['type']=='10MakeAction' and
                        request_types[identity]['line']<number,
                        'Neutral ACK is not the verified capsule03 MakeAction request')
                neutral_acks.append(dict(native_request_id=identity,line=number,pack_type=pack_type,
                                         actual_request_line=request_types[identity]['line'],actual_request_type='10MakeAction'))
            real_acks[identity] = dict(line=number,player=player,pack_type=pack_type,success=success)
        if 'TerminalPeerRequestCancellation ids=' in line:
            intents.append(dict(line=number,ids=snapshot(line,'TerminalPeerRequestCancellation ids=')))
        if 'NativeRequestTermination pending_ids=' in line:
            terminations.append(dict(line=number,ids=snapshot(line,'NativeRequestTermination pending_ids=')))
        if MARKER in line:
            marker_lines.append(number)
        if 'DirectorTypedEvent ' in line:
            event = json.JSONDecoder().raw_decode(line.split('DirectorTypedEvent ',1)[1])[0]
            if event['event']=='game_over' and event.get('completed') is True and event['player']==owned:
                terminal_lines.append(number)
            if event['event']=='native_action_sent':
                identity = event['native_request_id']
                require(identity not in native_sent,'Duplicate actual typed native send')
                native_sent[identity] = dict(line=number,player=event['player'])
    require(len(marker_lines)==1 and len(terminal_lines)==1 and terminal_lines[0]<marker_lines[0],
            'Missing/duplicate/out-of-order actual owned terminal or scoped shutdown marker')
    require(len(terminations)==1 and marker_lines[0]<terminations[0]['line'],
            'Missing/duplicate/pre-shutdown actual native request termination')
    require(registered and set(registered)==set(director_acks),'Director register/actual ACK sets do not match')
    for identity,reg in registered.items():
        ack = director_acks[identity]
        require(reg['line']<ack['line']<marker_lines[0],'Director registration/ACK outside drain boundary')
        require(reg['pack_type']==ack['pack_type'],'Director actual ACK packet type mismatch')
        require(identity in real_acks,'Director ACK lacks the unconditional actual native ACK line')
        actual = real_acks[identity]
        require((actual['player'],actual['pack_type'],actual['success'])==
                (ack['player'],ack['pack_type'],ack['success']),'Actual ACK versus Director ledger mismatch')
        require(reg['line']<actual['line']<ack['line']<marker_lines[0],'Actual Director ACK ordering mismatch')
    for identity,sent in native_sent.items():
        require(identity in registered and sent['player']==owned and registered[identity]['line']<sent['line'],
                'Typed policy/automatic action lacks prior real Director registration')
    # At most one cancellation-intention snapshot belongs to this one shutdown.
    require(len(intents)<=1,'Duplicate foreign cancellation intention')
    intent = intents[0] if intents else dict(line=marker_lines[0],ids=[])
    actual = terminations[0]
    require(terminal_lines[0]<intent['line']<actual['line'], 'Foreign cancellation intention outside terminal cleanup')
    intent_ids,actual_ids = set(intent['ids']),set(actual['ids'])
    require(not (intent_ids | actual_ids) & set(registered), 'Director request appears in foreign terminal cancellation')
    require(actual_ids<=intent_ids,'Actual termination includes requests absent from foreign intention snapshot')
    settled = []
    for identity in sorted(intent_ids-actual_ids):
        ack = real_acks.get(identity)
        require(ack is not None and ack['player']!=owned and intent['line']<ack['line']<actual['line'],
                'Foreign intention/termination difference lacks an actual intervening ACK')
        settled.append(dict(native_request_id=identity,actual_ack=ack))
    for identity in actual_ids:
        ack = real_acks.get(identity)
        require(ack is None or ack['line']>actual['line'], 'Terminated foreign wait had already received its ACK')
    return dict(passed=True,terminal_ack_scope='director',owned_player=owned,audit_epoch=AUDIT_EPOCH,
                registered_count=len(registered),actual_director_ack_count=len(director_acks),
                registered_ids=sorted(registered),policy_and_auto_request_count=len(native_sent),
                marker_line=marker_lines[0],owned_terminal_line=terminal_lines[0],
                cancellation_intention=intent,actual_termination=actual,
                foreign_waits_pending_at_termination=len(actual_ids),
                actual_atomic_cleared_ids=sorted(actual_ids),
                exact_cancelled_id_count_certified=True,
                termination_registry_semantics='atomic-termination-closed-registry-v3',
                foreign_acks_between_intention_and_termination=settled,
                director_requests_cancelled=0,
                verified_neutral_makeaction_ack_count=len(neutral_acks),verified_neutral_makeaction_acks=neutral_acks,
                limitation='Native termination atomically returns cleared wait IDs. Clearing a foreign wait is not an ACK/application and does not prove that its action never executed. The caller must verify this v3 native capsule and normal exit0.')
