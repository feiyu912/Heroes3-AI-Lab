"""Prepare DEV plan and load both CPU policies. No native/optimizer/sampling."""
import argparse,hashlib,importlib.util,json,py_compile,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;RUN=HERE.parent;POLICY=RUN.parent/'strategic-learned-economy-policy-v1'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    baseline=POLICY/'cpu-01/build-initialization.pt'
    candidate=Path('/root/heroes3-ai-lab/evaluations/strategic-learned-build-training-01/update-01/update-1.pt')
    parent=json.loads((HERE/'PARENT_SOURCES.json').read_text());assert all(sha(path)==h for path,h in parent.items())
    for path in HERE.glob('*.py'):py_compile.compile(str(path),doraise=True)
    spec=importlib.util.spec_from_file_location('_build_dev_collect',HERE/'collect_cpu.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    assert module.LOCAL==RUN and module.HERE==POLICY and module.BROKER==POLICY/'broker.py'
    text=(HERE/'collect_cpu.py').read_text()
    assert "ready['mode']=='new-policy' and ready['device']=='cpu'" in text
    assert "str(LAB/'venv/bin/python')" in text and '--mode\',\'new-policy' in text
    assert 'onpolicy_cuda' not in text and "gpu-venv/bin/python" not in text
    # Root-native audit is unmodified and the wrapper dispatches only run(args).
    wrapper=(HERE/'evaluate_dev.py').read_text()
    assert 'from collect_cpu import run' in wrapper and 'run_proxy_game' not in wrapper and 'clearance_' not in wrapper
    process=subprocess.run([sys.executable,str(HERE/'evaluate_dev.py'),'--baseline',str(baseline),'--candidate',str(candidate),'--out',str(a.out)],capture_output=True,text=True)
    assert process.returncode==0,process.stdout+process.stderr
    plan=json.loads((a.out/'PLAN.json').read_text());assert plan['execute'] is False and plan['sampling']=='CPU argmax'
    assert len(plan['jobs'])==8 and [j['seed'] for j in plan['jobs']]==list(range(2026102700,2026102708))
    assert len({(j['map'],j['opponent'],j['player']) for j in plan['jobs']})==8
    assert all(sha(path)==h for path,h in plan['input_sha256'].items())
    assert all(str(path) in plan['input_sha256'] for path in HERE.glob('*.py'))
    sys.path.insert(0,str(POLICY));from broker import Broker
    request=Path('/root/heroes3-ai-lab/evaluations/strategic-learned-build-training-01/cell-00/native/agent/request-00000001.json').read_bytes()
    actions=[]
    for checkpoint in (baseline,candidate):
        broker=Broker('new-policy',checkpoint);proposal=broker.propose(request,1)
        assert next(broker.model.parameters()).device.type=='cpu'
        assert proposal['model_sha256']==sha(checkpoint) and proposal['response']['classification']=='new_policy'
        actions.append(dict(model_sha256=sha(checkpoint),op=proposal['response']['op'],selected_index=proposal['response']['selected_index']))
    result=dict(passed=True,plan_only=True,planned_games=16,planned_pairs=8,native_runs=0,gpu_runs=0,optimizer_steps=0,
        cpu_models_loaded_and_argmax_checked=True,archived_training_request_only=True,actions=actions,
        frozen_input_count=len(plan['input_sha256']),root_inputs_unchanged=True,plan=str(a.out/'PLAN.json'))
    (HERE/'CPU_REPORT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
