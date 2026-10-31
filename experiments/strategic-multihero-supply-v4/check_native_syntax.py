"""Read flags and syntax-check isolated Director/Client overlays; no shared writes."""
import hashlib,json,shlex,shutil,subprocess,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
SOURCE=Path('/root/heroes3-ai-lab/src/vcmi-adv')
BUILD=Path('/root/heroes3-ai-lab/src/vcmi-adv-build')

def main():
    checks=[]
    with tempfile.TemporaryDirectory(prefix='supply-v4-syntax-') as temp:
        overlay=Path(temp)
        for p in SOURCE.iterdir():
            if p.name not in ['AI','client']:(overlay/p.name).symlink_to(p,target_is_directory=p.is_dir())
        folder=overlay/'AI/DirectorAI';folder.mkdir(parents=True)
        for p in (HERE/'candidate/AI/DirectorAI').iterdir():shutil.copyfile(p,folder/p.name)
        client=overlay/'client';client.mkdir()
        for p in (SOURCE/'client').iterdir():(client/p.name).symlink_to(p,target_is_directory=p.is_dir())
        for name in ['Client.h','Client.cpp']:
            target=client/name;target.unlink();shutil.copyfile(HERE/'candidate/client'/name,target)
        for target,relative in [('AI/DirectorAI/CMakeFiles/DirectorAI.dir/CDirectorAI.cpp.o','AI/DirectorAI/CDirectorAI.cpp'),
                                ('client/CMakeFiles/vcmiclientcommon.dir/Client.cpp.o','client/Client.cpp')]:
            command=subprocess.check_output(['ninja','-C',str(BUILD),'-t','commands',target],text=True).splitlines()[-1]
            args=shlex.split(command);clean=[];i=0
            while i<len(args):
                a=args[i]
                if a in ['-o','-MF','-MT','-include']:i+=2;continue
                if a in ['-c','-MD','-O3','-Winvalid-pch'] or a.endswith('/'+Path(relative).name):i+=1;continue
                clean.append(a);i+=1
            proc=subprocess.run(clean+['-O0','-fsyntax-only',str(overlay/relative)],capture_output=True,text=True)
            (HERE/(Path(relative).stem+'-syntax.log')).write_text(proc.stdout+proc.stderr)
            checks.append({'translation_unit':relative,'exit_code':proc.returncode,'passed':proc.returncode==0,
                           'flags_sha256':hashlib.sha256(command.encode()).hexdigest()})
            if proc.returncode:print(proc.stderr[-14000:])
    manifest=json.loads((HERE/'CANDIDATE_MANIFEST.json').read_text())
    result={'passed':all(c['passed'] for c in checks),'checks':checks,'native_built':False,'native_games':0,
            'scope':'two translation units syntax only, temporary overlay; no objects/link/game',
            'candidate_files':manifest['files'],'source_token':manifest['source_token']}
    (HERE/'NATIVE_SYNTAX.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':result['passed'],'native_built':False}))
    raise SystemExit(0 if result['passed'] else 1)

if __name__=='__main__':main()
