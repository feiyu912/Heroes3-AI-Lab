from pathlib import Path
import difflib

root = Path('/root/heroes3-ai-lab/src/gym')
patch_path = Path('/mnt/g/Heroes3-AI-Lab/research/outcome-isolation.patch')


def replace(relative, old, new):
    path = root / relative
    before = path.read_text()
    if new in before:
        return
    markers = {
        '// This is returned as std::any by IState': 'struct MMAI_DLL_LINKAGE TerminalOutcome',
        '\t}\n}\n\nvoid State::onActiveStack(const CStack * acstack, int round, S15::CombatResult result)':
            'supdata->terminalOutcome.resultType = static_cast<int>(br.result);',
        '        LOG("Creating p_dict...");\n\n        return py::dict(':
            'py::object p_outcome = py::none();',
    }
    if old in markers and markers[old] in before:
        return
    if old.startswith(': version_(version)') and 'initialArmies.at(' in before:
        return
    assert before.count(old) == 1, relative
    after = before.replace(old, new)
    path.write_text(after)
    with patch_path.open('a') as out:
        out.write(''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                    fromfile='a/' + relative, tofile='b/' + relative)))

# Remove an obsolete copy if an earlier incremental application inserted it twice.
types_path = root / 'vcmi/AI/MMAI/schema/v15/types.h'
types_text = types_path.read_text()
obsolete = '''struct MMAI_DLL_LINKAGE TerminalOutcome
{
    int resultType = -1;
    int winner = -1;
    std::array<std::map<int, int>, 2> casualties;
};

'''
if types_text.count('struct MMAI_DLL_LINKAGE TerminalOutcome') == 2:
    assert types_text.count(obsolete) == 1
    types_path.write_text(types_text.replace(obsolete, ''))


replace('vcmi/AI/MMAI/schema/v15/types.h', '#include <cstdint>',
        '#include <array>\n#include <map>\n#include <cstdint>')
replace('vcmi/AI/MMAI/schema/v15/types.h',
        '// This is returned as std::any by IState',
        '''struct MMAI_DLL_LINKAGE TerminalOutcome
{
    int resultType = -1;
    int winner = -1;
    std::array<std::map<int, int>, 2> casualties;
};

// This is returned as std::any by IState''')
replace('vcmi/AI/MMAI/schema/v15/types.h',
        '\tvirtual std::string getAnsiRender() const = 0;',
        '\tvirtual const TerminalOutcome & getTerminalOutcome() const = 0;\n'
        '\tvirtual std::string getAnsiRender() const = 0;')
replace('vcmi/AI/MMAI/BAI/v15/supplementary_data_v15.h',
        '\tstd::string getAnsiRender() const override',
        '''\tconst S15::TerminalOutcome & getTerminalOutcome() const override
\t{
\t\treturn terminalOutcome;
\t}

\tS15::TerminalOutcome terminalOutcome;

\tstd::string getAnsiRender() const override''')
replace('vcmi/AI/MMAI/BAI/v15/state_v15.cpp',
        '\t}\n}\n\nvoid State::onActiveStack(const CStack * acstack, int round, S15::CombatResult result)',
        '''\t}
\tsupdata->terminalOutcome.resultType = static_cast<int>(br.result);
\tsupdata->terminalOutcome.winner = static_cast<int>(br.winner);
\tfor(const auto side : {BattleSide::ATTACKER, BattleSide::DEFENDER})
\t\tfor(const auto & [creature, count] : br.casualties[side])
\t\t\tsupdata->terminalOutcome.casualties.at(static_cast<int>(side)).emplace(creature.getNum(), count);
}

void State::onActiveStack(const CStack * acstack, int round, S15::CombatResult result)''')
replace('vcmi_gym/connectors/v15/threadconnector.cpp',
        '        LOG("Creating p_dict...");\n\n        return py::dict(',
        '''        LOG("Creating p_dict...");
        py::object p_outcome = py::none();
        const auto & outcome = sup->getTerminalOutcome();
        if(outcome.resultType >= 0)
        {
            auto p_casualties = py::dict();
            for(int side = 0; side < 2; ++side)
                p_casualties[py::int_(side)] = py::cast(outcome.casualties.at(side));
            p_outcome = py::dict(py::arg("result_type") = outcome.resultType,
                                py::arg("winner") = outcome.winner,
                                py::arg("casualties") = p_casualties);
        }

        return py::dict(''')
replace('vcmi_gym/connectors/v15/threadconnector.cpp',
        '            py::arg("active_action_ids") = p_activeids',
        '            py::arg("active_action_ids") = p_activeids,\n'
        '            py::arg("terminal_outcome") = p_outcome')
replace('vcmi_gym/envs/v15/vcmi_env.py',
        '            is_success=gnode.BATTLE_WINNER == side,',
        '            is_success=gnode.BATTLE_WINNER == side,\n'
        '            terminal_outcome=obs.get("terminal_outcome"),')
replace('vcmi/lib/VCMIDirs.cpp',
        '''bfs::path VCMIDirsXDG::userDataPath() const
{
#ifdef ML
\treturn bfs::path(".") / "data";''',
        '''bfs::path VCMIDirsXDG::userDataPath() const
{
#ifdef ML
\tif(const char * dataHome = std::getenv("XDG_DATA_HOME"))
\t\treturn bfs::path(dataHome) / "vcmi";
\treturn bfs::path(".") / "data";''')
print('Added server BattleResult metadata and standard XDG worker data isolation')

replace('vcmi/AI/MMAI/schema/v15/types.h',
        '    std::array<std::map<int, int>, 2> casualties;',
        '    std::array<std::map<int, int>, 2> casualties;\n'
        '    std::array<std::map<int, int>, 2> initialArmies;')
replace('vcmi/AI/MMAI/BAI/v15/state_v15.h',
        '\tGlobalStats startStats;',
        '\tstd::array<std::map<int, int>, 2> initialArmies;\n\tGlobalStats startStats;')
replace('vcmi/AI/MMAI/BAI/v15/state_v15.cpp',
        ''': version_(version), battle(battle), startStats(CalcGlobalStats(battle)), lastStats(startStats), colorname(colorname), side(battle.battleGetMySide())
{
}''',
        ''': version_(version), battle(battle), startStats(CalcGlobalStats(battle)), lastStats(startStats), colorname(colorname), side(battle.battleGetMySide())
{
\tfor(const auto * stack : battle.battleGetAllStacks(false))
\t\tif(stack->unitSlot().getNum() >= 0 && stack->unitSlot().getNum() < 7 && !stack->summoned)
\t\t\tinitialArmies.at(static_cast<int>(stack->unitSide()))[stack->creatureId().getNum()] += stack->getCount();
}''')
replace('vcmi/AI/MMAI/BAI/v15/state_v15.cpp',
        '\tsupdata->terminalOutcome.resultType = static_cast<int>(br.result);',
        '\tsupdata->terminalOutcome.initialArmies = initialArmies;\n'
        '\tsupdata->terminalOutcome.resultType = static_cast<int>(br.result);')
replace('vcmi_gym/connectors/v15/threadconnector.cpp',
        '                                py::arg("casualties") = p_casualties);',
        '                                py::arg("casualties") = p_casualties,\n'
        '                                py::arg("initial_armies") = py::cast(outcome.initialArmies));')

replace('vcmi/AI/MMAI/BAI/v15/state_v15.cpp',
        'stack->unitSlot().getNum() < 7 && !stack->summoned',
        'stack->unitSlot().getNum() < GameConstants::ARMY_SIZE && !stack->summoned')
