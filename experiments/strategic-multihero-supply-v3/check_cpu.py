"""Synthetic boundary tests. Never certify fixture data as native execution."""
from pathlib import Path
import ast
import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import control_sidecar as sidecar

HERE=Path(__file__).resolve().parent

def main():
    checks=[]
    # Exercise the exact generated driver's deletion helper without importing or
    # executing its build path. Both restore paths must use this guarded helper.
    driver=(HERE/'build_capsule.py').read_text()
    tree=ast.parse(driver)
    helper=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='remove_added')
    namespace={}
    code=compile(ast.Module(body=[helper],type_ignores=[]),'extracted-builder-helper','exec')
    def reject(name,fn):
        try: fn()
        except (ValueError,KeyError,TypeError): checks.append({'case':name,'rejected':True});return
        raise AssertionError('negative accepted: '+name)
    with tempfile.TemporaryDirectory(prefix='supply-cpu-') as temp:
        work=Path(temp);binary=work/'controller'
        source_tree=work/'source';allowed=source_tree/'AI/DirectorAI';allowed.mkdir(parents=True)
        namespace.update(SOURCE=source_tree,DELETE_ALLOWLIST={'TypedPolicyProtocol.h','SupplyController.h','SupplyAdapter.inc'})
        exec(code,namespace)
        for name in namespace['DELETE_ALLOWLIST']:
            target=allowed/name;target.write_text('synthetic');namespace['remove_added'](target);assert not target.exists()
        try: namespace['remove_added'](allowed/'CDirectorAI.cpp')
        except AssertionError: checks.append({'case':'builder_nonwhitelisted_source_delete','rejected':True})
        else: raise AssertionError('builder unsafe delete')
        try: namespace['remove_added'](work/'SupplyController.h')
        except AssertionError: checks.append({'case':'builder_outside_parent_delete','rejected':True})
        else: raise AssertionError('builder outside delete')
        target=allowed/'SupplyController.h';target.symlink_to(work/'outside')
        try: namespace['remove_added'](target)
        except AssertionError: checks.append({'case':'builder_symlink_delete','rejected':True})
        else: raise AssertionError('builder symlink delete')
        assert driver.count('remove_added(target)')==2 and driver.count('remove_added(SOURCE/p)')==1
        assert "base==json.loads((ACCEPTED/'base-source-manifest.json').read_text())" in driver
        assert "original_hash==json.loads((ACCEPTED/'binary-sha256.json').read_text())" in driver
        capsule=json.loads((HERE/'CANDIDATE_MANIFEST.json').read_text())
        parent=json.loads((HERE.parent/'strategic-director-terminal-drain-v3/CANDIDATE_MANIFEST.json').read_text())
        for name,entry in capsule['files'].items():
            assert entry['baseline_sha256']==parent['files'].get(name,{}).get('baseline_sha256')
        checks.append({'case':'builder_exact_accepted_V8_baseline_and_three_binary_recompile_gates','passed':True})
        compile_result=subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror','-pedantic',
                                       str(HERE/'test_controller.cpp'),'-o',str(binary)],capture_output=True,text=True)
        assert compile_result.returncode==0,compile_result.stderr
        controller=json.loads(subprocess.check_output([str(binary)],text=True))
        save=work/'SYNTHETIC_NOT_NATIVE.vcgm1';save.write_bytes(b'synthetic native-save stand-in; no game executed')
        source=work/'manifest.json';source.write_text('{"synthetic_source":"v1"}')
        path=work/'control.json'
        control={'main':8,'courier':19,'home':3,'turn':2,'cursor':1,'cycles':0,'phase':2,
                 'spent':{'8':3,'19':2},'blocked':{},'goals':{'19':[8,4,0]},'visited':[[3,3,0]],
                 'job_state':{'id':1,'status':1,'successful_jobs':0,'incomplete_attempts':0,'success':False,'reason':'in_transit',
                              'initial_reserve_slots':[[2,3]]+[[-1,0]]*6,'cargo_slots':[[-1,0],[0,10]]+[[-1,0]]*5,
                              'reserve':[[2,3]],'picked':[[0,10]],'cargo_remaining':[[0,10]],'delivered':[]}}
        world={'heroes':[{'id':8,'position':[8,4,0],'army':[[0,5]]},
                         {'id':19,'position':[4,4,0],'army':[[0,10],[2,3]]}],
               'towns':[{'id':3,'army':[[4,12]]}]}
        boundary={'pending_request':None,'movement_busy':False,'battle_busy':False,
                  'native_query_open':False,'owned_request_count':0,'queued_own_turn':False}
        def write(c=control,w=world,b=boundary): sidecar.write_sidecar(path,save,c,w,b,source,'synthetic-run')
        def validate(w=world,run='synthetic-run',turn=2): return sidecar.validate_sidecar(path,save,w,source,run,turn)
        write();assert validate()==control
        assert not list(work.glob('control.json.*.tmp'))
        case=work/'case.json';case.write_text(json.dumps({'world':world,'control':control}))
        script='import json,sys; from pathlib import Path; import control_sidecar as c; d=json.loads(Path(sys.argv[1]).read_text()); assert c.validate_sidecar(sys.argv[2],sys.argv[3],d["world"],sys.argv[4],"synthetic-run",2)==d["control"]'
        subprocess.run([sys.executable,'-c',script,str(case),str(path),str(save),str(source)],cwd=HERE,check=True)
        checks.append({'case':'fresh_process_atomic_metadata_roundtrip','passed':True,'native_restore':False})
        for key,value in [('pending_request',42),('movement_busy',True),('battle_busy',True),
                          ('native_query_open',True),('owned_request_count',1),('queued_own_turn',True),
                          ('owned_request_count',False),('movement_busy',0)]:
            altered=copy.deepcopy(boundary);altered[key]=value
            reject('dirty_boundary_'+key+'_'+str(value),lambda b=altered:write(b=b))
        for key,value in [('main',19),('courier',99),('cursor',2),('turn',0),('phase',3),('spent',{'19':55}),
                          ('spent',{'99':1}),('goals',{'19':[-1,4,0]}),('cycles',True)]:
            altered=copy.deepcopy(control);altered[key]=value
            reject('bad_control_'+key+'_'+str(value),lambda c=altered:write(c=c))
        for key,value in [('status',2),('cargo_remaining',[]),('cargo_slots',[[-1,0]]*7),('reserve',[[2,2]]),
                          ('picked',[[0,11]]),('delivered',[[0,10]]),('success',True)]:
            altered=copy.deepcopy(control);altered['job_state'][key]=value
            reject('bad_job_state_'+key,lambda c=altered:write(c=c))
        altered=copy.deepcopy(control);altered['job_state'].pop('cargo_slots');reject('missing_job_cargo_slots',lambda:write(c=altered))
        altered=copy.deepcopy(control);altered.pop('visited');reject('missing_control_field',lambda:write(c=altered))
        altered=copy.deepcopy(boundary);altered.pop('queued_own_turn');reject('missing_boundary_field',lambda:write(b=altered))
        write();reject('wrong_run',lambda:validate(run='other-run'));reject('wrong_own_turn',lambda:validate(turn=3))
        for key in ['position','army']:
            altered=copy.deepcopy(world);altered['heroes'][0][key][0]=99
            reject('loaded_world_'+key+'_differs',lambda w=altered:validate(w=w))
        old=save.read_bytes();save.write_bytes(old+b'changed');reject('changed_native_save_bytes',validate);save.write_bytes(old)
        old=source.read_bytes();source.write_bytes(old+b'changed');reject('changed_source_epoch',validate);source.write_bytes(old)
        original=json.loads(path.read_text());broken=copy.deepcopy(original);broken['payload']['control']['cursor']=0
        path.write_text(json.dumps(broken));reject('sidecar_payload_checksum',validate)
        for field,value in [('epoch','old-epoch'),('native_restore_qualified',True)]:
            broken=copy.deepcopy(original);broken['payload'][field]=value
            broken['payload_sha256']=hashlib.sha256(sidecar.canonical(broken['payload'])).hexdigest()
            path.write_text(json.dumps(broken));reject('dishonest_'+field,validate)
        write();assert validate()==control
    report={'passed':True,'controller':controller,'sidecar_checks':checks,
            'native_games':0,'native_built':False,'native_restore_qualified':False,'optimizer_steps':0,
            'scope':'synthetic CPU C++ controller and atomic metadata gates; not native execution/restoration',
            'source_sha256':{name:hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in
                             ['SupplyController.h','test_controller.cpp','control_sidecar.py','check_cpu.py']}}
    (HERE/'CPU_REPORT.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'passed':True,'controller_checks':controller['checks'],'sidecar_checks':len(checks),
                      'native_games':0,'native_restore_qualified':False}))

if __name__=='__main__':main()
