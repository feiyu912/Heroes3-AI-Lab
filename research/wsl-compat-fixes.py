from pathlib import Path
import difflib

root = Path('/root/heroes3-ai-lab/src/gym')
path = root / 'vcmi/AI/MMAI/BAI/scripted/VIPBot.cpp'
before = path.read_text()
old = 'std::span<const BattleHex> candidates'
new = 'const BattleHexArray & candidates'
if old in before:
    assert before.count(old) == 1
    after = before.replace(old, new)
    path.write_text(after)
    patch = ''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                      fromfile='a/AI/MMAI/BAI/scripted/VIPBot.cpp',
                                      tofile='b/AI/MMAI/BAI/scripted/VIPBot.cpp'))
    Path('/mnt/g/Heroes3-AI-Lab/research/wsl-build-fixes.patch').write_text(patch)
elif new not in before:
    raise RuntimeError('Unexpected VIPBot signature')
print('Applied Boost 1.74 BattleHexArray compatibility fix')

path = root / 'vcmi/ML/CMakeLists.txt'
before = path.read_text()
old = 'target_link_libraries(mlclient PUBLIC vcmi vcmiclientcommon)'
new = ('find_package(Boost REQUIRED COMPONENTS stacktrace_basic)\n'
       'target_link_libraries(mlclient PRIVATE Boost::stacktrace_basic)\n' + old)
if 'target_link_libraries(mlclient PRIVATE Boost::stacktrace_basic)' not in before:
    assert before.count(old) == 1
    after = before.replace(old, new)
    path.write_text(after)
    patch = ''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                      fromfile='a/ML/CMakeLists.txt', tofile='b/ML/CMakeLists.txt'))
    with Path('/mnt/g/Heroes3-AI-Lab/research/wsl-build-fixes.patch').open('a') as out:
        out.write(patch)
print('Applied explicit Boost stacktrace linkage')

path = root / 'vcmi/ML/MLClient.cpp'
before = path.read_text()
old = '\t\tauto l = std::lock_guard(mutex_shutdown);\n\t\tcond_shutdown.notify_all();'
new = ('\t\tauto l = std::lock_guard(mutex_shutdown);\n'
       '\t\tif(flag_shutdown)\n\t\t\treturn;\n'
       '\t\tcond_shutdown.notify_all();')
if old in before:
    assert before.count(old) == 1
    after = before.replace(old, new)
    path.write_text(after)
    patch = ''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                      fromfile='a/ML/MLClient.cpp', tofile='b/ML/MLClient.cpp'))
    with Path('/mnt/g/Heroes3-AI-Lab/research/wsl-build-fixes.patch').open('a') as out:
        out.write(patch)
elif new not in before:
    raise RuntimeError('Unexpected shutdown implementation')
print('Applied idempotent shutdown guard')

path = root / 'vcmi/ML/MLClient.cpp'
before = path.read_text()
old = '\t\tENGINE->async().wait();'
new = '\t\tif(!headless)\n\t\t\tENGINE->async().wait();'
if new not in before:
    assert before.count(old) == 1
    after = before.replace(old, new)
    path.write_text(after)
    patch = ''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                      fromfile='a/ML/MLClient.cpp', tofile='b/ML/MLClient.cpp'))
    with Path('/mnt/g/Heroes3-AI-Lab/research/wsl-build-fixes.patch').open('a') as out:
        out.write(patch)
print('Applied headless shutdown fix: no GUI async runner exists')
