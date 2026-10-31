"""Strict derived targets over immutable native/CUDA admissions; no optimizer."""
import argparse,copy,hashlib,json,math,re,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
EXPERIMENTS=HERE.parent
PIPELINE=EXPERIMENTS/'strategic-learning-mainline-20261020/native-pipeline'
BASE=EXPERIMENTS/'strategic-typed-training-v1'
sys.path[:0]=[str(PIPELINE),str(BASE)]
from pipeline_common import validate_cells,validate_native_epoch,source_inputs,INITIAL_SHA,DEFAULT_CAPSULE,EPOCH as COLLECTION_EPOCH
from load_admitted import load as load_original
SCHEMA='strategic-efficiency-derived-targets-v1'
EPOCH='strategic-efficiency-reward-matched-data-v1'
SEED=2026102300
FORMULA='win:1-0.05*T/(T+75);loss:-1;T=terminal_native_day-first_request_day'
ARMS={'control':'native_win:+1;native_loss:-1','treatment':FORMULA}
NATIVE_ROOT=Path('/root/heroes3-ai-lab/src/vcmi-adv')
DAY_RELATIVE=['server/CGameHandler.cpp','server/processors/NewTurnProcessor.cpp']
DAY_SOURCES=[DEFAULT_CAPSULE/'source-snapshot'/r if (DEFAULT_CAPSULE/'source-snapshot'/r).is_file() else NATIVE_ROOT/r for r in DAY_RELATIVE]
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def read(path):return json.loads(Path(path).read_text())
def write(path,value):Path(path).write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
def compiled_day_sources(capsule):
    capsule=Path(capsule);manifest=read(capsule/'build-source-manifest.json');proof={}
    for relative in DAY_RELATIVE:
        path=capsule/'source-snapshot'/relative
        if not path.is_file():path=NATIVE_ROOT/relative
        actual=sha(path)
        if actual!=manifest[relative]['sha256']:raise ValueError('Calendar source differs from actual compiled source manifest: '+relative)
        proof[relative]=dict(path=str(path),sha256=actual,compiled_manifest_sha256=sha(capsule/'build-source-manifest.json'))
    return proof
def sources():
    paths=set(source_inputs())|set(HERE.glob('*.py'))|{HERE/'PLAN.md'}|set(DAY_SOURCES)
    return {str(p.resolve()):sha(p) for p in sorted(paths,key=str)}
def learning_return(native_reward,elapsed,arm):
    if type(native_reward) not in (int,float) or native_reward not in (-1.,1.):raise ValueError('Complete native +/-1 outcome required')
    if type(elapsed) is not int or elapsed<0:raise ValueError('Invalid native elapsed day')
    if arm not in ('control','treatment'):raise ValueError('Unknown registered arm')
    return 1.-.05*elapsed/(elapsed+75) if arm=='treatment' and native_reward==1 else float(native_reward)
def validate_derived_sample(sample,*,expected=None):
    # Local formula/shape gate only. Raw authentication is verify_targets()
    # followed by load_targets(); a standalone self-consistent row is no proof.
    target=sample.get('learning_target',{})
    if expected is not None and target!=expected:raise ValueError('Target differs from certified episode evidence')
    if target.get('schema')!=SCHEMA or target.get('epoch')!=EPOCH or target.get('formula')!=FORMULA:raise ValueError('Missing registered target protocol')
    if target.get('episode_id')!=sample.get('episode_id') or not re.fullmatch('[0-9a-f]{64}',target.get('evidence_sha256','')):raise ValueError('Missing target evidence binding')
    start,end=target.get('first_request_day'),target.get('terminal_native_day')
    if type(start) is not int or type(end) is not int or start<1 or end<start:raise ValueError('Invalid proven calendar days')
    value=learning_return(target.get('native_reward'),end-start,target.get('arm'))
    if type(sample.get('return')) not in (int,float) or not math.isfinite(sample['return']) or sample['return']!=value:raise ValueError('Derived formula mismatch')
    return value

def native_day_evidence(run,rows,episode,native):
    """Bind day to audited client server markers AND client-applied NewTurn order.

    Typed game_over has no day. Server Turn n precedes send; client NewTurn
    applies before PlayerStartsTurn/yourTurn. Validate every policy request,
    not last policy day (terminal may occur on the opponent turn).
    """
    owned=episode['job']['owned_player'];colour=('red','blue')[owned]
    lines=re.sub(r'\x1b\[[0-9;]*m','',(run/'client.log').read_text()).splitlines()
    typed=[];turns=[];infos=[];applies=[];player_starts=[];native_ends=[]
    for line_no,line in enumerate(lines,1):
        text=line.strip()
        m=re.fullmatch(r'Turn (\d+)',text)
        if m:turns.append((line_no,int(m[1])))
        m=re.fullmatch(r'Info about turn (\d+) has been sent!',text)
        if m:infos.append((line_no,int(m[1])))
        if text=='Applied on gs: 7NewTurn':applies.append(line_no)
        if text=='Applied on gs: 16PlayerStartsTurn':player_starts.append(line_no)
        if 'DirectorTypedEvent ' in line:typed.append((line_no,json.loads(line.split('DirectorTypedEvent ',1)[1])))
        m=re.fullmatch(r'DirectorAI: native gameOver player=(red|blue) victory=([01]) loss=([01])',text)
        if m and m[1]==colour:native_ends.append((line_no,int(m[2]),int(m[3])))
    mirrors=[event for _,event in typed]
    archived=[json.loads(line) for line in (run/'typed.jsonl').read_text().splitlines() if line]
    if mirrors!=archived:raise ValueError('Typed mirror/file differs')
    ends=[(n,e) for n,e in typed if e.get('event')=='game_over' and e.get('player')==owned]
    if len(ends)!=1 or ends[0][1].get('completed') is not True or len(native_ends)!=1:raise ValueError('Missing/ambiguous actual terminal')
    terminal_line,terminal=ends[0];native_line,win,loss=native_ends[0]
    expected_win=int(episode['reward']==1.)
    if win!=expected_win or loss!=1-win or native['winner']!=('red','blue')[owned if win else 1-owned] or native_line>=terminal_line:raise ValueError('Native terminal outcome differs')
    # Server marker n.day and independently received NewTurn count must agree.
    before=[(n,d) for n,d in turns if n<terminal_line]
    done=[(n,d) for n,d in infos if n<terminal_line]
    applied=[n for n in applies if n<terminal_line]
    if not before or [d for _,d in before]!=list(range(1,before[-1][1]+1)):raise ValueError('Native Turn sequence missing/repeated/non-fresh')
    if [d for _,d in done]!=[d for _,d in before] or len(applied)!=len(before):raise ValueError('Native day send/apply disagreement')
    for (start,day),(finish,day2),applied_line in zip(before,done,applied):
        if day!=day2 or not start<finish or not start<applied_line:raise ValueError('Malformed native new-day order')
    if not native_line<terminal_line or not any('Applied on gs: 14PlayerEndsGame' in s for s in lines[max(0,native_line-8):native_line-1]):raise ValueError('Native terminal lacks received PlayerEndsGame')
    policy=[(n,e) for n,e in typed if e.get('event')=='native_action_sent' and e.get('classification')=='new_policy']
    if len(policy)!=len(rows):raise ValueError('Policy evidence count differs')
    first_day=None;request_proofs=[]
    for sample,(line_no,event) in zip(rows,policy):
        number=sample['decision_id'];path=run/f'agent/request-{number:08d}.json';request=read(path)
        if request!=sample['request'] or sha(path)!=sample['request_sha256']:raise ValueError('Raw request/row differs')
        if any(event.get(k)!=sample.get(k) for k in ('decision_id','native_request_id','request_sha256')) or event.get('player')!=owned:raise ValueError('Unbound native policy request')
        current=[d for n,d in before if n<line_no];applied_count=sum(n<line_no for n in applied)
        if not current or request.get('day')!=current[-1] or request['day']!=applied_count:raise ValueError('Request day differs from native calendar')
        starts=[n for n in player_starts if n<line_no]
        if not starts or starts[-1]<applied[applied_count-1] or line_no>=terminal_line:raise ValueError('Policy outside received turn/terminal window')
        if first_day is None:first_day=request['day']
        request_proofs.append(dict(decision_id=number,native_request_id=event['native_request_id'],request_sha256=sha(path),day=request['day'],client_line=line_no))
    if first_day is None:raise ValueError('No first real policy request')
    return dict(first_request_day=first_day,terminal_native_day=before[-1][1],elapsed_days=before[-1][1]-first_day,
        terminal_client_line=terminal_line,native_game_over_line=native_line,terminal_own_turn=terminal['own_turn'],
        last_turn_marker_line=before[-1][0],last_turn_info_line=done[-1][0],last_client_newturn_line=applied[-1],
        calendar_basis='native server Turn n + Info(n.day) + client AppliedNewTurn + every bound policy request day',
        request_proofs=request_proofs)

def certify(directory):
    directory=Path(directory).resolve();rows,episodes,admission=load_original(directory);episode=episodes[0]
    paths=[Path(p) for p in admission['input_sha256'] if p.endswith('/sampling-state.pt')]
    if len(paths)!=1:raise ValueError('Ambiguous original collection')
    run=paths[0].parent.parent;plan=read(run/'PLAN.json');execution=read(run/'EXECUTION.json');native=read(episode['raw_audit_path'])
    validate_native_epoch(native,plan,execution)
    if native.get('contract_errors') or not episode.get('transport_drained') or episode['reward'] not in (-1.,1.):raise ValueError('Incomplete source episode')
    if plan['pipeline_epoch']!=COLLECTION_EPOCH or episode['checkpoint_sha256']!=INITIAL_SHA or sha(plan['checkpoint'])!=INITIAL_SHA:raise ValueError('Wrong collection parent/epoch')
    if not all(sha(run/name)==h for name,h in native['raw_sha256'].items()):raise ValueError('Raw native evidence changed')
    if not all(sha(path)==h for path,h in plan['hashes'].items()):raise ValueError('Collection frozen inputs changed')
    if any(s['return']!=episode['reward'] or s['policy_sha256']!=INITIAL_SHA for s in rows):raise ValueError('Source returns/parent differs')
    proof=native_day_evidence(run,rows,episode,native)
    evidence=dict(admission_directory=str(directory),episode_id=episode['episode_id'],native_reward=episode['reward'],
        native_winner=native['winner'],day_evidence=proof,compiled_calendar_source=compiled_day_sources(plan['capsule']),source_sha256={str(p):sha(p) for p in [directory/'AUDIT.json',directory/'episode.json',directory/'samples.jsonl',Path(episode['raw_audit_path'])]},
        audited_raw_sha256={str(run/name):h for name,h in native['raw_sha256'].items()},
        targets={arm:learning_return(episode['reward'],proof['elapsed_days'],arm) for arm in ('control','treatment')})
    evidence['evidence_sha256']=digest(evidence)
    return rows,episodes,admission,evidence

def verify_targets(path):
    manifest=read(Path(path)/'TARGETS.json')
    if manifest.get('schema')!=SCHEMA or manifest.get('epoch')!=EPOCH or manifest.get('formula')!=FORMULA or manifest.get('seed')!=SEED:raise ValueError('Wrong target protocol')
    if manifest.get('parent_sha256')!=INITIAL_SHA or manifest.get('arms')!=ARMS or manifest.get('original_samples_modified') is not False:raise ValueError('Wrong parent/arm/immutability metadata')
    if manifest.get('sources')!=sources():raise ValueError('Derived source closure changed or incomplete')
    evidence=[];all_episodes=[]
    for item in manifest['episodes']:
        _,episodes,_,actual=certify(item['admission_directory']);all_episodes+=episodes
        if actual!=item:raise ValueError('Derived evidence/target differs from original certified inputs')
        evidence.append(actual)
    validate_cells(all_episodes)
    if [e['job']['seed'] for e in all_episodes]!=list(range(SEED,SEED+8)) or any(e['job']['logical_update']!=0 for e in all_episodes):raise ValueError('Wrong registered batch order/seeds/update')
    if manifest.get('shared_batch_sha256')!=digest(evidence):raise ValueError('Shared batch digest differs')
    return manifest

def load_targets(directory,target_path,arm,*,verified=None):
    manifest=verify_targets(target_path) if verified is None else verified;key=str(Path(directory).resolve())
    matches=[e for e in manifest['episodes'] if e['admission_directory']==key]
    if len(matches)!=1:raise ValueError('Admission not in registered shared target batch')
    evidence=matches[0];rows,episodes,admission=load_original(directory);rows=copy.deepcopy(rows);episodes=copy.deepcopy(episodes)
    day=evidence['day_evidence'];value=evidence['targets'][arm]
    target=dict(schema=SCHEMA,epoch=EPOCH,formula=FORMULA,arm=arm,episode_id=evidence['episode_id'],native_reward=evidence['native_reward'],
        first_request_day=day['first_request_day'],terminal_native_day=day['terminal_native_day'],evidence_sha256=evidence['evidence_sha256'])
    for row in rows:
        row['native_reward']=row['return'];row['return']=value;row['learning_target']=target.copy();validate_derived_sample(row,expected=target)
    for episode in episodes:
        episode['native_reward']=episode['reward'];episode['reward']=value;episode['learning_target']=target.copy()
    return rows,episodes,admission

def main():
    p=argparse.ArgumentParser();p.add_argument('--shared',type=Path);p.add_argument('--out',type=Path);p.add_argument('--verify',type=Path);a=p.parse_args()
    if a.verify:
        value=verify_targets(a.verify);print(json.dumps(dict(passed=True,episodes=len(value['episodes']),shared_batch_sha256=value['shared_batch_sha256'],optimizer_steps=0)));return
    if not a.shared or not a.out:p.error('--shared and --out required to derive')
    evidence=[];episodes=[]
    for n in range(8):
        _,episode,_,proof=certify(a.shared/f'cell-{n:02d}/admitted');episodes+=episode;evidence.append(proof)
    validate_cells(episodes)
    if sorted(e['job']['seed'] for e in episodes)!=list(range(SEED,SEED+8)):raise ValueError('Wrong fresh shared batch seeds')
    value=dict(schema=SCHEMA,epoch=EPOCH,formula=FORMULA,seed=SEED,parent_sha256=INITIAL_SHA,arms=ARMS,sources=sources(),episodes=evidence,shared_batch_sha256=digest(evidence),original_samples_modified=False)
    a.out.mkdir(parents=True,exist_ok=False);write(a.out/'TARGETS.json',value);verify_targets(a.out)
    print(json.dumps(dict(passed=True,out=str(a.out),episodes=8,optimizer_steps=0)))
if __name__=='__main__':main()
