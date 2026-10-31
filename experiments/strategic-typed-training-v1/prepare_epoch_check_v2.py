"""Correct the rejection-test fixture; preserve first attempt and its earlier runtime gate."""
import json
from pathlib import Path
p=Path(__file__).resolve().parent
src=(p/'check_collector_epoch_cuda.py').read_text()
src=src.replace("OUT=HERE/'collector-epoch-cuda-check-01'","OUT=HERE/'collector-epoch-cuda-check-02'")
src=src.replace("cases=[('legacy_admission',HERE/'admitted-episode-02','Collector/source epoch differs'),",
    "cases=[('legacy_runtime',HERE/'admitted-episode-02','Mixed or uncertified native runtime epoch'),\n       ('legacy_admission',Path('/root/heroes3-ai-lab/evaluations/typed-onpolicy-balanced-ack-01/cell-00/admitted'),'Collector/source epoch differs'),")
dest=p/'check_collector_epoch_cuda_v2.py';assert not dest.exists();compile(src,str(dest),'exec');dest.write_text(src)
(p/'collector-epoch-cuda-check-01/FAILURE.json').write_text(json.dumps(dict(passed=False,
    error='Fixture used old runtime and reached the earlier correct runtime rejection, before intended collector-source rejection',
    optimizer_steps=0,corrected_in='check_collector_epoch_cuda_v2.py'),indent=2))
