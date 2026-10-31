#!/usr/bin/env python3
"""events-v2 native patch: expose native battle events to Python.

Applies ONLY to the isolated WSL runtime copy:
  /root/heroes3-ai-lab-events-v2/src/gym/{vcmi,vcmi_gym}

Audit-only addition (never model input):
  schema/v15/types.h                     : NativeDamageEvent/NativeBattleEvent/
                                           BattleEvents + ISupplementaryData::
                                           getBattleEvents()
  schema/v15/graph.h                     : IGraph::getUnitNodeIndexByUnitId()
  BAI/v15/graph/graph_v15.{h,cpp}        : implementation of the above
  BAI/v15/supplementary_data_v15.h       : carry events by value + getter
  BAI/v15/state_v15.{h,cpp}              : record actionStarted / battleAttack /
                                           actionFinished / battleEnd events;
                                           deliver+clear with each supplementary data
  BAI/v15/BAI_v15.{h,cpp}               : implement battleAttack/actionStarted
                                           overrides; forward actionFinished
  connectors/v15/threadconnector.cpp    : serialize "battle_events" into the
                                           Python obs dict (additive key)
"""
from pathlib import Path

ROOT = Path('/root/heroes3-ai-lab-events-v2/src/gym')


def patch(rel, old, new, count=1):
    p = ROOT / rel
    text = p.read_text()
    if new in text:
        print(f'  [skip] already patched: {rel}')
        return
    n = text.count(old)
    assert n == count, f'{rel}: expected {count} occurrence(s) of anchor, found {n}'
    p.write_text(text.replace(old, new, count))
    print(f'  [ok]   {rel}')


def insert_before(rel, anchor, block):
    p = ROOT / rel
    text = p.read_text()
    if block in text:
        print(f'  [skip] already patched: {rel}')
        return
    assert text.count(anchor) == 1, f'{rel}: anchor not unique/found'
    p.write_text(text.replace(anchor, block + anchor, 1))
    print(f'  [ok]   {rel} (insert)')


# ============================================================ schema/v15/types.h
EVENT_TYPES = '''// events-v2 audit extension: native battle events (NOT model input).
// Unit ids are stable within a battle (CStack::unitId()).
// damage flags use BattleStackAttacked::EFlags: KILLED=1, SECONDARY=2,
// CLONE_KILLED=8, SPELL_EFFECT=16
struct MMAI_DLL_LINKAGE NativeDamageEvent
{
\tint defenderId = -1;   // CStack::unitId() of damaged stack
\tint defenderSide = -1; // BattleSide of defender (0/1, -1 unknown)
\tint attackerId = -1;   // CStack::unitId() of attacker (-1: none/effect)
\tint attackerSide = -1; // BattleSide of attacker (0/1, -1 unknown)
\tint64_t damage = 0;
\tint killed = 0;
\tint flags = 0;
\tint spellId = -1;      // SpellID::getNum() when SPELL_EFFECT, else -1
};

// attackFlags use BattleAttack::EFlags: SHOT=1, COUNTER=2, LUCKY=4,
// UNLUCKY=8, BALLISTA_DOUBLE_DMG=16, DEATH_BLOW=32, SPELL_LIKE=64
struct MMAI_DLL_LINKAGE NativeBattleEvent
{
\tenum class Kind : uint8_t { ACTION_STARTED, ACTION_FINISHED, ATTACK, BATTLE_END };
\tKind kind = Kind::ATTACK;

\t// ACTION_STARTED / ACTION_FINISHED / BATTLE_END
\tint actionType = -1;   // EActionType as int (-1 for BATTLE_END)
\tint side = -1;
\tint stackNumber = -1;  // CStack::unitId() (-1/-2: hero action)
\tstd::vector<int> targetHexes;      // per DestinationInfo
\tstd::vector<int> targetUnitValue;  // per DestinationInfo
\tint resultType = -1;   // BATTLE_END only: BattleResult::result
\tint winner = -1;       // BATTLE_END only

\t// ATTACK
\tint attackerId = -1;   // CStack::unitId()
\tint attackerSide = -1; // BattleSide of attacker (0/1, -1 unknown)
\tint attackFlags = 0;
\tint attackSpellId = -1; // SpellID::getNum() when SPELL_LIKE, else -1
\tint attackTile = -1;   // BattleHex.toInt()
\tstd::vector<NativeDamageEvent> targets;
};

using BattleEvents = std::vector<NativeBattleEvent>;

'''
insert_before('vcmi/AI/MMAI/schema/v15/types.h',
              '// This is returned as std::any by IState', EVENT_TYPES)

patch('vcmi/AI/MMAI/schema/v15/types.h',
'''\tvirtual std::string getAnsiRender() const = 0;
\tvirtual ~ISupplementaryData() = default;
};''',
'''\tvirtual std::string getAnsiRender() const = 0;
\tvirtual const BattleEvents & getBattleEvents() const = 0;
\tvirtual ~ISupplementaryData() = default;
};''')

# ============================================================ schema/v15/graph.h
patch('vcmi/AI/MMAI/schema/v15/graph.h',
'''\tvirtual std::vector<int64_t> getActiveActionIds() const = 0;
\tvirtual ~IGraph() = default;''',
'''\tvirtual std::vector<int64_t> getActiveActionIds() const = 0;
\t// events-v2: Unit node index by CStack::unitId(); -1 when absent.
\tvirtual int64_t getUnitNodeIndexByUnitId(uint32_t unitId) const = 0;
\tvirtual ~IGraph() = default;''')

# ============================================================ graph_v15.h
patch('vcmi/AI/MMAI/BAI/v15/graph/graph_v15.h',
'''\tint64_t getNodeIndex(const S15::Graph::INode * node) const override;''',
'''\tint64_t getNodeIndex(const S15::Graph::INode * node) const override;
\tint64_t getUnitNodeIndexByUnitId(uint32_t unitId) const override;''')

# ============================================================ graph_v15.cpp
patch('vcmi/AI/MMAI/BAI/v15/graph/graph_v15.cpp',
'''int64_t Graph::getEdgeIndex(const S15::Graph::IEdge * iedge) const''',
'''int64_t Graph::getUnitNodeIndexByUnitId(uint32_t unitId) const
{
\t// Unit nodes may be absent (dead before this graph was built).
\tauto node = getByExtraIndex<Nodes::Unit>(unitId, false);
\tif(!node)
\t\treturn -1;

\treturn getNodeIndex(node.get());
}

int64_t Graph::getEdgeIndex(const S15::Graph::IEdge * iedge) const''')

# ==================================================== supplementary_data_v15.h
patch('vcmi/AI/MMAI/BAI/v15/supplementary_data_v15.h',
'''\t// Called on activeStack (complete battlefield info)
\tSupplementaryData(
\t\tconst std::string & colorname,
\t\tSide side,
\t\tconst std::shared_ptr<Graph::Graph> & G,
\t\tconst std::vector<AttackLog> & attackLogs,
\t\tS15::CombatResult result
\t)
\t\t: colorname(colorname), side(side), G(G), attackLogs(attackLogs), ended(result != S15::CombatResult::NONE), victory(EI(result) == EI(side)) {};''',
'''\t// Called on activeStack (complete battlefield info)
\tSupplementaryData(
\t\tconst std::string & colorname,
\t\tSide side,
\t\tconst std::shared_ptr<Graph::Graph> & G,
\t\tconst std::vector<AttackLog> & attackLogs,
\t\tconst S15::BattleEvents & battleEvents,
\t\tS15::CombatResult result
\t)
\t\t: colorname(colorname), side(side), G(G), attackLogs(attackLogs), battleEvents(battleEvents), ended(result != S15::CombatResult::NONE), victory(EI(result) == EI(side)) {};''')

patch('vcmi/AI/MMAI/BAI/v15/supplementary_data_v15.h',
'''\tS15::AttackLogs getAttackLogs() const override;''',
'''\tS15::AttackLogs getAttackLogs() const override;
\tconst S15::BattleEvents & getBattleEvents() const override
\t{
\t\treturn battleEvents;
\t}''')

patch('vcmi/AI/MMAI/BAI/v15/supplementary_data_v15.h',
'''\tconst std::vector<AttackLog> & attackLogs;''',
'''\tconst std::vector<AttackLog> & attackLogs;
\tconst S15::BattleEvents battleEvents;''')

# ============================================================== state_v15.h
patch('vcmi/AI/MMAI/BAI/v15/state_v15.h',
'''\tvoid onBattleStacksAttacked(const std::vector<BattleStackAttacked> & bsa);''',
'''\tvoid onBattleStacksAttacked(const std::vector<BattleStackAttacked> & bsa);
\tvoid onBattleAttack(const BattleAttack & ba);
\tvoid onActionStarted(const BattleAction & action);
\tvoid onActionFinished(const BattleAction & action);''')

patch('vcmi/AI/MMAI/BAI/v15/state_v15.h',
'''\tstd::vector<AttackLog> attackLogs;''',
'''\tstd::vector<AttackLog> attackLogs;
\tS15::BattleEvents battleEvents;''')

# ============================================================== state_v15.cpp
patch('vcmi/AI/MMAI/BAI/v15/state_v15.cpp',
'''\tsupdata = std::make_unique<SupplementaryData>(
\t\tcolorname,
\t\tstatic_cast<Side>(side),
\t\tG,
\t\tattackLogs, // store the logs since OUR last turn
\t\tresult
\t);

\tattackLogs.clear(); // accumulate new logs until next turn''',
'''\tsupdata = std::make_unique<SupplementaryData>(
\t\tcolorname,
\t\tstatic_cast<Side>(side),
\t\tG,
\t\tattackLogs, // store the logs since OUR last turn
\t\tbattleEvents, // store the native events since OUR last turn
\t\tresult
\t);

\tattackLogs.clear(); // accumulate new logs until next turn
\tbattleEvents.clear(); // accumulate new events until next turn''')

# BATTLE_END event: push BEFORE onActiveStack (which clears battleEvents)
patch('vcmi/AI/MMAI/BAI/v15/state_v15.cpp',
'''void State::onBattleEnd(const BattleResult & br, int round)
{
\tswitch(br.winner)''',
'''void State::onBattleEnd(const BattleResult & br, int round)
{
\t{
\t\tS15::NativeBattleEvent ev;
\t\tev.kind = S15::NativeBattleEvent::Kind::BATTLE_END;
\t\tev.actionType = -1;
\t\tev.resultType = static_cast<int>(br.result);
\t\tev.winner = static_cast<int>(br.winner);
\t\tbattleEvents.push_back(std::move(ev));
\t}

\tswitch(br.winner)''')

# event recorders: insert before onBattleTriggerEffect definition
STATE_ANCHOR = '''void State::onBattleTriggerEffect(const BattleTriggerEffect & bte)'''
STATE_METHODS = '''void State::onBattleAttack(const BattleAttack & ba)
{
\tS15::NativeBattleEvent ev;
\tev.kind = S15::NativeBattleEvent::Kind::ATTACK;
\tev.attackerId = static_cast<int>(ba.stackAttacking);
\tev.attackFlags = static_cast<int>(ba.flags);
\tev.attackSpellId = ba.spellID.getNum();
\tev.attackTile = ba.tile.toInt();

\t{
\t\tconst auto * astack = battle.battleGetStackByID(static_cast<int>(ba.stackAttacking), false);
\t\tev.attackerSide = astack ? static_cast<int>(astack->unitSide()) : -1;
\t}

\tfor(const auto & elem : ba.bsa)
\t{
\t\tS15::NativeDamageEvent de;
\t\tde.defenderId = static_cast<int>(elem.stackAttacked);
\t\tde.attackerId = static_cast<int>(elem.attackerID);

\t\tconst auto * dstack = battle.battleGetStackByID(static_cast<int>(elem.stackAttacked), false);
\t\tconst auto * estack = battle.battleGetStackByID(static_cast<int>(elem.attackerID), false);
\t\tde.defenderSide = dstack ? static_cast<int>(dstack->unitSide()) : -1;
\t\tde.attackerSide = estack ? static_cast<int>(estack->unitSide()) : -1;

\t\tde.damage = elem.damageAmount;
\t\tde.killed = static_cast<int>(elem.killedAmount);
\t\tde.flags = static_cast<int>(elem.flags);
\t\tde.spellId = (elem.flags & static_cast<int>(BattleStackAttacked::SPELL_EFFECT)) ? elem.spellID.getNum() : -1;
\t\tev.targets.push_back(std::move(de));
\t}

\tbattleEvents.push_back(std::move(ev));
}

void State::onActionStarted(const BattleAction & action)
{
\tS15::NativeBattleEvent ev;
\tev.kind = S15::NativeBattleEvent::Kind::ACTION_STARTED;
\tev.actionType = static_cast<int>(action.actionType);
\tev.side = static_cast<int>(action.side);
\tev.stackNumber = static_cast<int>(action.stackNumber);
\tfor(const auto & dest : action.target)
\t{
\t\tev.targetHexes.push_back(dest.hexValue.toInt());
\t\tev.targetUnitValue.push_back(dest.unitValue);
\t}
\tbattleEvents.push_back(std::move(ev));
}

void State::onActionFinished(const BattleAction & action)
{
\tS15::NativeBattleEvent ev;
\tev.kind = S15::NativeBattleEvent::Kind::ACTION_FINISHED;
\tev.actionType = static_cast<int>(action.actionType);
\tev.side = static_cast<int>(action.side);
\tev.stackNumber = static_cast<int>(action.stackNumber);
\tfor(const auto & dest : action.target)
\t{
\t\tev.targetHexes.push_back(dest.hexValue.toInt());
\t\tev.targetUnitValue.push_back(dest.unitValue);
\t}
\tbattleEvents.push_back(std::move(ev));
}

void State::onBattleTriggerEffect(const BattleTriggerEffect & bte)'''
patch('vcmi/AI/MMAI/BAI/v15/state_v15.cpp', STATE_ANCHOR, STATE_METHODS)

# ================================================================= BAI_v15.h
patch('vcmi/AI/MMAI/BAI/v15/BAI_v15.h',
'''\tvoid battleStacksAttacked(
\t\tconst BattleID & bid,
\t\tconst std::vector<BattleStackAttacked> & bsa,
\t\tbool ranged
\t) override; //called when stack receives damage (after battleAttack())''',
'''\tvoid battleAttack(const BattleID & bid, const BattleAttack * ba) override; //called when stack is performing attack
\tvoid actionStarted(const BattleID & bid, const BattleAction & action) override; //called BEFORE every action

\tvoid battleStacksAttacked(
\t\tconst BattleID & bid,
\t\tconst std::vector<BattleStackAttacked> & bsa,
\t\tbool ranged
\t) override; //called when stack receives damage (after battleAttack())''')

# ================================================================= BAI_v15.cpp
patch('vcmi/AI/MMAI/BAI/v15/BAI_v15.cpp',
'''void BAI::battleStacksAttacked(const BattleID & bid, const std::vector<BattleStackAttacked> & bsa, bool ranged)
{
\tstate->onBattleStacksAttacked(bsa);
}''',
'''void BAI::battleAttack(const BattleID & bid, const BattleAttack * ba)
{
\tif(state)
\t\tstate->onBattleAttack(*ba);
}

void BAI::actionStarted(const BattleID & bid, const BattleAction & action)
{
\tif(state)
\t\tstate->onActionStarted(action);
}

void BAI::battleStacksAttacked(const BattleID & bid, const std::vector<BattleStackAttacked> & bsa, bool ranged)
{
\tif(state)
\t\tstate->onBattleStacksAttacked(bsa);
}''')

patch('vcmi/AI/MMAI/BAI/v15/BAI_v15.cpp',
'''void BAI::actionFinished(const BattleID & bid, const BattleAction & action)
{
\ttacticsHandler->onActionFinished(action);
}''',
'''void BAI::actionFinished(const BattleID & bid, const BattleAction & action)
{
\tif(state)
\t\tstate->onActionFinished(action);
\ttacticsHandler->onActionFinished(action);
}''')

# ======================================================== threadconnector.cpp
OLD_RETURN = '''        return py::dict(
            py::arg("nodes") = p_nodesdict,
            py::arg("edges") = p_edgesdict,
            py::arg("active_action_ids") = p_activeids,
            py::arg("terminal_outcome") = p_outcome,
            py::arg("teacher_action_id") = sup->getTeacherAction(),
            py::arg("teacher_action_description") = sup->getTeacherDescription()
        );
    }'''
NEW_RETURN = '''        // events-v2: native battle events (audit only; not model input).
        // Delivered additively under the "battle_events" key. Each event may
        // reference Unit node indices of *this* graph (-1 when absent).
        auto p_events = py::list();
        const auto * p_graph = sup->getGraph();
        auto nodeIndexOfUnit = [&p_graph](int unitId) -> int64_t {
            if (unitId < 0)
                return -1;
            return p_graph ? p_graph->getUnitNodeIndexByUnitId(static_cast<uint32_t>(unitId)) : -1;
        };

        for (const auto & ev : sup->getBattleEvents())
        {
            py::dict p_ev;
            p_ev["kind"] = static_cast<int>(ev.kind);
            p_ev["action_type"] = ev.actionType;
            p_ev["side"] = ev.side;
            p_ev["stack_number"] = ev.stackNumber;
            p_ev["stack_node"] = nodeIndexOfUnit(ev.stackNumber);
            p_ev["target_hexes"] = ev.targetHexes;
            p_ev["target_unit_value"] = ev.targetUnitValue;
            p_ev["result_type"] = ev.resultType;
            p_ev["winner"] = ev.winner;
            p_ev["attacker_id"] = ev.attackerId;
            p_ev["attacker_side"] = ev.attackerSide;
            p_ev["attacker_node"] = nodeIndexOfUnit(ev.attackerId);
            p_ev["attack_flags"] = ev.attackFlags;
            p_ev["attack_spell_id"] = ev.attackSpellId;
            p_ev["attack_tile"] = ev.attackTile;

            auto p_targets = py::list();
            for (const auto & t : ev.targets)
            {
                py::dict p_t;
                p_t["defender_id"] = t.defenderId;
                p_t["defender_side"] = t.defenderSide;
                p_t["defender_node"] = nodeIndexOfUnit(t.defenderId);
                p_t["attacker_id"] = t.attackerId;
                p_t["attacker_side"] = t.attackerSide;
                p_t["attacker_node"] = nodeIndexOfUnit(t.attackerId);
                p_t["damage"] = t.damage;
                p_t["killed"] = t.killed;
                p_t["flags"] = t.flags;
                p_t["spell_id"] = t.spellId;
                p_targets.append(p_t);
            }
            p_ev["targets"] = p_targets;
            p_events.append(p_ev);
        }

        return py::dict(
            py::arg("nodes") = p_nodesdict,
            py::arg("edges") = p_edgesdict,
            py::arg("active_action_ids") = p_activeids,
            py::arg("terminal_outcome") = p_outcome,
            py::arg("teacher_action_id") = sup->getTeacherAction(),
            py::arg("teacher_action_description") = sup->getTeacherDescription(),
            py::arg("battle_events") = p_events
        );
    }'''
patch('vcmi_gym/connectors/v15/threadconnector.cpp', OLD_RETURN, NEW_RETURN)

print('OK: native patch applied to isolated runtime')
