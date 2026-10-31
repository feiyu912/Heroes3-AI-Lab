"""Download the pinned official GPU runtime through the Windows network stack."""
import hashlib
import json
from pathlib import Path
import time
import urllib.request
import sys

version=sys.argv[1] if len(sys.argv)>1 else '1.22.0'
with urllib.request.urlopen('https://pypi.org/pypi/onnxruntime-gpu/'+version+'/json',timeout=30) as response:
    metadata=json.load(response)
release=next(x for x in metadata['urls'] if 'cp310-cp310-manylinux' in x['filename'] and 'x86_64' in x['filename'])
assert release['url'].startswith('https://files.pythonhosted.org/')
folder=Path(r'\\wsl.localhost\Ubuntu-22.04\root\heroes3-ai-lab\downloads')
target=folder/release['filename'];temporary=target.with_suffix('.windows.part')
folder.mkdir(exist_ok=True)
tick=time.monotonic();total=0;digest=hashlib.sha256()
with urllib.request.urlopen(release['url'],timeout=60) as response,temporary.open('wb') as output:
    while True:
        chunk=response.read(1024*1024)
        if not chunk:break
        output.write(chunk);digest.update(chunk);total+=len(chunk)
        if total%(25*1024*1024)==0:print(total,'bytes downloaded',flush=True)
assert total==release['size'] and digest.hexdigest()==release['digests']['sha256']
temporary.replace(target)
print(json.dumps(dict(bytes=total,seconds=time.monotonic()-tick,sha256=digest.hexdigest(),file=str(target))),flush=True)
