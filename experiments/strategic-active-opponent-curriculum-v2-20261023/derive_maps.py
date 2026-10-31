"""TRAIN-only VMAP hero-count variants. No native process or shared map writes."""
import argparse,copy,hashlib,json,struct,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
LAB=Path('/root/heroes3-ai-lab')
SOURCES={'takeover-v2-train-01-mines':'0ccc185c66b1379e8a9522ca81dc6e1567f540aefb104d0b1602e23ad538d036',
    'takeover-v2-train-02-development':'5f637c73fe5a7361385f9c32b40c11685dddc4a1014ba7c991fa721582d7b7bd'}
ROLES={0:'red',1:'blue'}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def digest(raw):return hashlib.sha256(raw).hexdigest()
def encode(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def differences(before,after,path=''):
    if type(before) is not type(after):return [dict(path=path,before=before,after=after)]
    if isinstance(before,dict):
        if set(before)!=set(after):return [dict(path=path,before_keys=sorted(before),after_keys=sorted(after))]
        return [change for key in before for change in differences(before[key],after[key],path+'/'+str(key))]
    if isinstance(before,list):
        if len(before)!=len(after):return [dict(path=path,before=before,after=after)]
        return [change for index,(b,a) in enumerate(zip(before,after)) for change in differences(b,a,path+'/'+str(index))]
    return [] if before==after else [dict(path=path,before=before,after=after)]
def metadata(info):
    return dict(date_time=info.date_time,compression=info.compress_type,flags=info.flag_bits,create_system=info.create_system,
        create_version=info.create_version,extract_version=info.extract_version,internal_attr=info.internal_attr,external_attr=info.external_attr,
        extra=info.extra.hex(),comment=info.comment.hex(),CRC=info.CRC,size=info.file_size,compressed_size=info.compress_size)
def entries(path):
    raw=Path(path).read_bytes();result={}
    with zipfile.ZipFile(path) as z:
        assert z.namelist()==['header.json','objects.json','surface_terrain.json'] and z.testzip() is None
        for info in z.infolist():
            assert info.flag_bits==0 and info.compress_type==zipfile.ZIP_DEFLATED
            fields=struct.unpack_from('<IHHHHHIIIHH',raw,info.header_offset);assert fields[0]==0x04034b50
            start=info.header_offset+30+fields[-2]+fields[-1]
            result[info.filename]=dict(content_sha256=digest(z.read(info.filename)),compressed_payload_sha256=digest(raw[start:start+info.compress_size]),
                metadata=metadata(info),local_header_offset=info.header_offset)
    return result
def inspect(path):
    with zipfile.ZipFile(path) as z:
        header=json.loads(z.read('header.json'));objects=json.loads(z.read('objects.json'))
        assert encode(objects)==z.read('objects.json'),'Original object serialization must be exactly understood'
        assert set(header['players'])=={'red','blue'}
        heroes={}
        for player,colour in ROLES.items():
            owned=[(key,obj) for key,obj in objects.items() if obj.get('type')=='hero' and obj.get('options',{}).get('owner')==colour]
            assert len(owned)==1,'Exactly one actual starting hero per owned role required'
            key,obj=owned[0];declared=header['players'][colour]['heroes']
            assert set(declared)=={key} and declared[key]['type']==obj['options']['type']
            army=obj['options']['army'];assert isinstance(army,list) and army
            assert all(set(stack)=={'amount','type'} and type(stack['amount']) is int and 0<stack['amount']<=2**31//4-1 and isinstance(stack['type'],str) for stack in army)
            heroes[player]=dict(key=key,colour=colour,army=copy.deepcopy(army))
        return header,objects,heroes
def verify_variant(source,target,player,multiplier):
    header,objects,heroes=inspect(source);info=heroes[player]
    with zipfile.ZipFile(target) as z:
        after=json.loads(z.read('objects.json'));assert z.read('header.json')==zipfile.ZipFile(source).read('header.json')
    expected=copy.deepcopy(objects)
    for stack in expected[info['key']]['options']['army']:stack['amount']*=multiplier
    assert after==expected
    changes=differences(objects,after)
    expected_changes=[] if multiplier==1 else [dict(path=f"/{info['key']}/options/army/{i}/amount",before=s['amount'],after=s['amount']*multiplier) for i,s in enumerate(info['army'])]
    assert changes==expected_changes,'Only owned starting-hero amount fields may change'
    before_entries=entries(source);after_entries=entries(target)
    for name in before_entries:
        if name!='objects.json' or multiplier==1:
            assert before_entries[name]['content_sha256']==after_entries[name]['content_sha256']
            assert before_entries[name]['compressed_payload_sha256']==after_entries[name]['compressed_payload_sha256']
            assert before_entries[name]['metadata']==after_entries[name]['metadata']
    if multiplier==1:assert Path(source).read_bytes()==Path(target).read_bytes()
    return dict(owned_hero_key=info['key'],owner_colour=info['colour'],original_army=info['army'],modified_army=after[info['key']]['options']['army'],
        JSON_semantic_changes=changes,ZIP_entries={name:dict(before=before_entries[name],after=after_entries[name]) for name in before_entries},
        all_other_objects_semantically_identical=True,header_and_terrain_content_and_compressed_payload_exact=True,original_archive_exact=multiplier==1)
def main():
    p=argparse.ArgumentParser();p.add_argument('--source-dir',type=Path,default=LAB/'data/vcmi/Maps/adv');p.add_argument('--out',type=Path,default=HERE/'maps');a=p.parse_args()
    assert not a.out.exists(),'Preserve existing map derivations';a.out.mkdir(parents=True)
    manifest=dict(schema='active-opponent-hero-count-TRAIN-mapset-v1',sources={},variants=[],native_runs=0,GPU_steps=0,optimizer_steps=0,shared_runtime_maps_written=False)
    for index,(name,expected_sha) in enumerate(SOURCES.items(),1):
        source=(a.source_dir/(name+'.vmap')).resolve();assert sha(source)==expected_sha
        header,objects,heroes=inspect(source)
        manifest['sources'][name]=dict(path=str(source),sha256=expected_sha,ZIP_entries=entries(source),role_heroes=heroes)
        for player in (0,1):
            for multiplier in (1,2,4):
                mapname=f'active-calibration-train-{index:02d}-owned{player}-hero-x{multiplier}';target=a.out/(mapname+'.vmap')
                if multiplier==1:target.write_bytes(source.read_bytes())
                else:
                    modified=copy.deepcopy(objects)
                    for stack in modified[heroes[player]['key']]['options']['army']:stack['amount']*=multiplier
                    with zipfile.ZipFile(source) as src,zipfile.ZipFile(target,'w') as dst:
                        dst.comment=src.comment
                        for info in src.infolist():dst.writestr(copy.copy(info),encode(modified) if info.filename=='objects.json' else src.read(info.filename),compresslevel=6)
                proof=verify_variant(source,target,player,multiplier)
                manifest['variants'].append(dict(map=mapname,path=str(target.resolve()),sha256=sha(target),source_map=name,owned_player=player,multiplier=multiplier,**proof))
        assert sha(source)==expected_sha
    manifest['deriver_sha256']=sha(__file__);manifest['passed']=True
    (HERE/'MAP_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(dict(passed=True,variants=len(manifest['variants']),source_maps=len(SOURCES),native_runs=0,shared_runtime_maps_written=False)))
if __name__=='__main__':main()
