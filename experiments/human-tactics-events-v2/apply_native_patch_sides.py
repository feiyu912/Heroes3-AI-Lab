#!/usr/bin/env python3
"""events-v2 native patch (increment 2): add BattleSide info to events.

Applied on top of apply_native_patch.py on the ISOLATED runtime copy only:
  NativeDamageEvent/NativeBattleEvent gain *Side fields so friendly-fire and
  side attribution can be decided natively (not inferred in Python).
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


# ------------------------------------------------------------- types.h
patch('vcmi/AI/MMAI/schema/v15/types.h',
'''	int defenderId = -1;   // CStack::unitId() of damaged stack
	int attackerId = -1;   // CStack::unitId() of attacker (-1: none/effect)''',
'''	int defenderId = -1;   // CStack::unitId() of damaged stack
	int defenderSide = -1; // BattleSide of defender (0/1, -1 unknown)
	int attackerId = -1;   // CStack::unitId() of attacker (-1: none/effect)
	int attackerSide = -1; // BattleSide of attacker (0/1, -1 unknown)''')

patch('vcmi/AI/MMAI/schema/v15/types.h',
'''	int attackerId = -1;   // CStack::unitId()
	int attackFlags = 0;''',
'''	int attackerId = -1;   // CStack::unitId()
	int attackerSide = -1; // BattleSide of attacker (0/1, -1 unknown)
	int attackFlags = 0;''')

# --------------------------------------------------------- state_v15.cpp
patch('vcmi/AI/MMAI/BAI/v15/state_v15.cpp',
'''	ev.attackerId = static_cast<int>(ba.stackAttacking);
	ev.attackFlags = static_cast<int>(ba.flags);
	ev.attackSpellId = ba.spellID.getNum();
	ev.attackTile = ba.tile.toInt();

	for(const auto & elem : ba.bsa)
	{
		S15::NativeDamageEvent de;
		de.defenderId = static_cast<int>(elem.stackAttacked);
		de.attackerId = static_cast<int>(elem.attackerID);
		de.damage = elem.damageAmount;''',
'''	ev.attackerId = static_cast<int>(ba.stackAttacking);
	ev.attackFlags = static_cast<int>(ba.flags);
	ev.attackSpellId = ba.spellID.getNum();
	ev.attackTile = ba.tile.toInt();

	{
		const auto * astack = battle.battleGetStackByID(static_cast<int>(ba.stackAttacking), false);
		ev.attackerSide = astack ? static_cast<int>(astack->unitSide()) : -1;
	}

	for(const auto & elem : ba.bsa)
	{
		S15::NativeDamageEvent de;
		de.defenderId = static_cast<int>(elem.stackAttacked);
		de.attackerId = static_cast<int>(elem.attackerID);

		const auto * dstack = battle.battleGetStackByID(static_cast<int>(elem.stackAttacked), false);
		const auto * estack = battle.battleGetStackByID(static_cast<int>(elem.attackerID), false);
		de.defenderSide = dstack ? static_cast<int>(dstack->unitSide()) : -1;
		de.attackerSide = estack ? static_cast<int>(estack->unitSide()) : -1;

		de.damage = elem.damageAmount;''')

# ---------------------------------------------------- threadconnector.cpp
patch('vcmi_gym/connectors/v15/threadconnector.cpp',
'''            p_ev["attacker_id"] = ev.attackerId;
            p_ev["attacker_node"] = nodeIndexOfUnit(ev.attackerId);''',
'''            p_ev["attacker_id"] = ev.attackerId;
            p_ev["attacker_side"] = ev.attackerSide;
            p_ev["attacker_node"] = nodeIndexOfUnit(ev.attackerId);''')

patch('vcmi_gym/connectors/v15/threadconnector.cpp',
'''                p_t["defender_id"] = t.defenderId;
                p_t["defender_node"] = nodeIndexOfUnit(t.defenderId);
                p_t["attacker_id"] = t.attackerId;
                p_t["attacker_node"] = nodeIndexOfUnit(t.attackerId);''',
'''                p_t["defender_id"] = t.defenderId;
                p_t["defender_side"] = t.defenderSide;
                p_t["defender_node"] = nodeIndexOfUnit(t.defenderId);
                p_t["attacker_id"] = t.attackerId;
                p_t["attacker_side"] = t.attackerSide;
                p_t["attacker_node"] = nodeIndexOfUnit(t.attackerId);''')

print('OK: side fields patched')
