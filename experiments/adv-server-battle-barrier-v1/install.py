"""Install an explicit post-request battle barrier in the isolated adventure server.

No rules, rewards or battle mechanics change. Original server sources are retained.
Only turn-start saves without active battles are supported by the current lab.
"""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
TREE = Path('/root/heroes3-ai-lab/src/vcmi-adv')


def patch(relative, old, new):
    path = TREE / relative
    text = path.read_text()
    if new in text:
        return
    assert text.count(old) == 1, f'Unexpected server source: {relative}'
    backup = HERE / 'source-before' / relative
    backup.parent.mkdir(parents=True, exist_ok=True)
    assert not backup.exists(), f'Refusing to overwrite historical source {backup}'
    backup.write_bytes(path.read_bytes())
    path.write_text(text.replace(old, new, 1))


patch('server/CGameHandler.h',
      '\tstd::set<PlayerColor> uiReadyForDialogs;',
      '\tstd::set<PlayerColor> uiReadyForDialogs;\n\n'
      '\t// Transport-only barrier; never used to alter game state or legality.\n'
      '\tstd::set<PlayerColor> pendingBattleBarriers;')
patch('server/battles/BattleProcessor.cpp',
      '\t//notify interfaces\n\tPlayerBlocked pb;',
      '\t// Release only after the complete server request and all battle queries.\n'
      '\tif(player.isValidPlayer())\n'
      '\t\tgameHandler->pendingBattleBarriers.insert(player);\n'
      '\t//notify interfaces\n\tPlayerBlocked pb;')
patch('server/CGameHandler.cpp',
      '\t\tsendPackageResponse(true);\n\t}\n}\n\nCGameHandler::CGameHandler',
      '\t\tsendPackageResponse(true);\n\t}\n\n'
      '\t// BattleEnded and movement-query removal can arrive in either order.\n'
      '\t// Notify readiness only here, after all consequences of this request\n'
      '\t// (including deferred prompts and victory checks) and its ACK.\n'
      '\tfor(auto it = pendingBattleBarriers.begin(); it != pendingBattleBarriers.end();)\n'
      '\t{\n'
      '\t\tconst auto player = *it;\n'
      '\t\tconst bool inBattle = std::any_of(gs->currentBattles.begin(), gs->currentBattles.end(),\n'
      '\t\t\t[player](const auto & battle)\n'
      '\t\t\t{\n'
      '\t\t\t\treturn battle->getSidePlayer(BattleSide::ATTACKER) == player ||\n'
      '\t\t\t\t\tbattle->getSidePlayer(BattleSide::DEFENDER) == player;\n'
      '\t\t\t});\n'
      '\t\tif(queries->topQuery(player) || inBattle)\n'
      '\t\t{\n'
      '\t\t\t++it;\n'
      '\t\t\tcontinue;\n'
      '\t\t}\n'
      '\t\tit = pendingBattleBarriers.erase(it);\n'
      '\t\tPlayerBlocked ready;\n'
      '\t\tready.player = player;\n'
      '\t\tready.reason = PlayerBlocked::UPCOMING_BATTLE;\n'
      '\t\tready.startOrEnd = PlayerBlocked::BLOCKADE_ENDED;\n'
      '\t\tlogGlobal->trace("Adventure battle barrier ready for player %s", player.toString());\n'
      '\t\tsendAndApply(ready);\n'
      '\t}\n}\n\nCGameHandler::CGameHandler')
files = ['server/CGameHandler.h', 'server/CGameHandler.cpp', 'server/battles/BattleProcessor.cpp']
(HERE / 'installed-source-sha256.json').write_text(json.dumps(
    {name: hashlib.sha256((TREE / name).read_bytes()).hexdigest() for name in files}, indent=2))
print('Installed isolated server battle readiness barrier')
