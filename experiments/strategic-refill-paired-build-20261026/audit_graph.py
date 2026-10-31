"""Audit the actual configured graph against the saved original build flags."""
import hashlib,json,re,shlex,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    c=json.loads((HERE/'build-contract-v1.json').read_text());scratch=Path(c['scratch_root']);build=scratch/'build';prefix=Path(c['toolchain_root']);sysroot=prefix/'sysroot'
    old=json.loads((HERE.parent/'ubuntu-native-takeover-20261025/toolchain-plan/TOOLCHAIN_SOURCE_PLAN.json').read_text());cmds=json.loads((build/'compile_commands.json').read_text())
    director=[x for x in cmds if x['file'].endswith('/AI/DirectorAI/CDirectorAI.cpp')];assert len(director)==1
    command=director[0]['command'];flags=command[command.index('-Wall '):command.index(' -o ')]
    expected=next(x.strip().split('FLAGS = ',1)[1] for x in old['old_compiler']['director_build_lines'] if x.strip().startswith('FLAGS = ')).replace('/root/heroes3-ai-lab/src/vcmi-adv-build',str(build))
    assert flags==expected,(flags,expected)
    actual={}
    for line in (build/'CMakeCache.txt').read_text().splitlines():
        if line.startswith(('//','#')) or '=' not in line or ':' not in line.split('=',1)[0]:continue
        namekind,val=line.split('=',1);name,kind=namekind.split(':',1);actual[name]=val
    options={k:{'expected':v['value'],'actual':actual.get(k)} for k,v in old['old_cmake_cache'].items() if k.startswith('ENABLE_')}
    assert all(v['expected']==v['actual'] for v in options.values()),options
    includes=[]
    for row in cmds:
        assert str(scratch/'source') in row['file'] or str(build) in row['file']
        words=shlex.split(row['command']);assert words[0]==str(sysroot/'usr/bin/g++-11')
        assert '--sysroot='+str(sysroot) in words
        for i,w in enumerate(words):
            value=w[2:] if w.startswith('-I') and w!='-I' else words[i+1] if w in ('-isystem','-I') else None
            if value:
                assert any(value.startswith(str(p)+'/') for p in (scratch,prefix,Path(c['profile_root']))),('External include',value)
                includes.append(value)
    report={'passed':True,'scope':'configured flags/options/include graph; not a successful full compile or runtime test','contract_sha256':h(HERE/'build-contract-v1.json'),'configured_sha256':h(scratch/'CONFIGURED.json'),'build_ninja_sha256':h(build/'build.ninja'),'compile_commands_sha256':h(build/'compile_commands.json'),'compile_commands':len(cmds),'director_flags_exact_after_build_path_relocation':True,'unchanged_options':options,'include_paths':sorted(set(includes)),'new_native_games':0,'optimizer_steps':0}
    target=HERE/(sys.argv[1] if len(sys.argv)>1 else 'GRAPH_AUDIT.json');assert not target.exists();target.write_text(json.dumps(report,indent=2)+'\n');print('graph audit passed',len(cmds),'commands')
if __name__=='__main__':main()
