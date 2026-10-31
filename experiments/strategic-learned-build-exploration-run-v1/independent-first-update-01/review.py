"""Independent CPU final review. Existing auditor reused; no native/CUDA execution."""
import hashlib,json,os,re,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;RUN=HERE.parent;POLICY=RUN.parent/'strategic-learned-build-exploration-policy-v1'
LAB=Path('/root/heroes3-ai-lab');TRAIN=LAB/'evaluations/strategic-learned-build-exploration-train-01';DEV=LAB/'evaluations/strategic-learned-build-exploration-dev-01'
sys.path.insert(0,str(POLICY));sys.path.insert(0,str(RUN))
from broker import Broker
from load_admitted import load
from pipeline_common import source_inputs,capsule_inputs,validate_capsule,validate_native_epoch
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_text())
def rows(path):return [json.loads(line) for line in Path(path).read_text().splitlines() if line]
def digest(obj):return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def write(path,value):Path(path).write_text(json.dumps(value,indent=2)+'\n')
def differences(a,b,path=''):
    if type(a)!=type(b):return [dict(path=path,a=a,b=b)]
    if isinstance(a,dict):
        result=[]
        for key in sorted(set(a)|set(b)):
            if key not in a or key not in b:result.append(dict(path=path+'/'+key,a=a.get(key),b=b.get(key)))
            else:result.extend(differences(a[key],b[key],path+'/'+key))
            if len(result)>=12:break
        return result[:12]
    if isinstance(a,list):
        if len(a)!=len(b):return [dict(path=path+'/length',a=len(a),b=len(b))]
        result=[]
        for index,(x,y) in enumerate(zip(a,b)):
            result.extend(differences(x,y,path+'/'+str(index)))
            if len(result)>=12:break
        return result[:12]
    return [] if a==b else [dict(path=path,a=a,b=b)]
def calendar(native,owned):
    # Native calendar markers, not strategy-trace end rows or own_turn==day.
    text=re.sub(r'\x1b\[[0-9;]*m','',(native/'client.log').read_text());turns=[];infos=[];client_days=0;terminal=None
    for number,line in enumerate(text.splitlines(),1):
        clean=line.strip();match=re.fullmatch(r'Turn (\d+)',clean)
        if match:turns.append(int(match[1]))
        match=re.fullmatch(r'Info about turn (\d+) has been sent!',clean)
        if match:infos.append(int(match[1]))
        if clean=='Applied on gs: 7NewTurn':client_days+=1
        if 'DirectorTypedEvent ' in line:
            event=json.loads(line.split('DirectorTypedEvent ',1)[1])
            if event['event']=='game_over' and event['player']==owned:
                assert terminal is None and event['completed'] and turns and infos==turns
                assert turns==list(range(1,turns[-1]+1)) and client_days==turns[-1]
                terminal=dict(native_day=turns[-1],own_turn=event['own_turn'],client_line=number)
    assert terminal is not None
    terminal['first_policy_day']=read(native/'agent/request-00000001.json')['day']
    terminal['elapsed_days']=terminal['native_day']-terminal['first_policy_day'];assert terminal['elapsed_days']>=0
    return terminal
def main():
    baseline=RUN.parent/'strategic-learned-build-exploration-v1/calibration-01/build-offset-initialization.pt';trained=TRAIN/'update-01/update-1.pt'
    brokers={sha(path):Broker('new-policy',path) for path in (baseline,trained)}
    capsule=LAB/'evaluations/strategic-learned-economy-build-capsule-01';validate_capsule(capsule)
    frozen_paths=set(source_inputs()+capsule_inputs(capsule)+list((RUN/'dev-tools').glob('*.py'))+[RUN/'dev-tools/PLAN.md',baseline,trained,TRAIN/'RESULT.json',DEV/'RESULT.json'])
    frozen={str(path):sha(path) for path in sorted(frozen_paths)}
    write(HERE/'INPUTS.json',frozen)
    cases=[('train',str(i),TRAIN/f'cell-{i:02d}') for i in range(8)]
    cases += [('dev',f'{i:02d}-{arm}',DEV/f'pair-{i:02d}'/arm) for i in range(8) for arm in ('a','b')]
    output=[];build_rows=[];dev_rows={};admitted_rows=0;dev_choices=0
    for phase,identity,case in cases:
        native=case/'native';original=read(case/'raw-audit/AUDIT.json');destination=HERE/'raw-reaudit'/f'{phase}-{identity}'
        destination.parent.mkdir(exist_ok=True)
        proc=subprocess.run([sys.executable,str(RUN/'audit_game_v6.py'),str(native),str(destination)],capture_output=True,text=True,env=dict(os.environ,CUDA_VISIBLE_DEVICES=''))
        if proc.returncode:
            (HERE/f'FAILED-{phase}-{identity}.log').write_text(proc.stdout+'\n'+proc.stderr)
            raise AssertionError('Frozen raw auditor failed '+str(case))
        audit=read(destination/'AUDIT.json');assert audit==original,'Re-audited raw certificate differs '+str(case)
        assert all(sha(native/name)==value for name,value in audit['raw_sha256'].items())
        plan=read(native/'PLAN.json');execution=read(native/'EXECUTION.json');validate_native_epoch(audit,plan,execution)
        assert all(sha(path)==value for path,value in plan['hashes'].items())
        proposals=rows(native/'agent/typed-broker.jsonl');events=rows(destination/'events.jsonl')
        actual={e['decision_id']:e for e in events if e['event']=='native_action_sent' and e['decision_id'] is not None}
        assert len(actual)==len(proposals)==audit['counts']['new_policy_decisions']
        assert len({e['native_request_id'] for e in actual.values()})==len(actual)
        for proposal in proposals:
            response=proposal['response'];q=proposal['request'];number=response['decision_id'];sent=actual[number]
            raw=(native/f'agent/request-{number:08d}.json').read_bytes()
            assert json.loads(raw)==q and hashlib.sha256(raw).hexdigest()==response['request_sha256']==proposal['request_sha256']
            assert all(sent[key]==response[key] for key in ('decision_id','player','hero','own_turn','op','selected_index','request_sha256'))
            assert sent['candidate']==q['candidates'][response['selected_index']]
            assert proposal['model_sha256']==sha(plan['checkpoint'])
            if phase=='dev':
                ready=read(native/'agent/broker-ready.json');assert ready['mode']=='new-policy' and ready['device']=='cpu' and ready['model_sha256']==proposal['model_sha256']
                expected=brokers[proposal['model_sha256']].propose(raw,number)
                assert proposal==expected,'CPU exact argmax/value/proposal mismatch '+str(case)+'/'+str(number)
                dev_choices+=1
        for build in audit['build_evidence']['builds']:
            proposal=next(p for p in proposals if p['response']['decision_id']==build['decision_id'])
            c=proposal['request']['candidates'][proposal['response']['selected_index']];before=build['before'];after=build['after']
            assert c['op']=='build' and actual[build['decision_id']]['native_request_id']==build['native_request_id']
            assert all(before['resources'][key]-after['resources'][key]==value for key,value in c['cost'].items())
            assert c['building_id'] not in before['buildings'] and c['building_id'] in after['buildings']
            assert set(before['buildings'])<=set(after['buildings']) and after['built_today']==before['built_today']+1
            build_rows.append(dict(case=str(case),native_request_id=build['native_request_id'],decision_id=build['decision_id'],town_id=c['town_id'],building_id=c['building_id'],cost=c['cost'],before=before,after=after))
        record=dict(phase=phase,identity=identity,case=str(case),calendar=calendar(native,plan['owned_player']),raw_auditor_actually_rerun=True,certificate_exact=sha(destination/'AUDIT.json')==sha(case/'raw-audit/AUDIT.json'),
            whole_game_valid=audit['whole_game_valid'],winner=audit['winner'],owned_player=plan['owned_player'],counts=audit['counts'],actual_bound_policy_actions=len(actual),
            raw_audit_sha256=sha(destination/'AUDIT.json'),model_sha256=sha(plan['checkpoint']))
        if phase=='train':
            samples,episode,admission=load(case/'admitted');assert len(samples)==len(proposals);admitted_rows+=len(samples)
            for sample,proposal in zip(samples,proposals):
                assert sample['request']==proposal['request'] and sample['action']==proposal['action']
                assert sample['old_logprob']==proposal['old_logprob'] and sample['old_value']==proposal['old_value']
                assert sample['native_request_id']==actual[sample['decision_id']]['native_request_id']
            record.update(admission_hash_chain_verified=True,cuda_sampling_replay_certificate_verified=True,cuda_sampling_replay_rerun=False,admitted_rows=len(samples))
        else:dev_rows[identity]=proposals
        output.append(record)
        write(HERE/'PROGRESS.json',dict(completed=len(output),total=24,cases=output));print(json.dumps(dict(completed=len(output),phase=phase,identity=identity,policy_actions=len(actual),builds=audit['counts']['policy_builds'])),flush=True)
    pairs=[]
    for i in range(8):
        a,b=dev_rows[f'{i:02d}-a'],dev_rows[f'{i:02d}-b'];prefix=0;first_action=None
        for n,(x,y) in enumerate(zip(a,b),1):
            if x['request']!=y['request']:break
            prefix+=1
            if first_action is None and x['response']['selected_index']!=y['response']['selected_index']:
                first_action=dict(decision_id=n,a=x['response']['op'],b=y['response']['op'],a_index=x['response']['selected_index'],b_index=y['response']['selected_index'])
        mismatch=None
        if prefix<min(len(a),len(b)):
            mismatch=dict(decision_id=prefix+1,first_differences=differences(a[prefix]['request'],b[prefix]['request']))
        result=next(p for p in read(DEV/'RESULT.json')['pairs'] if p['pair']==i)
        first_equal=a[0]['request']==b[0]['request'];assert first_equal==result['initial_request_exact']
        pairs.append(dict(pair=i,job=result['job'],initial_observation_semantics_equal=first_equal,equal_request_prefix=prefix,
            a_decisions=len(a),b_decisions=len(b),first_request_mismatch=mismatch,first_action_difference_on_equal_request=first_action,
            a_win=result['arms']['a']['win'],b_win=result['arms']['b']['win']))
    restore=POLICY/'recovery-audit-01/native-cuda-01/AUDIT.json';certificate=read(restore)
    assert certificate['passed_exact'] and certificate['checkpoint_sha256']==sha(trained) and certificate['optimizer_steps_restored']==120
    assert certificate['model_Adam_stop_moment_exact'] and certificate['cpu_CUDA_python_RNG_exact'] and certificate['invalid_resume_does_not_mutate_state']
    assert len(certificate['negative_cases'])==6 and certificate['auditor_sha256']==sha(POLICY/'recovery-audit-01/audit_checkpoint_cuda.py')
    assert all(sha(path)==value for path,value in frozen.items())
    assert admitted_rows==1891 and sum('/cell-' in row['case'] for row in build_rows)==28
    dev_cases=[r for r in output if r['phase']=='dev']
    wins={arm:sum(p[arm+'_win'] for p in pairs) for arm in ('a','b')};assert wins=={'a':4,'b':4}
    report=dict(passed=True,train_games=8,dev_games=16,train_admitted_rows=admitted_rows,real_train_policy_builds=sum('/cell-' in row['case'] for row in build_rows),
        dev_cpu_argmax_proposals_actually_recomputed=dev_choices,dev_wins=wins,dev_policy_builds=sum(r['counts']['policy_builds'] for r in dev_cases),dev_policy_end_turns=sum(r['counts']['policy_end_turns'] for r in dev_cases),
        all_24_raw_audits_actually_rerun_and_exact=True,all_actual_policy_bindings_checked=True,all_manifest_capsule_raw_source_hashes_verified=True,
        train_cuda_replay_rerun=False,train_cuda_replay_admission_certificates_verified=True,gpu_restore_rerun=False,
        gpu_restore_certificate=dict(path=str(restore),sha256=sha(restore),verified=True,checkpoint_sha256=sha(trained),optimizer_steps=120),
        new_native_runs=0,new_gpu_runs=0,new_optimizer_steps=0,cases=output,pairs=pairs,
        actual_cpu_build_bias={h:float(b.model.actor.build_bias.detach().cpu()) for h,b in brokers.items()},
        limitations=['Raw audit implementation reused frozen root auditor; additional cost/row/CPU-policy checks are independent here.',
                    'CUDA multinomial replay and saved optimizer/RNG recovery were not rerun; existing exact certificates/hash chains verified only.',
                    'Initial policy already has a zero-gradient build_bias=1.5; both arms building does not establish that PPO learned building.',
                    'Live continuation controller and logical updates1..3 are outside this review and are not asserted to be in the first checkpoint source protocol.',
                    'Paired observations describe published own-state/candidates only, not full hidden-world equality or causal strength improvement.'])
    write(HERE/'BUILD_TRANSACTIONS.json',build_rows);write(HERE/'REPORT.json',report)
    print(json.dumps({k:v for k,v in report.items() if k not in ('cases','pairs','limitations')},indent=2))
if __name__=='__main__':main()
