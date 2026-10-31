#!/usr/bin/env python3
"""Make a NEW local map artifact. Does not install it in the native map pool."""
import argparse,copy,hashlib,json,zipfile
from pathlib import Path

def make(source,out):
    assert not out.exists()
    raw=source.read_bytes()
    with zipfile.ZipFile(source) as z:
        entries={name:z.read(name) for name in z.namelist()}
    header=json.loads(entries['header.json']);objects=json.loads(entries['objects.json'])
    assert header['mapLevels']['surface']['width']==36 and header['mapLevels']['surface']['height']==36
    donor=copy.deepcopy(objects['hero_0']);receiver=copy.deepcopy(donor)
    donor.update(x=10,y=12);receiver.update(x=12,y=12)
    donor['options'].update(name='ENGINEERING courier',type='core:christian',army=[{'type':'core:pikeman','amount':10},{'type':'core:archer','amount':3}])
    receiver['options'].update(name='ENGINEERING receiver',type='core:tyris',army=[{'type':'core:pikeman','amount':5}])
    # No pickups, monsters, or scripted grants on this dedicated probe map.
    objects={name:copy.deepcopy(objects[name]) for name in ('town_0','town_1','hero_1')}
    objects['hero_0']=donor;objects['hero_2']=receiver
    header['players']['red']['heroes']={'hero_0':{'type':'core:christian'},'hero_2':{'type':'core:tyris'}}
    header['name']='multihero-native-mechanism-probe-v1'
    header['description']='ENGINEERING ONLY: real owned-hero meeting/query/army exchange. No training or ability score.'
    header['mods']=None
    entries['header.json']=json.dumps(header,sort_keys=True,indent=2).encode()
    entries['objects.json']=json.dumps(objects,sort_keys=True,indent=2).encode()
    out.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        for name,data in sorted(entries.items()):
            info=zipfile.ZipInfo(name,date_time=(2026,10,18,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(info,data)
    manifest={'source':str(source),'source_sha256':hashlib.sha256(raw).hexdigest(),'map':str(out),
        'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'installed':False,'loaded_by_native':False,
        'red_heroes':2,'intended_stack_totals':{'core:pikeman':15,'core:archer':3},
        'positions_are_object_coordinates':True,'native_pathfinding_still_required':True}
    out.with_suffix('.json').write_text(json.dumps(manifest,indent=2))
    return manifest

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();print(json.dumps(make(a.source,a.out),indent=2))
