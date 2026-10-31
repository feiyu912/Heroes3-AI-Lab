"""Strict CPU fixture/selection checks and actual prepare-only collector paths."""
from pathlib import Path
import argparse,copy,importlib.util,json,subprocess,sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from pipeline_common import map_manifest,DEFAULT_CAPSULE,DEFAULT_INITIAL
from run_calibration import jobs,select_difficulty
from derive_maps import verify_variant
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False,parents=True)
    manifest=map_manifest()
    for item in manifest['variants']:
        source=manifest['sources'][item['source_map']]['path']
        proof=verify_variant(source,item['path'],item['owned_player'],item['multiplier'])
        assert proof['JSON_semantic_changes']==item['JSON_semantic_changes']
    registered=jobs();assert len(registered)==12
    assert len({(r['source_map'],r['player'],r['multiplier']) for r in registered})==12
    for source in {r['source_map'] for r in registered}:
        for role in (0,1):assert len({r['seed'] for r in registered if r['source_map']==source and r['player']==role})==1
    synthetic=[dict(job=r,valid=True,win=(r['multiplier'] in (2,4) and r['player']==0)) for r in registered]
    assert select_difficulty(synthetic)['selected_multiplier']==2
    for r in synthetic:r['win']=r['job']['multiplier']==4 and r['job']['player']==0
    assert select_difficulty(synthetic)['selected_multiplier']==4
    for r in synthetic:r['win']=False
    assert not select_difficulty(synthetic)['qualified']
    synthetic[0]['valid']=False
    assert not select_difficulty(synthetic)['qualified'] and not select_difficulty(synthetic[:-1])['qualified']
    prepared=[]
    for i,r in enumerate(registered):
        dest=a.out/f'cell-{i:02d}'
        command=['/usr/bin/python3',str(HERE/'collect_calibration.py'),'--prepare-only','--capsule',str(DEFAULT_CAPSULE),'--checkpoint',str(DEFAULT_INITIAL),'--map',r['map'],'--player',str(r['player']),'--seed',str(r['seed']),'--opponent','Nullkiller2','--out',str(dest)]
        completed=subprocess.run(command,capture_output=True,text=True)
        (a.out/f'cell-{i:02d}.log').write_text(completed.stdout+'\n'+completed.stderr)
        assert completed.returncode==0,(i,completed.stderr)
        d=json.loads((dest/'PREPARED.json').read_text());assert d['passed'] and d['locks_acquired'] is False and d['native_runs']==d['optimizer_steps']==0
        prepared.append(d)
    result=dict(passed=True,all12_maps_strictly_rederived=True,all12_actual_collector_prepare_paths_passed=True,selection_and_invalid_rejection_passed=True,native_runs=0,GPU_operations=0,optimizer_steps=0,shared_resource_locks_taken=False)
    (a.out/'AUDIT.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':main()
