"""Locate actual saved updates and carry checkpoint provenance across attempts."""
import json
from pathlib import Path
import shutil
import time
import zipfile


def available(data,initial):
    folders=set()
    checkpoint=data.get('checkpoint')
    if checkpoint and checkpoint!=initial:folders.add(Path(checkpoint).parent)
    if data.get('source_snapshot'):folders.add(Path(data['source_snapshot']).parent)
    history=data.get('checkpoint_history',{})
    folders.update(Path(path).parent for path in history.values())
    result={}
    for folder in sorted(folders):
        assert folder.is_relative_to('/root/heroes3-ai-lab/models')
        for path in folder.glob('update-*.pt'):
            number=int(path.stem.split('-')[-1])
            result[str(number)]=str(path)
    result.update({n:path for n,path in history.items() if Path(path).exists()})
    complete={}
    for number,path in result.items():
        try:
            with zipfile.ZipFile(path) as archive:
                assert archive.testzip() is None,'Checkpoint CRC mismatch'
            complete[number]=path
        except (OSError,zipfile.BadZipFile,AssertionError) as error:
            print('Excluded incomplete checkpoint; file preserved:',path,repr(error),flush=True)
    return complete


def resume_command(command,output,initial,target_updates):
    """Return command, prior checkpoints. Completed experiments never rerun."""
    output=Path(output)
    if not output.exists():return command,{},None
    data=json.loads(output.read_text())
    assert data.get('experiment_initial_checkpoint',data['config'].get('experiment_initial_checkpoint',data['config']['checkpoint']))==initial
    history=available(data,initial)
    if data.get('completed') and data.get('all_workers_exit_zero') and data['checkpoint'] in history.values():
        return command,history,data
    archived=output.with_name(output.stem+'-attempt-'+str(time.time_ns())+'.json')
    shutil.copyfile(output,archived)
    if not history:return command,history,None
    # The writer is atomic; candidate files end in .pt only after successful save.
    last=max(map(int,history));assert 0<last<target_updates
    command=list(command)
    command[command.index('--checkpoint')+1]=history[str(last)]
    command[command.index('--updates')+1]=str(target_updates-last)
    command.append('--resume')
    command+=['--experiment-initial-checkpoint',initial]
    print('Resuming saved update',last,'of',target_updates,'from',history[str(last)],flush=True)
    return command,history,None


def annotate(output,initial,history):
    output=Path(output);data=json.loads(output.read_text())
    merged=dict(history);merged.update(available(data,initial))
    data.update(experiment_initial_checkpoint=initial,checkpoint_history=merged)
    output.write_text(json.dumps(data,indent=2))
    return data


def snapshot(data,iteration):
    key=str(iteration)
    candidate=data.get('checkpoint_history',{}).get(key,str(Path(data['checkpoint']).parent/f'update-{iteration}.pt'))
    assert Path(candidate).is_file(),f'Missing saved snapshot {iteration}: {candidate}'
    return candidate
