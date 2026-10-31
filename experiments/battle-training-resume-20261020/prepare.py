"""Derive an isolated bounded trainer; no game, CUDA or frozen file writes."""
import difflib
from pathlib import Path
HERE=Path(__file__).resolve().parent;R=HERE.parent.parent/'research'
def once(text,a,b):
    assert text.count(a)==1,(a,text.count(a));return text.replace(a,b,1)
def main():
    original=(R/'train-graph-finetune.py').read_text();t=original
    t=once(t,'    import decision_model','    import decision_model\n    import support')
    t=once(t,"    p.add_argument('--checkpoint',required=True);p.add_argument('--output',required=True)","    p.add_argument('--checkpoint',required=True);p.add_argument('--output',required=True)\n    p.add_argument('--models-dir',required=True);p.add_argument('--freeze',required=True)")
    t=once(t,'    args=p.parse_args()',"    args=p.parse_args()\n    support.validate_args(args)\n    frozen=support.verify_freeze(args.freeze)")
    t=once(t,'torch.set_num_threads(2);torch.manual_seed(args.seed)','torch.set_num_threads(2);torch.manual_seed(args.seed)\n    __import__(\'random\').seed(args.seed);np.random.seed(args.seed)')
    t=once(t,'    fixed_opponent=configure_training(args,graph.base,model)',"    fixed_opponent=None  # Only actual native BattleAI/original public CPU ONNX opponents.")
    t=once(t,'    previous=steps=0',"    counter=support.install_step_counter(optimizer)\n    initial_parameters=support.snapshot(model)\n    previous=steps=0")
    t=once(t,"folder=Path('/root/heroes3-ai-lab/models/graph-finetune')/run","folder=Path(args.models_dir)/run")
    t=once(t,"    source_snapshot=capture_source(folder,'train-graph-finetune.py')","    source_snapshot=capture_source(folder,'train-graph-finetune.py')\n    support.capture_local(folder,frozen)")
    t=once(t,'            tick=time.monotonic();samples=[];',"            support.verify_freeze(args.freeze)\n            before_parameters=support.snapshot(model)\n            step_before=counter['steps']\n            tick=time.monotonic();samples=[];")
    t=once(t,"            stamp=time.monotonic()\n            metrics=update", "            support.save_rollout(folder,previous+iteration+1,dict(samples=samples,actions=actions,old_logp=old_logp,values=values,next_values=next_values,rewards=rewards,terminated=terminated,truncated=truncated,configs=configs))\n            stamp=time.monotonic()\n            metrics=update")
    t=once(t,"            timings['update']=time.monotonic()-stamp","            timings['update']=time.monotonic()-stamp\n            assert counter['steps']>step_before,'No actual Adam step'\n            parameter_delta=support.delta(model,before_parameters)\n            support.verify_freeze(args.freeze)")
    t=once(t,"            records.append(record)","            record.update(actual_Adam_steps=counter['steps']-step_before,actual_Adam_steps_total=counter['steps'],parameter_delta=parameter_delta,delta_from_B64=support.delta(model,initial_parameters))\n            records.append(record)")
    t=once(t,'            if (iteration+1)%16==0 or iteration+1==args.updates:',"            if True:  # Save every completed update, including short finite pilots.")
    t=once(t,"optimizer_state_dict=optimizer.state_dict(),torch_rng_state=torch.get_rng_state(),cuda_rng_states=torch.cuda.get_rng_state_all())","optimizer_state_dict=optimizer.state_dict(),torch_rng_state=torch.get_rng_state(),cuda_rng_states=torch.cuda.get_rng_state_all(),\n                    python_rng_state=__import__('random').getstate(),numpy_rng_state=support.numpy_rng(),\n                    actual_Adam_steps=counter['steps'],complete_update_boundary=True,frozen_inputs=frozen,\n                    native_environment_restorable=False)\n                record['checkpoint_readback']=support.check_readback(latest,model,optimizer,graph,counter['steps'])\n                record['checkpoint_sha256']=support.sha(latest)")
    t=once(t,'    finally:\n        if vector:vector.abort()',"    except BaseException as error:\n        atomic_json(args.output,dict(completed=False,error=repr(error),actual_Adam_steps=counter['steps'],\n            CUDA_training=counter['steps']>0,checkpoint=latest,checkpoint_exists=Path(latest).is_file(),records=records,\n            source_snapshot=source_snapshot,partial_live_state_not_resumable=True,config=vars(args)))\n        raise\n    finally:\n        if vector:vector.abort()")
    (HERE/'train_last_graph.py').write_text(t)
    (HERE/'trainer.diff').write_text(''.join(difflib.unified_diff(original.splitlines(True),t.splitlines(True),fromfile='frozen/train-graph-finetune.py',tofile='isolated/train_last_graph.py')))
    original=(R/'evaluate-battles.py').read_text();t=original
    t=once(t,"parser.add_argument('--seeds', type=int, default=5)","parser.add_argument('--seeds', type=int, default=5)\nparser.add_argument('--seed-base',type=int,default=2026102500)")
    t=once(t,'2026101400 + scenario * 100 + seed','args.seed_base + scenario * 100 + seed')
    t=once(t,'frozen=freeze(args)',"frozen=freeze(args)\nfrozen[str(Path(__file__).resolve())]=__import__('hashlib').sha256(Path(__file__).read_bytes()).hexdigest()")
    (HERE/'evaluate_bounded.py').write_text(t)
    (HERE/'evaluation.diff').write_text(''.join(difflib.unified_diff(original.splitlines(True),t.splitlines(True),fromfile='frozen/evaluate-battles.py',tofile='isolated/evaluate_bounded.py')))
if __name__=='__main__':main()

