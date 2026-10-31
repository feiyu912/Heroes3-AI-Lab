"""Atomic native-boundary bundle coordinator. Does not run games, hydrate C++, or certify recovery."""
import argparse,hashlib,json,os,re,shlex,tempfile,time
from pathlib import Path
EPOCH='supply-native-boundary-v4'
HERE=Path(__file__).resolve().parent
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def sha(x):return hashlib.sha256(x).hexdigest()
def require(yes,reason):
    if not yes:raise ValueError(reason)

def decode_control(text):
    require(type(text) is str and len(text.encode())<=8*1024*1024,'control_size')
    tokens=iter(shlex.split(text,posix=True));count=0
    def token():
        nonlocal count
        count+=1;require(count<=1000000,'control_token_count')
        try:return next(tokens)
        except StopIteration:raise ValueError('truncated_control')
    def integer():
        value=token();require(re.fullmatch(r'-?(0|[1-9][0-9]*)',value) is not None,'control_integer');return int(value)
    def size(maximum):
        n=integer();require(0<=n<=maximum,'collection_size');return n
    def army():
        a=[[integer(),integer()] for _ in range(7)]
        require(all(n>=0 and (n==0 or c>=0) for c,n in a),'army_count');return a
    def mapping():
        result={}
        for _ in range(size(1024)):
            key=integer();value=integer();require(str(key) not in result,'duplicate_map');result[str(key)]=value
        return result
    require(token()==EPOCH,'control_epoch')
    source,nonce,player,day=token(),token(),integer(),integer()
    require(re.fullmatch('[0-9a-f]{64}',source) is not None and re.fullmatch('[A-Za-z0-9_-]{1,96}',nonce) is not None,'identity')
    names=['main','courier','home','turn','cursor','cycles','phase','phase_before_exchange','job','successful_jobs','incomplete_attempts','job_status']
    c={name:integer() for name in names};c['delivery_reason']=token()
    require(c['phase'] in (0,1,2) and c['phase_before_exchange'] in (0,1,2) and c['job_status'] in (0,1,2,3),'phase')
    require(0<=player<8 and day>0 and c['turn']>0 and c['cursor'] in (0,1),'counter')
    c['initial_reserve_slots']=army();c['cargo_slots']=army()
    for name in ['reserve','cargo','picked','delivered','spent']:c[name]=mapping()
    c['blocked']={}
    for _ in range(size(2)):
        key=integer();value=token();require(str(key) not in c['blocked'],'duplicate_blocked');c['blocked'][str(key)]=value
    c['goals']={}
    for _ in range(size(2)):
        key=integer();pos=[integer() for _ in range(3)];require(min(pos)>=0 and str(key) not in c['goals'],'goal');c['goals'][str(key)]=pos
    visited=[[integer() for _ in range(3)] for _ in range(size(65536))]
    require(all(min(p)>=0 for p in visited) and len({tuple(p) for p in visited})==len(visited),'visited')
    heroes=[]
    for _ in range(size(2)):
        h={'id':integer(),'movement':integer(),'garrison':integer(),'boat':integer(),'position':[integer() for _ in range(3)],'army':army()}
        require(h['movement']>=0 and min(h['position'])>=0 and h['garrison'] in (0,1) and h['boat'] in (0,1),'hero_state');heroes.append(h)
    towns=[]
    for _ in range(size(128)):
        t={'id':integer(),'visitor':integer(),'position':[integer() for _ in range(3)],'army':army()};require(min(t['position'])>=0,'town_position');towns.append(t)
    economy=token();require(next(tokens,None) is None,'trailing_control')
    def totals(a):
        out={}
        for creature,n in a:
            if n:out[str(creature)]=out.get(str(creature),0)+n
        return out
    require(len(heroes)==2 and {h['id'] for h in heroes}=={c['main'],c['courier']} and c['main']!=c['courier'],'roster_roles')
    require(any(t['id']==c['home'] for t in towns),'home')
    require(c['reserve']==totals(c['initial_reserve_slots']) and bool(c['reserve']) and c['cargo']==totals(c['cargo_slots']),'reserve_cargo_slots')
    sum_=dict(c['cargo'])
    for creature,n in c['delivered'].items():sum_[creature]=sum_.get(creature,0)+n
    require(sum_==c['picked'],'cargo_conservation')
    for name in ['reserve','cargo','picked','delivered']:require(all(int(k)>=0 and n>0 for k,n in c[name].items()),'ledger_count')
    courier=next(h for h in heroes if h['id']==c['courier'])
    for actual,reserve,cargo in zip(courier['army'],c['initial_reserve_slots'],c['cargo_slots']):
        if reserve[1]:require(actual[0]==reserve[0] and actual[1]>=reserve[1],'reserve_lost')
        if cargo[1]:require(actual[0]==cargo[0] and actual[1]>=cargo[1]+reserve[1],'cargo_lost')
    roles={str(c['main']),str(c['courier'])}
    for name in ['spent','blocked','goals']:require(set(c[name])<=roles,'foreign_actor')
    require(all(0<=n<=54 for n in c['spent'].values()),'budget')
    return {'epoch':EPOCH,'source_token':source,'nonce':nonce,'player':player,'day':day,'control':c,'visited':visited,'world':{'heroes':heroes,'towns':towns,'economy':economy}}

def verify_manifest(path):
    path=Path(path);m=json.loads(path.read_text());require(m['recovery_epoch']==EPOCH,'manifest_epoch')
    require(len(m['files'])==13,'manifest_file_count')
    normalized={}
    for relative,entry in m['files'].items():
        file=(path.parent/'candidate'/relative);require(file.is_file() and not file.is_symlink(),'candidate_input_missing')
        data=file.read_bytes();require(sha(data)==entry['candidate_sha256'],'candidate_input_changed')
        if relative=='AI/DirectorAI/SupplyRecovery.h':
            require(data.count(m['source_token'].encode())==1,'compiled_source_literal');data=data.replace(m['source_token'].encode(),b'@COMPILED_SOURCE_TOKEN@')
        normalized[relative]=sha(data)
    require(normalized==m['normalized_source_inputs'] and sha(canonical(normalized))==m['source_token'],'compiled_source_token')
    return m

def stable_save(path):
    path=Path(path);require(path.is_file() and not path.is_symlink() and path.suffix=='.vsgm1','native_save_missing')
    before=path.stat();data=path.read_bytes();time.sleep(0.02);after=path.stat()
    require((before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns) and sha(data)==sha(path.read_bytes()),'native_save_not_stable')
    require(data[:4]==b'VCMI' and data[8:15]==b'VCMISVG' and len(data)>15,'native_save_header')
    return data

def collect(events,client_log,server_logs,manifest):
    m=verify_manifest(manifest);rows=[json.loads(s) for s in Path(events).read_text().splitlines() if s]
    client=Path(client_log).read_text(errors='replace');mirrors=[]
    for line in client.splitlines():
        if 'DirectorSupplyCheckpoint ' in line:mirrors.append(json.loads(line.split('DirectorSupplyCheckpoint ',1)[1]))
    require(rows==mirrors,'checkpoint_mirror_file_mismatch')
    order=['checkpoint_prepared','local_state_native_sent','local_state_real_ack','save_native_sent','checkpoint_snapshot'];selected=[]
    for name in order:
        matches=[(i,r) for i,r in enumerate(rows) if r['event']==name];require(len(matches)==1,'checkpoint_event_count_'+name);selected.append(matches[0])
    require([i for i,_ in selected]==sorted(i for i,_ in selected),'checkpoint_event_order')
    snapshot=selected[-1][1];payload=snapshot['payload'];decoded=decode_control(payload['control_text']);c=decoded['control']
    require(payload['epoch']==EPOCH and payload['source_token']==m['source_token']==decoded['source_token'],'payload_source_epoch')
    require(sha(payload['control_text'].encode())==payload['control_sha256'],'control_digest')
    require(c['turn']==2 and sum(c['spent'].values())>0 and c['job_status']==1 and c['phase']==2 and bool(c['cargo']) and c['cargo']==c['picked'] and not c['delivered'] and bool(decoded['visited']),'nontrivial_target_not_met')
    for _,row in selected:
        require(row['schema']=='supply-native-checkpoint-events-v4' and row['payload']==payload and row['source_token']==m['source_token'],'checkpoint_payload_changed')
        require(row['current_control_text']==payload['control_text'],'world_or_control_changed_during_save')
    require(snapshot['owned_callback_pending']==0 and selected[2][1]['owned_callback_pending']==0,'owned_not_drained_at_callback')
    for sent,ack,native_type in [(selected[1][1],selected[2][1],'SaveLocalState'),(selected[3][1],snapshot,'SaveGame')]:
        request=sent['request_id'];require(request>0 and ack['request_id']==request,'request_identity')
        register=re.findall(r'DirectorNativeRequestRegistered id='+str(request)+r' player=(-?\d+) pack_type=(\d+) type=([^\r\n]+)',client)
        reply=re.findall(r'DirectorNativeRequestAck id='+str(request)+r' player=(-?\d+) pack_type=(\d+) success=(\d+)',client)
        require(len(register)==1 and len(reply)==1,'native_owned_register_ack')
        require(register[0][:2]==reply[0][:2] and int(register[0][0])==decoded['player'] and reply[0][2]=='1' and native_type in register[0][2],'native_request_type_owner_success')
    save_name=payload['save_name'];require(save_name=='Saves/supply-boundary-v4-'+decoded['nonce'],'save_name_nonce')
    successes=[]
    for path in server_logs:
        log=Path(path).read_text(errors='replace');starts=[match.start() for match in re.finditer(re.escape('Saving to '+save_name),log)]
        for start in starts:
            end=log.find('Saving to ',start+1);section=log[start:end if end>=0 else len(log)]
            if 'Game has been successfully saved!' in section and 'Failed to save game:' not in section:successes.append(str(Path(path).resolve()))
    require(len(successes)==1,'native_successful_save_marker_missing_or_ambiguous')
    return m,snapshot,decoded,successes

def atomic_file(path,data):
    fd,temp=tempfile.mkstemp(prefix=path.name+'.',suffix='.tmp',dir=path.parent)
    with os.fdopen(fd,'wb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
    os.replace(temp,path)
    if os.name!='nt':
        fd=os.open(path.parent,os.O_DIRECTORY)
        try:os.fsync(fd)
        finally:os.close(fd)

def create_bundle(events,client_log,server_logs,manifest,save,out):
    m,snapshot,decoded,successes=collect(events,client_log,server_logs,manifest);data=stable_save(save)
    require(Path(save).stem==Path(snapshot['save_name']).name,'save_filename_mismatch')
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False);destination=out/Path(save).name
    atomic_file(destination,data)
    bundle={'epoch':EPOCH,'source_token':m['source_token'],'save_file':str(destination),'save_sha256':sha(data),
            'candidate_manifest_sha256':sha(Path(manifest).read_bytes()),'payload':snapshot['payload'],
            'payload_sha256':sha(canonical(snapshot['payload'])),'decoded_snapshot':decoded,
            'proof':{'events_sha256':sha(Path(events).read_bytes()),'client_log_sha256':sha(Path(client_log).read_bytes()),
                     'server_success_logs':{p:sha(Path(p).read_bytes()) for p in successes},'local_state_request_id':snapshot['local_state_request_id'],'save_request_id':snapshot['save_request_id']},
            'native_restore_qualified':False,'scope':'actual saved boundary bundle only; fresh native hydration/continuation still require independent proof'}
    atomic_file(out/'bundle.json',canonical(bundle)+b'\n');return out/'bundle.json'

def main():
    ap=argparse.ArgumentParser();sub=ap.add_subparsers(dest='command',required=True)
    p=sub.add_parser('create');p.add_argument('--events',type=Path,required=True);p.add_argument('--client-log',type=Path,required=True)
    p.add_argument('--server-log',type=Path,action='append',required=True);p.add_argument('--manifest',type=Path,default=HERE/'CANDIDATE_MANIFEST.json')
    p.add_argument('--save',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p=sub.add_parser('decode');p.add_argument('file',type=Path)
    args=ap.parse_args()
    if args.command=='decode':print(json.dumps(decode_control(args.file.read_text()),indent=2));return
    path=create_bundle(args.events,args.client_log,args.server_log,args.manifest,args.save,args.out)
    print(json.dumps({'bundle':str(path),'passed':True,'native_restore_qualified':False}))

if __name__=='__main__':main()
