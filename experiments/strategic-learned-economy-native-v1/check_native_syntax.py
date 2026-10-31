"""Syntax-only compile three isolated translation units; no shared source/object writes."""
import hashlib,json,shlex,shutil,subprocess,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
SOURCE=Path('/root/heroes3-ai-lab/src/vcmi-adv');BUILD=Path('/root/heroes3-ai-lab/src/vcmi-adv-build')
def overlay_directory(source,dest,relative,files):
    dest.mkdir()
    for path in source.iterdir():
        rel=str(relative/path.name)
        if rel in files:shutil.copyfile(HERE/'candidate'/rel,dest/path.name)
        elif any(name.startswith(rel+'/') for name in files):overlay_directory(path,dest/path.name,Path(rel),files)
        else:(dest/path.name).symlink_to(path,target_is_directory=path.is_dir())
def main():
    manifest=json.loads((HERE/'CANDIDATE_MANIFEST.json').read_text());files=manifest['files'];results=[];logs=[]
    commands=subprocess.check_output(['ninja','-C',str(BUILD),'-t','commands','vcmiclient','vcmiserver'],text=True).splitlines()
    with tempfile.TemporaryDirectory(prefix='learned-build-syntax-') as temp:
        overlay=Path(temp)/'source';overlay_directory(SOURCE,overlay,Path(),files)
        for relative in files:
            target=overlay/relative
            if not target.exists():shutil.copyfile(HERE/'candidate'/relative,target)
        for relative in ['AI/DirectorAI/CDirectorAI.cpp','server/CGameHandler.cpp','client/NetPacksClient.cpp']:
            matches=[c for c in commands if shlex.split(c)[-1]==str(SOURCE/relative)]
            assert len(matches)==1,(relative,len(matches))
            command=matches[0];args=shlex.split(command);clean=[];i=0
            while i<len(args):
                arg=args[i]
                if arg in ['-o','-MF','-MT','-include']:i+=2;continue
                if arg in ['-c','-MD','-O3','-O2','-g','-Winvalid-pch'] or arg==str(SOURCE/relative):i+=1;continue
                clean.append(arg);i+=1
            proc=subprocess.run(clean+['-O0','-fsyntax-only',str(overlay/relative)],capture_output=True,text=True)
            logs.append(relative+'\n'+proc.stdout+proc.stderr)
            results.append(dict(source=relative,passed=proc.returncode==0,exit_code=proc.returncode,compiler_command_sha256=hashlib.sha256(command.encode()).hexdigest()))
    result=dict(passed=all(r['passed'] for r in results),translation_units=results,native_builds=0,native_games=0,optimizer_steps=0,
        scope='Isolated syntax only; no linker/native runtime qualification',candidate_manifest_sha256=hashlib.sha256((HERE/'CANDIDATE_MANIFEST.json').read_bytes()).hexdigest())
    (HERE/'NATIVE_SYNTAX.log').write_text('\n'.join(logs));(HERE/'NATIVE_SYNTAX.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2));raise SystemExit(0 if result['passed'] else 1)
if __name__=='__main__':main()
