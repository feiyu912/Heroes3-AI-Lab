"""Read engine compiler flags; syntax-check an isolated overlay. No object/shared build writes."""
import hashlib
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile

HERE=Path(__file__).resolve().parent
SOURCE=Path('/root/heroes3-ai-lab/src/vcmi-adv')
BUILD=Path('/root/heroes3-ai-lab/src/vcmi-adv-build')

def main():
    command=subprocess.check_output(['ninja','-C',str(BUILD),'-t','commands',
                                    'AI/DirectorAI/CMakeFiles/DirectorAI.dir/CDirectorAI.cpp.o'],text=True).splitlines()[-1]
    args=shlex.split(command)
    clean=[];i=0
    while i<len(args):
        a=args[i]
        if a in ['-o','-MF','-MT','-include']:
            i+=2;continue
        if a in ['-c','-MD','-O3','-Winvalid-pch'] or a.endswith('/CDirectorAI.cpp'):
            i+=1;continue
        clean.append(a);i+=1
    with tempfile.TemporaryDirectory(prefix='supply-v1-syntax-') as temp:
        overlay=Path(temp)
        for p in SOURCE.iterdir():
            if p.name!='AI': (overlay/p.name).symlink_to(p,target_is_directory=p.is_dir())
        target=overlay/'AI'/'DirectorAI';target.mkdir(parents=True)
        for p in (HERE/'candidate/AI/DirectorAI').iterdir():shutil.copyfile(p,target/p.name)
        proc=subprocess.run(clean+['-O0','-fsyntax-only',str(target/'CDirectorAI.cpp')],capture_output=True,text=True)
    (HERE/'NATIVE_SYNTAX.log').write_text(proc.stdout+proc.stderr,encoding='utf-8')
    manifest=json.loads((HERE/'MANIFEST.json').read_text())
    result={'passed':proc.returncode==0,'exit_code':proc.returncode,'native_built':False,'native_games':0,
            'scope':'one isolated Director translation unit syntax only; no link/runtime certification',
            'candidate_files':manifest['candidate_files'],
            'compiler_flags_sha256':hashlib.sha256(command.encode()).hexdigest()}
    (HERE/'NATIVE_SYNTAX.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'passed':result['passed'],'exit_code':proc.returncode,'native_built':False}))
    if proc.returncode: print(proc.stderr[-12000:])
    raise SystemExit(proc.returncode)

if __name__=='__main__': main()
