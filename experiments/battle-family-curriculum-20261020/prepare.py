"""Isolated derivative of the completed 4-update battle trainer; CPU preparation only."""
from pathlib import Path
import difflib
HERE=Path(__file__).resolve().parent;OLD=HERE.with_name('battle-training-resume-20261020-v2')
def once(t,a,b):assert t.count(a)==1,(a,t.count(a));return t.replace(a,b,1)
def save(name,old,new):
    (HERE/name).write_text(new);(HERE/(name+'.diff')).write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='frozen-v2/'+name,tofile='family-curriculum/'+name)))
def main():
    for name in ['support.py','evaluate_bounded.py']:(HERE/name).write_text((OLD/name).read_text())
    old=(OLD/'support.py').read_text();t=old.replace("(8,4,32,'last')","(12,4,32,'last')").replace('2026102008','2026102012').replace('a.rotate_every==16','a.rotate_every==2').replace('battle-resume-bounded-last-v1','battle-family-balanced-last-v1');save('support.py',old,t)
    old=(OLD/'train_last_graph.py').read_text();t=once(old,'    import support','    import support\n    import curriculum')
    t=once(t,'started=time.monotonic();records=[];episodes=wins=cuts=0;vector=None','started=time.monotonic();records=[];episodes=wins=cuts=0;vector=None\n    phase_close_events=[];live_steps=[]')
    begin=t.index('                if vector:vector.close();vector=None');end=t.index('                vector=(OpponentVector',begin)
    t=t[:begin]+'''                if vector:
                    phase_close_events.append(curriculum.close_evidence(phase,live_steps,configs,'phase_switch'))
                    vector.close();vector=None
                phase=(previous+iteration)//args.rotate_every
                curriculum.resource_gate()
                configs=curriculum.configs(args.scenario_file,args.seed,phase,run)
                live_steps=[0]*args.workers
'''+t[end:]
    needle='                current=next_obs';t=once(t,needle,'''                for worker,s in enumerate(transitions):
                    live_steps[worker]+=1
                    if s['terminated'] or s['truncated']:live_steps[worker]=0
'''+needle)
    t=once(t,'native_environment_restorable=False)','native_environment_restorable=False,phase_close_events=phase_close_events)')
    t=once(t,'records=records,wall_seconds=time.monotonic()-started,policy=\'recovered\',',"records=records,phase_close_events=phase_close_events,wall_seconds=time.monotonic()-started,policy='recovered',")
    t=once(t,'\n        vector.close();vector=None\n        report.update',"\n        phase_close_events.append(curriculum.close_evidence(phase,live_steps,configs,'final_budget_stop'))\n        vector.close();vector=None\n        report.update")
    # Successful final report includes final shutdown event, not just events at last save.
    t=once(t,'report.update(completed=True,all_workers_exit_zero=True)','report.update(completed=True,all_workers_exit_zero=True,phase_close_events=phase_close_events)')
    t=once(t,'source_snapshot=source_snapshot,partial_live_state_not_resumable=True,config=vars(args)))','source_snapshot=source_snapshot,partial_live_state_not_resumable=True,config=vars(args),phase_close_events=phase_close_events))')
    save('train_last_graph.py',old,t)
    old=(OLD/'run.py').read_text();t=old.replace('battle-resume-bounded-last-v1','battle-family-balanced-last-v1').replace('2026102008','2026102012').replace('2026102500','2026102600')
    t=t.replace("'--workers','8','--updates','4'","'--workers','12','--updates','4'").replace("'--rotate-every','16'","'--rotate-every','2'").replace('workers=8,updates=4,owned_transitions_budget=1024','workers=12,updates=4,owned_transitions_budget=1536')
    t=once(t,'from pathlib import Path','from pathlib import Path\nimport curriculum')
    t=once(t,"evaluation=a.evaluate,opponents=['BattleAI','MMAI_MODEL']","evaluation=a.evaluate,registered_curriculum=curriculum.registered(SCENARIOS),opponents=['BattleAI','MMAI_MODEL']")
    save('run.py',old,t)
if __name__=='__main__':main()
