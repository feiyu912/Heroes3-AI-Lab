"""Patch ML references that are not guarded by the ML() macro in the isolated source copy.

The upstream tree is a battle-only fork: BattleProcessor.cpp reads gameHandler->mlplugin without
the ML() guard, so it cannot compile with ENABLE_ML=OFF. Only the isolated copy under
src/vcmi-adv is modified; src/gym/vcmi stays byte-identical.
"""
from pathlib import Path

PATH = Path('/root/heroes3-ai-lab/src/vcmi-adv/server/battles/BattleProcessor.cpp')
OLD = """	const bool regenerateLayout = IS_ML && (
		gameHandler->mlplugin->config.randomTerrainChance > 0 ||
		gameHandler->mlplugin->config.randomArmies ||
		gameHandler->mlplugin->config.creatureBankChance > 0 ||
		gameHandler->mlplugin->config.tightFormationChance > 0);"""
NEW = """#ifdef ENABLE_ML
	const bool regenerateLayout = (
		gameHandler->mlplugin->config.randomTerrainChance > 0 ||
		gameHandler->mlplugin->config.randomArmies ||
		gameHandler->mlplugin->config.creatureBankChance > 0 ||
		gameHandler->mlplugin->config.tightFormationChance > 0);
#else
	const bool regenerateLayout = false;
#endif"""


def main():
    text = PATH.read_text()
    if NEW in text:
        print('already patched')
        return
    if OLD not in text:
        raise SystemExit('expected block not found; inspect the file before patching')
    PATH.write_text(text.replace(OLD, NEW, 1))
    print(f'patched {PATH}')


if __name__ == '__main__':
    main()
