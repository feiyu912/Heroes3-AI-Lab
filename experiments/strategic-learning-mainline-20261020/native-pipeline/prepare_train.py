"""Generate the old train_update_v3 with source/runtime epoch bindings only."""
from pathlib import Path
import difflib,json
HERE=Path(__file__).resolve().parent;BASE=HERE.parent.parent/'strategic-typed-training-v1'
from prepare_entries import BOOT
def main():
    original=(BASE/'train_update_v3.py').read_text();text=original
    def change(a,b):
        nonlocal text
        assert text.count(a)==1,(a,text.count(a));text=text.replace(a,b,1)
    change('HERE=Path(__file__).resolve().parent;TYPED=HERE.parent/\'strategic-policy-v3\'',"HERE=BASE;TYPED=HERE.parent/'strategic-policy-v3'")
    a="""    names=['train_update_v3.py','model_io.py','load_admitted.py','episode_balanced_ppo.py','collect_episode_v5.py','onpolicy_broker_v2.py','admit_episode_v5.py','live_jsonl.py']
    sources=[HERE/n for n in names]+[TYPED/n for n in ['model.py','encoder.py','broker.py','audit_typed_execution.py']]
    native=HERE.parent/'strategic-typed-native-v1'
    sources += [native/n for n in ['audit_game_v5.py','raw_events_v4.py']]"""
    change(a,"    sources=source_inputs()+[Path(__file__).resolve(),LOCAL/'run_pipeline.py']")
    change("schema='typed-certified-single-env-ppo-training-v2'","schema=EPOCH")
    change("default='engineering_boundary'","default='curriculum_training'")
    a="""        coverage={(e['job']['map'],e['job']['owned_player'],e['job']['opponent']) for e in episodes}
        assert len(episodes)>=8 and len(coverage)==8,'Research curriculum needs both maps, roles and opponents'"""
    change(a,"        validate_cells(episodes)\n    else:raise ValueError('This new mainline epoch requires the complete eight-cell curriculum')")
    a="""            for name in ['collect_episode_v5.py','live_jsonl.py','onpolicy_broker_v2.py','model_io.py']:
                path=str(HERE/name)
                assert collection_plan['hashes'].get(path)==config['sources'][path],'Collector/source epoch differs'
            admission_source=str(HERE/'admit_episode_v5.py')"""
    b="""            for item in [LOCAL/'collect_episode_v5.py',LOCAL/'pipeline_common.py',BASE/'live_jsonl.py',BASE/'onpolicy_broker_v2.py',BASE/'model_io.py',AUDITOR/'audit_game_v6.py',AUDITOR/'director_registry_v1.py',NATIVE/'raw_events_v4.py']:
                path=str(item)
                assert collection_plan['hashes'].get(path)==config['sources'][path],'Collector/source epoch differs'
            assert collection_plan['pipeline_epoch']==EPOCH
            admission_source=str(LOCAL/'admit_episode_v5.py')"""
    change(a,b)
    change("'explicit_optimizer_reset':bool(a.initialize)","'training_epoch':EPOCH,'explicit_optimizer_reset':bool(a.initialize)")
    text=BOOT+text;(HERE/'train_update_v3.py').write_text(text)
    (HERE/'train_update_v3.py.diff').write_text(''.join(difflib.unified_diff(original.splitlines(True),text.splitlines(True),fromfile='frozen/train_update_v3.py',tofile='mainline/train_update_v3.py')))
    print(json.dumps({'prepared':'train_update_v3.py','native_runs':0,'optimizer_steps':0}))
if __name__=='__main__':main()
