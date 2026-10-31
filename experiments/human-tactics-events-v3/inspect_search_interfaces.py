"""Read source/bindings only; never construct an env or start a game."""
from pathlib import Path
import re

root=Path('/root/heroes3-ai-lab-events-v2/src/gym')
queries=[
 ('vcmi_gym/envs/v15/pyconnector.py',r'^    def |VCMI_STARTED|seed'),
 ('vcmi_gym/connectors/v15/threadconnector.cpp',r'\.def\(|\.def_static\(|clone|save|load|snapshot'),
 ('vcmi/AI/BattleAI/HypotheticBattle.h',r'class |HypotheticBattle\(|clone|serialize|nextRound|nextTurn|battle|apply'),
 ('vcmi/AI/BattleAI/HypotheticBattle.cpp',r'HypotheticBattle::|nextRound|nextTurn'),
 ('vcmi/AI/BattleAI/PotentialTargets.h',r'class |struct |public:|private:|attacks|possibleAttacks|bestAction|PotentialTargets'),
 ('vcmi/AI/BattleAI/BattleExchangeVariant.h',r'class |public:|private:|evaluate|calculate|find|simulate'),
 ('vcmi/server/CGameHandler.h',r'save|load|gameState|gs;|getRandom'),
 ('vcmi/lib/CGameState.h',r'serialize|rand|battle|CGameState\('),
 ('vcmi/server/battles/BattleActionProcessor.h',r'public:|private:|makeAction|makeAttack|process|BattleActionProcessor'),
]
for rel,pattern in queries:
    path=root/rel
    print('\nFILE',path)
    if not path.exists():
        print('MISSING');continue
    for n,line in enumerate(path.read_text().splitlines(),1):
        if re.search(pattern,line):
            print(f'{n}:{line}')
