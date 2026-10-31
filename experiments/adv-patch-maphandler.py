"""Second patch for the isolated adventure build.

Upstream skipped CMapHandler creation in headless mode unless IS_ML, because battle-only runs
never touch GAME->map(). An adventure game does, so with ENABLE_ML=OFF every map access threw
"Invalid access to GameInstance::map" on the first turn.

Only src/vcmi-adv is modified; src/gym/vcmi stays byte-identical.
"""
from pathlib import Path

PATH = Path('/root/heroes3-ai-lab/src/vcmi-adv/client/Client.cpp')
OLD = """	if(!settings["session"]["headless"].Bool() || IS_ML)
	{
		GAME->setMapInstance(std::make_unique<CMapHandler>(&gameState().getMap()));
		logNetwork->trace("Creating mapHandler: %d ms", GAME->server().th->getDiff());
	}"""
NEW = """	// Adventure-layer build: the map handler is required for any adventure map game.
	// Upstream skipped it in headless mode for battle-only ML runs, which breaks GAME->map().
	{
		GAME->setMapInstance(std::make_unique<CMapHandler>(&gameState().getMap()));
		logNetwork->trace("Creating mapHandler: %d ms", GAME->server().th->getDiff());
	}"""


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
