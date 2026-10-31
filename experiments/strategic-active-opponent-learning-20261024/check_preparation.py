"""No native game or learning: verify treatment, private maps, seeds and codec."""
import argparse,ast,copy,hashlib,json,subprocess,sys
from pathlib import Path
from types import SimpleNamespace
from pipeline_common import HERE,BASE,LAB,MAPS,DEFAULT_INITIAL,INITIAL_SHA,DEFAULT_CAPSULE,source_inputs,capsule_inputs,sha,training_variant,validate_cells,audit_metadata
from run import jobs
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    assert sha(DEFAULT_INITIAL)==INITIAL_SHA
    for folder in (HERE,BASE):
        for path in folder.glob('*.py'):ast.parse(path.read_text(),filename=str(path))
    from collect_episode_v5 import run as prepare
    entries=[];groups={};seeds={}
    for arm in ('control','curriculum'):
        episodes=[]
        for i,j in enumerate(jobs()):
            out=a.out/arm/f'cell-{i:02d}'
            args=SimpleNamespace(capsule=DEFAULT_CAPSULE,out=out,checkpoint=DEFAULT_INITIAL,load_save=None,prepare_only=True,seconds=120,arm=arm,**j)
            assert prepare(args)==0
            plan=json.loads((out/'PLAN.json').read_text());entry=training_variant(j['map'],j['player'],j['opponent'],arm)
            assert plan['map_variant']==entry and plan['multiplier']==(4 if arm=='curriculum' and j['opponent']=='Nullkiller2' else 1)
            assert sha(out/('data/vcmi/Maps/adv/'+j['map']+'.vmap'))==entry['sha256']
            assert all(plan[k]==v for k,v in audit_metadata().items())
            material=json.dumps(dict(seed=j['seed'],map=j['map'],player=j['player'],opponent=j['opponent'],logical_update=0),sort_keys=True).encode()
            expected=int.from_bytes(hashlib.sha256(material).digest()[:8],'little')%(2**63-1);assert plan['sampling_seed']==expected
            if arm=='curriculum':assert expected==seeds[i]
            else:seeds[i]=expected
            episode=dict(episode_id=arm+str(i),checkpoint_sha256=INITIAL_SHA,job=dict(map=j['map'],owned_player=j['player'],opponent=j['opponent'],seed=j['seed'],logical_update=0,arm=arm,multiplier=entry['multiplier']))
            episodes.append(episode);entries.append(dict(arm=arm,index=i,sampling_seed=expected,map_sha256=entry['sha256'],multiplier=entry['multiplier']))
        validate_cells(episodes);groups[arm]=episodes
    rejected=[]
    for label,fn in [('wrong_map',lambda:training_variant('DEV',0,'Nullkiller2','curriculum')),('wrong_role',lambda:training_variant(MAPS[0],2,'Nullkiller2','curriculum')),('wrong_arm',lambda:training_variant(MAPS[0],0,'Nullkiller2','other'))]:
        try:fn()
        except ValueError:rejected.append(label)
        else:raise AssertionError('Invalid treatment accepted '+label)
    for label in ('missing_cell','duplicate','mixed_arm','wrong_multiplier','wrong_seed'):
        bad=copy.deepcopy(groups['control'])
        if label=='missing_cell':bad.pop()
        elif label=='duplicate':bad[-1]=bad[0]
        elif label=='mixed_arm':bad[-1]['job']['arm']='curriculum'
        elif label=='wrong_multiplier':bad[-1]['job']['multiplier']=4
        elif label=='wrong_seed':bad[-1]['job']['seed']+=1
        try:validate_cells(bad)
        except ValueError:rejected.append(label)
        else:raise AssertionError('Invalid batch accepted '+label)
    command=[str(LAB/'venv/bin/python'),str(BASE/'check_actual_cpu.py'),'--out',str(a.out/'codec')]
    result=subprocess.run(command,capture_output=True,text=True);(a.out/'codec.log').write_text(result.stdout+'\n'+result.stderr);assert result.returncode==0
    # The cached parser was already compared against the complete uncached
    # report on the longest calibration game; replay all unchanged gates here.
    raw=LAB/'evaluations/strategic-active-calibration-v2-native-01/cell-10/native'
    result=subprocess.run([str(LAB/'venv/bin/python'),str(HERE/'audit_game_v6.py'),str(raw),str(a.out/'cached-raw')],capture_output=True,text=True)
    (a.out/'cached.log').write_text(result.stdout+'\n'+result.stderr);assert result.returncode==0
    fresh=json.loads((a.out/'cached-raw/AUDIT.json').read_text());old=json.loads((raw.parent/'raw-audit/AUDIT.json').read_text())
    for key in audit_metadata():fresh.pop(key,None);old.pop(key,None)
    for key in ('TRAIN_only','curriculum_calibration_only'):fresh.pop(key,None);old.pop(key,None)
    assert fresh==old,'Cache/new wrapper must preserve every native gate/report outside declared epoch metadata'
    report=dict(passed=True,prepared_cells=16,canonical_sampling_seeds_equal_across_treatments=True,entries=entries,rejected=rejected,CPU_codec_passed=True,cached_longest_complete_audit_equal=True,native_runs=0,GPU_operations=0,optimizer_steps=0)
    (a.out/'AUDIT.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='entries'}))
if __name__=='__main__':main()
