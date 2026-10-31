"""Opt-in environment for a separately verified native CUDA opponent runtime."""
import json
import os
from pathlib import Path
import sys


def environment(profile=False,require_contract=True):
    r=Path(__file__).parent
    if require_contract:
        contract=json.loads((r/'native-cuda-contract.json').read_text())
        assert contract['passed'] and contract['all_exact_trajectories']
    runtime=json.loads((r/'native-cuda-runtime.json').read_text())
    result=dict(os.environ,LAB_NATIVE_ONNX_CUDA='1',LAB_ONNX_CUDA='1')
    result['LAB_NATIVE_ONNX_LIBRARY']=runtime['library_directory']
    result['LD_LIBRARY_PATH']=':'.join(runtime['library_paths'])+(':'+result['LD_LIBRARY_PATH'] if result.get('LD_LIBRARY_PATH') else '')
    result['LD_PRELOAD']=runtime['shim']+(':'+result['LD_PRELOAD'] if result.get('LD_PRELOAD') else '')
    if profile:result['LAB_ONNX_PROFILE']='/root/heroes3-ai-lab/profiles/native-cuda'
    return result


def maybe_reexec():
    if os.environ.get('LAB_NATIVE_ONNX_CUDA')=='1':return
    r=Path(__file__).parent
    explicit=False
    if '--native-opponent-device' in sys.argv:
        explicit=sys.argv[sys.argv.index('--native-opponent-device')+1]=='cuda'
    use=False
    if '--output' in sys.argv and (r/'native-cuda-throughput.json').exists():
        name=Path(sys.argv[sys.argv.index('--output')+1]).name
        selected=json.loads((r/'native-cuda-throughput.json').read_text())
        use=selected.get('completed') and selected.get('use_cuda') and name.startswith(('v5-diverse-','v5-full-graph-capacity'))
    if explicit or use:
        # Must re-exec before the dynamic loader starts any VCMI worker;
        # modifying LD_LIBRARY_PATH within a running process is insufficient.
        env=environment()
        os.execvpe('bash',['bash',str(r/'run-lab.sh'),str(Path(sys.argv[0]).resolve()),*sys.argv[1:]],env)
