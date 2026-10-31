"""Third patch for the isolated adventure build: per-player AI selection.

The --ai CLI flag exists in this fork's option list but is never consumed, and the AI name comes
from settings["ai"]["adventureEnemyAI"] for every AI player. To pit our own policy against the
native AI we need per-player control, so honour LAB_ADV_AI_<playerSlot> environment variables.
Only src/vcmi-adv is modified.
"""
from pathlib import Path

PATH = Path('/root/heroes3-ai-lab/src/vcmi-adv/client/Client.cpp')
OLD = """				auto AiToGive = aiNameForPlayer(playerInfo.second, false, alliedToHuman);
				logNetwork->info("Player %s will be lead by %s", color.toString(), AiToGive);"""
NEW = """				auto AiToGive = aiNameForPlayer(playerInfo.second, false, alliedToHuman);
				// Lab hook: allow per-player AI selection without touching the settings schema.
				{
					const std::string envName = "LAB_ADV_AI_" + std::to_string(static_cast<int>(playerInfo.first));
					if(const char * requested = std::getenv(envName.c_str()))
						if(AIFactory::isAvailableAdventureAI(requested))
							AiToGive = requested;
				}
				logNetwork->info("Player %s will be lead by %s", color.toString(), AiToGive);"""


def main():
    text = PATH.read_text()
    if 'LAB_ADV_AI_' in text:
        print('already patched')
        return
    if OLD not in text:
        raise SystemExit('expected block not found; inspect Client.cpp before patching')
    PATH.write_text(text.replace(OLD, NEW, 1))
    print(f'patched {PATH}')


if __name__ == '__main__':
    main()
