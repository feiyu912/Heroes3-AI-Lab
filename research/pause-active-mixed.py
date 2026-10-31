"""Stop only the verified current mixed-run process tree at user request."""
import json
import os
from pathlib import Path
import signal
import time

ROOT=Path('/mnt/g/Heroes3-AI-Lab')
OUT=ROOT/'experiments/expert-mixed-b64-run-v1'
TARGET=261190


def processes():
    result={}
    for folder in Path('/proc').iterdir():
        if not folder.name.isdigit():continue
        try:
            stat=(folder/'stat').read_text().rsplit(')',1)[1].split()
            result[int(folder.name)]=dict(parent=int(stat[1]),state=stat[0],start=stat[19],
                command=(folder/'cmdline').read_bytes().decode(errors='replace'))
        except (OSError,ValueError,IndexError):pass
    return result


def main():
    before=processes()
    assert 'experiments/run-next-mixed.py' in before[TARGET]['command']
    controllers=[pid for pid,row in before.items() if row['parent']==TARGET and 'run_experiment.py' in row['command']]
    assert len(controllers)==1
    trainers=[pid for pid,row in before.items() if row['parent']==controllers[0] and 'train_mixed_heads.py' in row['command']]
    assert len(trainers)==1
    for pid in [TARGET,*controllers,*trainers]:os.kill(pid,signal.SIGSTOP)
    snapshot=processes();owned={TARGET}
    while True:
        expanded=owned|{pid for pid,row in snapshot.items() if row['parent'] in owned}
        if expanded==owned:break
        owned=expanded
    for pid in [TARGET,*controllers]:
        os.kill(pid,signal.SIGTERM);os.kill(pid,signal.SIGCONT)
    for pid in trainers:
        os.kill(pid,signal.SIGINT);os.kill(pid,signal.SIGCONT)
    deadline=time.monotonic()+8
    while time.monotonic()<deadline:
        current=processes()
        alive=[pid for pid in owned if pid in current and current[pid]['state']!='Z'
            and current[pid]['start']==snapshot[pid]['start']]
        if not alive:break
        time.sleep(.2)
    current=processes()
    for pid in owned:
        if pid in current and current[pid]['state']!='Z' and current[pid]['start']==snapshot[pid]['start']:
            os.kill(pid,signal.SIGTERM)
    time.sleep(.3)
    current=processes()
    remaining=[pid for pid in owned if pid in current and current[pid]['state']!='Z'
        and current[pid]['start']==snapshot[pid]['start']]
    assert not remaining,remaining
    training_path=ROOT/'experiments/expert-mixed-ppo-v1/b64-anchor-plan/training.json'
    training=json.loads(training_path.read_text())
    report=dict(state='paused_by_user',all_owned_processes_stopped=True,stopped_tree_pids=sorted(owned),
        last_reported_update=training['latest_update'],saved_checkpoint=training['checkpoint'],
        saved_checkpoint_sha256=training['checkpoint_sha256'],
        new_mixed_optimizer_checkpoint_exists=training['latest_update']>=16,
        note='Mixed trainer saves every16 updates. Earlier reported updates have no saved weights/optimizer; restart this trial from B64 in a fresh output, preserving partial evidence.',
        goal_achieved=False,paused_unix=time.time())
    (OUT/'paused-state.json').write_text(json.dumps(report,indent=2)+'\n')
    (OUT/'control.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
