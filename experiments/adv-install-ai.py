"""Install the custom DirectorAI into the isolated adventure tree.

Registers a third adventure AI name ("DirectorAI") next to the native Nullkiller2 and EmptyAI.
Only src/vcmi-adv is touched; the frozen battle tree keeps its own AIFactory.
"""
import shutil
from pathlib import Path

SRC = Path('/mnt/g/Heroes3-AI-Lab/experiments/adv-ai')
TREE = Path('/root/heroes3-ai-lab/src/vcmi-adv')
DST = TREE / 'AI' / 'DirectorAI'


def install_files():
    DST.mkdir(parents=True, exist_ok=True)
    for name in ('CDirectorAI.h', 'CDirectorAI.cpp', 'CMakeLists.txt', 'StdInc.h'):
        shutil.copyfile(SRC / name, DST / name)
    print(f'installed {DST}')


def patch_ai_cmake():
    path = TREE / 'AI' / 'CMakeLists.txt'
    text = path.read_text()
    if 'add_subdirectory(DirectorAI)' in text:
        print('AI/CMakeLists.txt already patched')
        return
    text = text.replace('add_subdirectory(EmptyAI)', 'add_subdirectory(EmptyAI)\nadd_subdirectory(DirectorAI)', 1)
    path.write_text(text)
    print('patched AI/CMakeLists.txt')


def patch_factory():
    path = TREE / 'lib' / 'callback' / 'AIFactory.cpp'
    text = path.read_text()
    if 'CDirectorAI.h' not in text:
        text = text.replace('#include "../../AI/EmptyAI/CEmptyAI.h"',
                            '#include "../../AI/EmptyAI/CEmptyAI.h"\n#include "../../AI/DirectorAI/CDirectorAI.h"', 1)
    marker = """	auto ret = std::make_shared<CEmptyAI>();"""
    addition = """	if(name == "DirectorAI")
	{
		auto ret = std::make_shared<CDirectorAI>();
		ret->dllName = name;
		return ret;
	}

"""
    if addition not in text:
        if marker not in text:
            raise SystemExit('CEmptyAI fallback block not found in AIFactory.cpp')
        text = text.replace(marker, addition + marker, 1)

    availability = """bool AIFactory::isAvailableAdventureAI(const std::string & name)
{
	if(name == "EmptyAI")
		return true;"""
    availability_new = """bool AIFactory::isAvailableAdventureAI(const std::string & name)
{
	if(name == "EmptyAI")
		return true;
	if(name == "DirectorAI")
		return true;"""
    if 'if(name == "DirectorAI")\n\t\treturn true;' not in text:
        if availability not in text:
            raise SystemExit('isAvailableAdventureAI block not found')
        text = text.replace(availability, availability_new, 1)
    path.write_text(text)
    print('patched AIFactory.cpp')


def patch_facade():
    path = TREE / 'libFacade' / 'CMakeLists.txt'
    text = path.read_text()
    if 'DirectorAI' in text:
        print('libFacade/CMakeLists.txt already patched')
        return
    marker = '\t\ttarget_link_libraries(vcmi PRIVATE EmptyAI)\n'
    if marker not in text:
        raise SystemExit('EmptyAI link line not found in libFacade/CMakeLists.txt')
    text = text.replace(marker, marker + '\t\ttarget_link_libraries(vcmi PRIVATE DirectorAI)\n', 1)
    path.write_text(text)
    print('patched libFacade/CMakeLists.txt')


if __name__ == '__main__':
    install_files()
    patch_ai_cmake()
    patch_facade()
    patch_factory()
