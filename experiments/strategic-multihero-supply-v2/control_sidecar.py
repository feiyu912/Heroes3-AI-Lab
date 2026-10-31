"""Atomic save binding utility. NOT a native save/load integration or recovery proof.

Native adapter deliberately rejects restore until a fresh-process native test binds
these verified metadata to the actual reconstructed engine state and C++ members.
"""
import hashlib
import json
import os
from pathlib import Path
import tempfile

EPOCH='scripted-supply-control-v1'
BOUNDARY_KEYS={'pending_request','movement_busy','battle_busy','native_query_open','owned_request_count','queued_own_turn'}
CONTROL_KEYS={'main','courier','home','turn','cursor','cycles','phase','spent','blocked','goals','visited'}

def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def validate_control(control):
    if set(control)!=CONTROL_KEYS: raise ValueError('control_fields_missing_or_unknown')
    for key in ('main','courier','home','turn','cursor','cycles','phase'):
        if type(control[key]) is not int: raise ValueError('control_integer_required')
    if min(control['main'],control['courier'],control['home'])<0 or control['main']==control['courier']:
        raise ValueError('invalid_roles')
    if control['turn']<1 or control['cursor'] not in (0,1) or control['cycles']<0 or control['phase'] not in (0,1,2):
        raise ValueError('invalid_boundary_control')  # Exchange is never a save boundary.
    roles={str(control['main']),str(control['courier'])}
    for key in ('spent','blocked','goals'):
        if type(control[key]) is not dict or not set(control[key])<=roles: raise ValueError('invalid_hero_map')
    # Ordinary scheduling stops at 48, but a live meeting at that boundary must
    # still drain up to six whole-stack transfers while preserving one stack.
    if any(type(n) is not int or not 0<=n<=54 for n in control['spent'].values()): raise ValueError('invalid_budget')
    if any(type(s) is not str for s in control['blocked'].values()): raise ValueError('invalid_block_reason')
    positions=list(control['goals'].values())+control['visited']
    if any(type(p) is not list or len(p)!=3 or any(type(n) is not int or n<0 for n in p) for p in positions):
        raise ValueError('invalid_position')

def validate_boundary(boundary):
    if set(boundary)!=BOUNDARY_KEYS: raise ValueError('boundary_fields_missing_or_unknown')
    if boundary['pending_request'] is not None: raise ValueError('pending_request')
    for key in ('movement_busy','battle_busy','native_query_open','queued_own_turn'):
        if boundary[key] is not False: raise ValueError('not_drained_'+key)
    if type(boundary['owned_request_count']) is not int or boundary['owned_request_count']!=0:
        raise ValueError('owned_requests_not_drained')

def write_sidecar(path,save,control,world,boundary,source_manifest,run_identity):
    validate_control(control);validate_boundary(boundary)
    if not run_identity: raise ValueError('run_identity_required')
    heroes=world.get('heroes',[])
    if len(heroes)!=2 or {h['id'] for h in heroes}!={control['main'],control['courier']}:
        raise ValueError('actual_roster_role_mismatch')
    payload={'epoch':EPOCH,'native_restore_qualified':False,'save_sha256':sha(save),
             'source_manifest_sha256':sha(source_manifest),'run_identity':run_identity,
             'control':control,'world':world,'boundary':boundary}
    wrapper={'payload':payload,'payload_sha256':hashlib.sha256(canonical(payload)).hexdigest()}
    target=Path(path);target.parent.mkdir(parents=True,exist_ok=True)
    fd,temp=tempfile.mkstemp(prefix=target.name+'.',suffix='.tmp',dir=target.parent)
    try:
        with os.fdopen(fd,'wb') as stream:
            stream.write(canonical(wrapper)+b'\n');stream.flush();os.fsync(stream.fileno())
        os.replace(temp,target)
        if os.name!='nt':
            directory=os.open(target.parent,os.O_DIRECTORY)
            try: os.fsync(directory)
            finally: os.close(directory)
    finally:
        if os.path.exists(temp): os.unlink(temp)

def validate_sidecar(path,save,actual_world,source_manifest,run_identity,actual_turn):
    wrapper=json.loads(Path(path).read_text(encoding='utf-8'))
    if set(wrapper)!={'payload','payload_sha256'}: raise ValueError('wrapper_fields')
    p=wrapper['payload']
    if hashlib.sha256(canonical(p)).hexdigest()!=wrapper['payload_sha256']: raise ValueError('sidecar_checksum_mismatch')
    if p['epoch']!=EPOCH or p['native_restore_qualified'] is not False: raise ValueError('unsupported_epoch_or_claim')
    if p['save_sha256']!=sha(save): raise ValueError('native_save_mismatch')
    if p['source_manifest_sha256']!=sha(source_manifest): raise ValueError('source_epoch_mismatch')
    if p['run_identity']!=run_identity: raise ValueError('run_identity_mismatch')
    if canonical(p['world'])!=canonical(actual_world): raise ValueError('native_world_mismatch')
    if p['control']['turn']!=actual_turn: raise ValueError('own_turn_mismatch')
    validate_control(p['control']);validate_boundary(p['boundary'])
    return p['control']  # Verified data only. No C++ member hydration or native resume claim.
