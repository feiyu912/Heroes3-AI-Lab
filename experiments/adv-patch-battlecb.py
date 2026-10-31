"""Fourth patch: give adventure AIs a battle callback.

installNewPlayerInterface(..., bool battlecb = false) means initBattleInterface() is never called
for AI players, so CAdventureAI::cbc stays null. CAdventureAI::battleStart() then dereferences it
inside suspendWaitTillRealize() and aborts on the first encounter (confirmed by gdb:
#0 CAdventureAI::battleStart <- CClient::battleStarted).

Only DirectorAI opts in, so the native Nullkiller2 path keeps its previous behaviour.
"""
from pathlib import Path

PATH = Path('/root/heroes3-ai-lab/src/vcmi-adv/client/Client.cpp')
OLD = "\t\t\t\tinstallNewPlayerInterface(AIFactory::createAdventureAI(AiToGive), color);"
NEW = ("\t\t\t\t// DirectorAI needs a CBattleCallback: CAdventureAI::battleStart dereferences it.\n"
       "\t\t\t\tinstallNewPlayerInterface(AIFactory::createAdventureAI(AiToGive), color, AiToGive == \"DirectorAI\");")


def main():
    text = PATH.read_text()
    if NEW in text:
        print('already patched')
        return
    if OLD not in text:
        raise SystemExit('call site not found; inspect Client.cpp before patching')
    PATH.write_text(text.replace(OLD, NEW, 1))
    print(f'patched {PATH}')


if __name__ == '__main__':
    main()
