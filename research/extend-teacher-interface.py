"""Add optional BattleAI unit-action labels to the isolated training fork."""
from pathlib import Path
import difflib

root = Path('/root/heroes3-ai-lab/src/gym')
patches = []


def edit(relative, old, new):
    path = root / relative
    before = path.read_text()
    if old == '\tstate->onActiveStack(astack, roundcounter);' and 'LAB_BATTLEAI_TEACHER' in before:
        return
    if old.startswith('\t\tauto evaluator = BattleEvaluator') and 'LAB_BATTLEAI_TEACHER_TURNS' in before:
        return
    if new in before and new not in old:
        return
    if old not in before:
        assert new in before, relative
        return
    assert before.count(old) == 1, relative
    after = before.replace(old, new)
    path.write_text(after)
    patches.extend(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                       fromfile='a/' + relative, tofile='b/' + relative))


edit('vcmi/AI/MMAI/schema/v15/types.h',
     '\tvirtual const TerminalOutcome & getTerminalOutcome() const = 0;',
     '\tvirtual int getTeacherAction() const = 0;\n\tvirtual std::string getTeacherDescription() const = 0;\n\tvirtual const TerminalOutcome & getTerminalOutcome() const = 0;')
edit('vcmi/AI/MMAI/BAI/v15/supplementary_data_v15.h',
     '\tS15::TerminalOutcome terminalOutcome;',
     '\tint teacherAction = -1;\n\tstd::string teacherDescription;\n\tint getTeacherAction() const override { return teacherAction; }\n\tstd::string getTeacherDescription() const override { return teacherDescription; }\n\tS15::TerminalOutcome terminalOutcome;')
edit('vcmi_gym/connectors/v15/threadconnector.cpp',
     'py::arg("terminal_outcome") = p_outcome',
     'py::arg("terminal_outcome") = p_outcome,\n            py::arg("teacher_action_id") = sup->getTeacherAction(),\n            py::arg("teacher_action_description") = sup->getTeacherDescription()')

# Export the existing helpers, so teacher and BattleAI use identical settings.
edit('vcmi/AI/BattleAI/BattleAI.cpp',
     'static float getStrengthRatio(std::shared_ptr<CBattleInfoCallback> cb, BattleSide side)',
     'float getStrengthRatio(std::shared_ptr<CBattleInfoCallback> cb, BattleSide side)')
edit('vcmi/AI/BattleAI/BattleEvaluator.h', 'struct CachedAttack',
     'struct StartInfo;\nclass CBattleInfoCallback;\nDLL_EXPORT float getStrengthRatio(std::shared_ptr<CBattleInfoCallback> cb, BattleSide side);\nDLL_EXPORT int getSimulationTurnsCount(const StartInfo * startInfo);\n\nstruct CachedAttack')
edit('vcmi/AI/MMAI/BAI/v15/BAI_v15.cpp',
     '#include "AI/BattleAI/BattleEvaluator.h"',
     '#include "AI/BattleAI/BattleEvaluator.h"\n#include "callback/IGameInfoCallback.h"\n#include "StartInfo.h"')
edit('vcmi/AI/MMAI/BAI/v15/BAI_v15.cpp',
     '\tstate->onActiveStack(astack, roundcounter);',
     '''\tstate->onActiveStack(astack, roundcounter);

\tconst char * collectTeacher = std::getenv("LAB_BATTLEAI_TEACHER");
\tif(collectTeacher && std::strcmp(collectTeacher, "1") == 0)
\t{
\t\tauto evaluator = BattleEvaluator(env, cb, astack, *cb->getPlayerID(), bid,
\t\t\tbattle->battleGetMySide(), getStrengthRatio(cb->getBattle(bid), battle->battleGetMySide()),
\t\t\tgetSimulationTurnsCount(env->game()->getStartInfo()));
\t\tconst auto teacher = evaluator.selectStackAction(astack);
\t\tstate->supdata->teacherDescription = teacher.toString();
\t\tfor(const int id : state->G->getActiveActionIds())
\t\t{
\t\t\tconst auto candidate = ToBattleAction(*battle, state->G->getById<N::Action>(id), astack);
\t\t\tif(candidate.side != teacher.side || candidate.stackNumber != teacher.stackNumber
\t\t\t\t|| candidate.actionType != teacher.actionType || candidate.spell != teacher.spell
\t\t\t\t|| candidate.target.size() != teacher.target.size())
\t\t\t\tcontinue;
\t\t\tbool matches = true;
\t\t\tfor(std::size_t i = 0; i < teacher.target.size(); ++i)
\t\t\t\tmatches = matches && candidate.target.at(i).unitValue == teacher.target.at(i).unitValue
\t\t\t\t\t&& candidate.target.at(i).hexValue == teacher.target.at(i).hexValue;
\t\t\tif(matches)
\t\t\t{
\t\t\t\tstate->supdata->teacherAction = id;
\t\t\t\tbreak;
\t\t\t}
\t\t}
\t}
''')
if patches:
    Path('/mnt/g/Heroes3-AI-Lab/research/teacher-interface.patch').write_text(''.join(patches))
edit('vcmi/AI/MMAI/BAI/v15/BAI_v15.cpp',
     '''\t\t\tbool matches = true;
\t\t\tfor(std::size_t i = 0; i < teacher.target.size(); ++i)
\t\t\t\tmatches = matches && candidate.target.at(i).unitValue == teacher.target.at(i).unitValue
\t\t\t\t\t&& candidate.target.at(i).hexValue == teacher.target.at(i).hexValue;''',
     '''\t\t\tconst auto candidateTargets = candidate.getTarget(battle.get());
\t\t\tconst auto teacherTargets = teacher.getTarget(battle.get());
\t\t\tbool matches = true;
\t\t\tfor(std::size_t i = 0; i < teacherTargets.size(); ++i)
\t\t\t{
\t\t\t\tif(teacher.actionType == EActionType::WALK_AND_ATTACK && i == 1)
\t\t\t\t\tmatches = matches && battle->battleGetUnitByPos(candidateTargets.at(i).hexValue)
\t\t\t\t\t\t== battle->battleGetUnitByPos(teacherTargets.at(i).hexValue);
\t\t\t\telse
\t\t\t\t\tmatches = matches && candidateTargets.at(i).hexValue == teacherTargets.at(i).hexValue;
\t\t\t}''')
if patches:
    Path('/mnt/g/Heroes3-AI-Lab/research/teacher-mapping-fix.patch').write_text(''.join(patches))
print('Teacher interface patch applied')
edit('vcmi/AI/MMAI/BAI/v15/BAI_v15.cpp',
     '\t\tauto evaluator = BattleEvaluator(env, cb, astack, *cb->getPlayerID(), bid,\n\t\t\tbattle->battleGetMySide(), getStrengthRatio(cb->getBattle(bid), battle->battleGetMySide()),\n\t\t\tgetSimulationTurnsCount(env->game()->getStartInfo()));',
     '''\t\tint teacherTurns = getSimulationTurnsCount(env->game()->getStartInfo());
\t\tif(const char * turns = std::getenv("LAB_BATTLEAI_TEACHER_TURNS"))
\t\t{
\t\t\tteacherTurns = std::stoi(turns);
\t\t\tif(teacherTurns != 2 && teacherTurns != 4 && teacherTurns != 10)
\t\t\t\tthrow std::runtime_error("Teacher horizon must be 2, 4 or 10");
\t\t}
\t\tauto evaluator = BattleEvaluator(env, cb, astack, *cb->getPlayerID(), bid,
\t\t\tbattle->battleGetMySide(), getStrengthRatio(cb->getBattle(bid), battle->battleGetMySide()), teacherTurns);''')
edit('vcmi/AI/MMAI/BAI/v15/BAI_v15.cpp',
     '\t\tint teacherTurns = getSimulationTurnsCount(env->game()->getStartInfo());',
     '\t\tconst auto teacherStart = std::chrono::steady_clock::now();\n\t\tint teacherTurns = getSimulationTurnsCount(env->game()->getStartInfo());')
edit('vcmi/AI/MMAI/BAI/v15/BAI_v15.cpp',
     '\t\tstate->supdata->teacherDescription = teacher.toString();',
     '''\t\tconst auto teacherUs = std::chrono::duration_cast<std::chrono::microseconds>(std::chrono::steady_clock::now() - teacherStart).count();
\t\tstate->supdata->teacherDescription = teacher.toString() + "; teacher_eval_us=" + std::to_string(teacherUs);''')
