"""Archive invalid audit batch, keeping source RESULT false and all raw evidence."""
from pathlib import Path
source=Path(__file__).resolve().parent.parent/'strategic-request-bind-barrier-v2/archive_failed_proxy_v2.py'
text=source.read_text().replace('typed-clearance-proxy-paired-02','typed-clearance-proxy-paired-03').replace("OUT=HERE/'failed-proxy-evidence-02'","OUT=HERE/'failed-proxy-evidence-03'")
exec(compile(text,str(source)+'-batch03','exec'),{'__file__':__file__})
